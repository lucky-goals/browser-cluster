"""任务查询、删除和重试 API。"""

import base64
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.auth import get_current_user
from app.db.mongo import mongo
from app.models.task import BatchDeleteRequest, RetryRequest, TaskResponse
from app.services.cache_service import cache_service
from app.services.oss_service import oss_service
from app.services.queue_service import rabbitmq_service

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])


@router.delete("/batch")
async def batch_delete_tasks(
    request: BatchDeleteRequest, current_user: dict = Depends(get_current_user)
):
    result = mongo.tasks.delete_many({"task_id": {"$in": request.task_ids}})
    return {
        "status": "success",
        "message": f"Successfully deleted {result.deleted_count} tasks",
        "deleted_count": result.deleted_count,
    }


def _mask_params(params: dict) -> dict:
    """只脱敏代理密码，避免任务详情泄露凭据。"""
    safe_params = (params or {}).copy()
    proxy = safe_params.get("proxy")
    if isinstance(proxy, dict):
        proxy = proxy.copy()
        if "password" in proxy:
            proxy["password"] = "****"
        safe_params["proxy"] = proxy
    return safe_params


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    include_html: bool = Query(True, description="是否包含 HTML 源码"),
    include_screenshot: bool = Query(True, description="是否包含截图数据"),
    current_user: dict = Depends(get_current_user),
):
    projection = {}
    if not include_html:
        projection["result.html"] = 0
    if not include_screenshot:
        projection["result.screenshot"] = 0
    task = mongo.tasks.find_one({"task_id": task_id}, projection)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = task.get("result") or {}
    if include_html and result.get("oss_html") and not result.get("html"):
        try:
            content = oss_service.get_content(result["oss_html"])
            if content:
                result["html"] = content.decode("utf-8", errors="ignore")
        except Exception as exc:
            # A missing remote asset should not make the task metadata unavailable.
            print(f"Error fetching HTML from OSS via SDK: {exc}")
    if include_screenshot and result.get("oss_screenshot") and not result.get("screenshot"):
        try:
            content = oss_service.get_content(result["oss_screenshot"])
            if content:
                result["screenshot"] = base64.b64encode(content).decode("utf-8")
        except Exception as exc:
            print(f"Error fetching screenshot from OSS via SDK: {exc}")

    return TaskResponse(
        task_id=task["task_id"],
        url=task["url"],
        node_id=task.get("node_id"),
        status=task["status"],
        retry_count=task.get("retry_count", 0),
        retry_enabled=task.get("retry_enabled", True),
        max_retries=task.get("max_retries", 3),
        execution_type=task.get("execution_type", "production"),
        params=_mask_params(task.get("params", {})),
        priority=task.get("priority"),
        cache=task.get("cache"),
        result=result,
        error=task.get("error"),
        cached=task.get("cached", False),
        html_cached=task.get("html_cached", False),
        agent_cached=task.get("agent_cached", False),
        created_at=task["created_at"],
        updated_at=task["updated_at"],
        completed_at=task.get("completed_at"),
    )


