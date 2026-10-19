"""网页抓取 API 路由。"""

import asyncio
import time
from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.scraper import scraper
from app.db.mongo import mongo
from app.models.task import (
    BatchScrapeRequest,
    BatchScrapeResponse,
    ProxyTestRequest,
    ScrapeRequest,
    TaskResponse,
)
from app.services.cache_service import cache_service
from app.services.queue_service import rabbitmq_service
from app.services.task_service import task_service

router = APIRouter(prefix="/api/v1/scrape", tags=["Scrape"])


def _retry_values(request: ScrapeRequest) -> tuple[bool, int]:
    return (
        request.retry_enabled if request.retry_enabled is not None else settings.retry_enabled,
        request.max_retries if request.max_retries is not None else settings.max_retries,
    )


def _materialize_cached_task(
    request: ScrapeRequest,
    cached: dict,
    task_id: str | None = None,
) -> TaskResponse:
    """Persist and return a task represented by a full-task cache entry."""
    url = str(request.url)
    params = request.params.model_dump()
    task_id = task_id or str(ObjectId())
    retry_enabled, max_retries = _retry_values(request)
    cached = cached if isinstance(cached, dict) else {}
    result_data = cached.get("result") if "result" in cached else cached
    result_data = result_data if isinstance(result_data, dict) else {}
    completed_at = cached.get("completed_at")
    if not completed_at:
        completed_at = result_data.get("metadata", {}).get("timestamp")
    html_cached = cached.get("html_cached", result_data.get("html_cached", True))
    agent_cached = cached.get("agent_cached", result_data.get("agent_cached", True))
    now = datetime.now()
    task_data = {
        "task_id": task_id,
        "url": url,
        "status": cached.get("status", "success"),
        "priority": request.priority,
        "schedule_id": request.schedule_id,
        "execution_type": request.execution_type,
        "params": params,
        "retry_count": 0,
        "retry_enabled": retry_enabled,
        "max_retries": max_retries,
        "cache": request.cache.model_dump(),
        "result": result_data,
        "cache_key": cache_service.generate_cache_key(url, params),
        "cached": True,
        "html_cached": html_cached,
        "agent_cached": agent_cached,
        "created_at": now,
        "updated_at": now,
        "completed_at": completed_at or now,
    }
    mongo.tasks.insert_one(task_data)
    return TaskResponse(
        task_id=task_id,
        url=url,
        status=task_data["status"],
        retry_count=0,
        retry_enabled=retry_enabled,
        max_retries=max_retries,
        execution_type=request.execution_type,
        params=params,
        priority=request.priority,
        cache=task_data["cache"],
        result=result_data,
        cached=True,
        html_cached=html_cached,
        agent_cached=agent_cached,
        created_at=now,
        updated_at=now,
        completed_at=task_data["completed_at"],
    )


def _has_usable_agent_result(cached: dict) -> bool:
    """Failed Agent responses must not short-circuit a fresh extraction."""
    if not isinstance(cached, dict):
        return True
    result_data = cached.get("result") if "result" in cached else cached
    agent_result = result_data.get("agent_result") if isinstance(result_data, dict) else None
    return not (isinstance(agent_result, dict) and agent_result.get("status") == "failed")


@router.post("/", response_model=TaskResponse)
async def scrape(request: ScrapeRequest, current_user: dict = Depends(get_current_user)):
    """同步抓取：先查全量缓存，未命中后投递任务并等待完成。"""
    url = str(request.url)
    params = request.params.model_dump()
    task_id = str(ObjectId())
    cache_key = cache_service.generate_cache_key(url, params)
    retry_enabled, max_retries = _retry_values(request)

    if request.cache.enabled:
        cached = await cache_service.get(url, params)
        if cached and _has_usable_agent_result(cached):
            return _materialize_cached_task(request, cached, task_id=task_id)

    now = datetime.now()
    task_data = {
        "task_id": task_id,
        "url": url,
        "status": "pending",
        "priority": request.priority,
        "schedule_id": request.schedule_id,
        "execution_type": request.execution_type,
        "params": params,
        "retry_count": 0,
        "retry_enabled": retry_enabled,
        "max_retries": max_retries,
        "cache": request.cache.model_dump(),
        "cache_key": cache_key,
        "cached": False,
        "html_cached": False,
        "agent_cached": False,
        "created_at": now,
        "updated_at": now,
    }
    mongo.tasks.insert_one(task_data)

    queue_task = {
        "task_id": task_id,
        "url": url,
        "params": params,
        "execution_type": request.execution_type,
        "cache": request.cache.model_dump(),
        "priority": request.priority,
        "retry_enabled": retry_enabled,
        "max_retries": max_retries,
    }
    if not rabbitmq_service.publish_task(queue_task):
        mongo.tasks.update_one(
            {"task_id": task_id},
            {
                "$set": {
                    "status": "failed",
                    "error": {"message": "Failed to queue task: RabbitMQ connection issue"},
                    "updated_at": datetime.now(),
                }
            },
        )
        raise HTTPException(status_code=500, detail="Failed to queue task")

    task_timeout_ms = request.params.timeout or settings.default_timeout
    wait_timeout = task_timeout_ms / 1000 + 30
    start_time = datetime.now()
    while (datetime.now() - start_time).total_seconds() < wait_timeout:
        task = mongo.tasks.find_one({"task_id": task_id})
        if task and task.get("status") in {"success", "failed"}:
            return TaskResponse(
                task_id=task_id,
                url=url,
                node_id=task.get("node_id"),
                status=task["status"],
                retry_count=task.get("retry_count", 0),
                retry_enabled=task.get("retry_enabled", retry_enabled),
                max_retries=task.get("max_retries", max_retries),
                execution_type=task.get("execution_type", request.execution_type),
                params=task.get("params"),
                priority=task.get("priority"),
                cache=task.get("cache"),
                result=task.get("result"),
                error=task.get("error"),
                cached=task.get("cached", False),
                html_cached=task.get("html_cached", False),
                agent_cached=task.get("agent_cached", False),
                created_at=task["created_at"],
                updated_at=task["updated_at"],
                completed_at=task.get("completed_at"),
            )
        await asyncio.sleep(0.5)
    raise HTTPException(status_code=504, detail="Task execution timed out")


@router.post("/async", response_model=TaskResponse)
async def scrape_async(request: ScrapeRequest, current_user: dict = Depends(get_current_user)):
    """异步创建抓取任务并立即返回。"""
    if request.cache.enabled:
        url = str(request.url)
        params = request.params.model_dump()
        cached = await cache_service.get(url, params)
        if cached and _has_usable_agent_result(cached):
            return _materialize_cached_task(request, cached)
    return await task_service.create_task(request)


@router.post("/batch", response_model=BatchScrapeResponse)
async def scrape_batch(
    request: BatchScrapeRequest, current_user: dict = Depends(get_current_user)
):
    """批量创建异步抓取任务。"""
    task_ids: list[str] = []
    for req in request.tasks:
        url = str(req.url)
        params = req.params.model_dump()
        task_id = str(ObjectId())
        cache_key = cache_service.generate_cache_key(url, params)
        retry_enabled, max_retries = _retry_values(req)
        now = datetime.now()
        task_data = {
            "task_id": task_id,
            "url": url,
            "status": "pending",
            "priority": req.priority,
            "schedule_id": req.schedule_id,
            "execution_type": req.execution_type,
            "params": params,
            "retry_count": 0,
            "retry_enabled": retry_enabled,
            "max_retries": max_retries,
            "cache": req.cache.model_dump(),
            "cache_key": cache_key,
            "cached": False,
            "html_cached": False,
            "agent_cached": False,
            "created_at": now,
            "updated_at": now,
        }
        mongo.tasks.insert_one(task_data)
        queue_task = {
            "task_id": task_id,
            "url": url,
            "params": params,
            "cache": req.cache.model_dump(),
            "priority": req.priority,
            "execution_type": req.execution_type,
            "retry_enabled": retry_enabled,
            "max_retries": max_retries,
        }
        if not rabbitmq_service.publish_task(queue_task):
            mongo.tasks.update_one(
                {"task_id": task_id},
                {
                    "$set": {
                        "status": "failed",
                        "error": {"message": "Failed to queue task: RabbitMQ connection issue"},
                        "updated_at": datetime.now(),
                    }
                },
            )
        task_ids.append(task_id)
    return BatchScrapeResponse(task_ids=task_ids)


@router.post("/test-proxy")
async def test_proxy(
    request: ProxyTestRequest, current_user: dict = Depends(get_current_user)
):
    """使用配置的测试地址验证代理。"""
    test_url = settings.proxy_test_url
    start_time = time.time()
    scrape_params = {
        "proxy": request.proxy.model_dump(),
        "timeout": 15000,
        "wait_for": "domcontentloaded",
        "screenshot": False,
        "stealth": True,
    }
    try:
        result = await scraper.scrape(test_url, scrape_params, node_id="test-node")
        latency = time.time() - start_time
        if result.get("status") == "success":
            return {
                "status": "success",
                "message": "Proxy is working correctly",
                "latency": round(latency, 2),
                "url": test_url,
                "status_code": result.get("metadata", {}).get("status_code"),
            }
        error = result.get("error") or {}
        return {
            "status": "failed",
            "message": error.get("message", str(error)) if isinstance(error, dict) else str(error),
            "type": error.get("type") if isinstance(error, dict) else None,
            "latency": round(latency, 2),
        }
    except Exception as exc:
        return {
            "status": "failed",
            "message": str(exc),
            "latency": round(time.time() - start_time, 2),
        }