@router.get("/")
async def list_tasks(
    status: str = None,
    url: str = None,
    schedule_id: str = None,
    execution_type: str = "production",
    cached: bool = None,
    skip: int = 0,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    query = {}
    if status:
        query["status"] = status
    if schedule_id:
        query["schedule_id"] = schedule_id
    if url:
        query["$or"] = [
            {"url": {"$regex": url, "$options": "i"}},
            {"task_id": {"$regex": url, "$options": "i"}},
        ]
    if cached is not None:
        query["cached"] = cached
    if execution_type == "production":
        query["execution_type"] = {"$ne": "test"}
    elif execution_type == "test":
        query["execution_type"] = "test"

    projection = {
        "task_id": 1,
        "url": 1,
        "params": 1,
        "priority": 1,
        "cache": 1,
        "status": 1,
        "cached": 1,
        "html_cached": 1,
        "agent_cached": 1,
        "execution_type": 1,
        "node_id": 1,
        "created_at": 1,
        "updated_at": 1,
        "completed_at": 1,
        "result.metadata.load_time": 1,
    }
    tasks = mongo.tasks.find(query, projection).sort("created_at", -1).skip(skip).limit(limit)
    return {
        "total": mongo.tasks.count_documents(query),
        "tasks": [
            {
                "task_id": task["task_id"],
                "url": task["url"],
                "params": _mask_params(task.get("params", {})),
                "priority": task.get("priority", 1),
                "cache": task.get("cache", {"enabled": True, "ttl": 3600}),
                "status": task["status"],
                "cached": task.get("cached", False),
                "html_cached": task.get("html_cached", False),
                "agent_cached": task.get("agent_cached", False),
                "execution_type": task.get("execution_type", "production"),
                "node_id": task.get("node_id"),
                "created_at": task["created_at"],
                "updated_at": task["updated_at"],
                "completed_at": task.get("completed_at"),
                "duration": (task.get("result") or {}).get("metadata", {}).get("load_time"),
            }
            for task in tasks
        ],
    }


@router.delete("/{task_id}")
async def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    result = mongo.tasks.delete_one({"task_id": task_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"status": "success", "message": "Task deleted"}


@router.post("/{task_id}/retry", response_model=TaskResponse)
async def retry_task(
    task_id: str,
    request: Optional[RetryRequest] = None,
    agent_model_id: Optional[str] = None,
    agent_parallel_enabled: Optional[bool] = None,
    agent_parallel_batch_size: Optional[int] = None,
    current_user: dict = Depends(get_current_user),
):
    task = mongo.tasks.find_one({"task_id": task_id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    params = (task.get("params") or {}).copy()
    if agent_model_id:
        params["agent_model_id"] = agent_model_id
    if agent_parallel_enabled is not None:
        params["agent_parallel_enabled"] = agent_parallel_enabled
    if agent_parallel_batch_size is not None:
        params["agent_parallel_batch_size"] = agent_parallel_batch_size

    final_url = task["url"]
    final_priority = task.get("priority", 1)
    final_cache = task.get("cache", {"enabled": True, "ttl": 3600})
    update_data = {
        "status": "pending",
        "retry_count": 0,
        "params": params,
        "result": None,
        "cached": False,
        "html_cached": False,
        "agent_cached": False,
        "updated_at": datetime.now(),
        "completed_at": None,
        "node_id": None,
    }
    if request:
        if request.url:
            final_url = request.url
            update_data["url"] = final_url
        if request.params is not None:
            params = request.params
            update_data["params"] = params
        if request.priority is not None:
            final_priority = request.priority
            update_data["priority"] = final_priority
        if request.cache is not None:
            final_cache = request.cache
            update_data["cache"] = final_cache

    cache_key = cache_service.generate_cache_key(final_url, params)
    update_data["cache_key"] = cache_key
    if final_cache.get("enabled"):
        cached = await cache_service.get(final_url, params)
        if cached:
            result = cached.get("result") if "result" in cached else cached
            result = result or {}
            now = datetime.now()
            html_cached = cached.get("html_cached", result.get("html_cached", True))
            agent_cached = cached.get("agent_cached", result.get("agent_cached", True))
            update_data.update(
                {
                    "status": "success",
                    "result": result,
                    "cached": True,
                    "html_cached": html_cached,
                    "agent_cached": agent_cached,
                    "node_id": "cache",
                    "updated_at": now,
                    "completed_at": cached.get("completed_at") or now,
                }
            )
            mongo.tasks.update_one({"task_id": task_id}, {"$set": update_data, "$unset": {"error": ""}})
            return TaskResponse(
                task_id=task_id,
                url=final_url,
                status="success",
                retry_count=0,
                retry_enabled=task.get("retry_enabled", True),
                max_retries=task.get("max_retries", 3),
                execution_type=task.get("execution_type", "production"),
                params=params,
                priority=final_priority,
                cache=final_cache,
                result=result,
                cached=True,
                html_cached=html_cached,
                agent_cached=agent_cached,
                created_at=task["created_at"],
                updated_at=now,
                completed_at=update_data["completed_at"],
            )

    mongo.tasks.update_one({"task_id": task_id}, {"$set": update_data, "$unset": {"error": ""}})
    queue_task = {
        "task_id": task_id,
        "url": final_url,
        "params": params,
        "execution_type": task.get("execution_type", "production"),
        "cache": final_cache,
        "priority": final_priority,
        "retry_enabled": task.get("retry_enabled", True),
        "max_retries": task.get("max_retries", 3),
    }
    if not rabbitmq_service.publish_task(queue_task):
        mongo.tasks.update_one(
            {"task_id": task_id},
            {"$set": {"status": "failed", "error": {"message": "Failed to re-queue task"}}},
        )
        raise HTTPException(status_code=500, detail="Failed to queue task")
    now = update_data["updated_at"]
    return TaskResponse(
        task_id=task_id,
        url=final_url,
        status="pending",
        retry_count=0,
        retry_enabled=task.get("retry_enabled", True),
        max_retries=task.get("max_retries", 3),
        execution_type=task.get("execution_type", "production"),
        params=params,
        priority=final_priority,
        cache=final_cache,
        created_at=task["created_at"],
        updated_at=now,
    )
