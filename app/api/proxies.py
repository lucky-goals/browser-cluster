"""
代理服务器管理 API
"""

import logging
import time
from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Query

from app.models.proxy import (
    ProxyCreate,
    ProxyUpdate,
    ProxyResponse,
    ProxyListResponse,
)
from app.core.auth import get_current_active_user
from app.db.mongo import mongo
from app.core.scraper import scraper
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/proxies", tags=["Proxies"])


def serialize_proxy(doc: dict) -> dict:
    """序列化代理文档"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("", response_model=ProxyListResponse)
async def list_proxies(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user),
):
    """
    获取代理列表，支持模糊搜索（按名称、服务器、地理位置搜索）
    """
    query = {}

    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"server": {"$regex": search, "$options": "i"}},
            {"location": {"$regex": search, "$options": "i"}},
        ]

    cursor = (
        mongo.proxies.find(query)
        .skip(skip)
        .limit(limit)
        .sort("created_at", -1)
    )
    items = [serialize_proxy(doc) for doc in cursor]
    total = mongo.proxies.count_documents(query)

    return ProxyListResponse(items=items, total=total)


@router.post("", response_model=ProxyResponse)
async def create_proxy(
    data: ProxyCreate, current_user: dict = Depends(get_current_active_user)
):
    """
    创建新的代理配置
    """
    now = datetime.utcnow()
    doc = {
        **data.model_dump(),
        "created_at": now,
        "updated_at": now,
    }

    result = mongo.proxies.insert_one(doc)
    doc["_id"] = str(result.inserted_id)

    logger.info(f"User {current_user.get('username')} created proxy: {data.name}")
    return doc


@router.put("/{proxy_id}", response_model=ProxyResponse)
async def update_proxy(
    proxy_id: str,
    data: ProxyUpdate,
    current_user: dict = Depends(get_current_active_user),
):
    """
    更新代理配置
    """
    try:
        doc = mongo.proxies.find_one({"_id": ObjectId(proxy_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="无效的代理 ID")

    if not doc:
        raise HTTPException(status_code=404, detail="代理不存在")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()

    mongo.proxies.update_one(
        {"_id": ObjectId(proxy_id)}, {"$set": update_data}
    )

    updated_doc = mongo.proxies.find_one({"_id": ObjectId(proxy_id)})
    return serialize_proxy(updated_doc)


@router.delete("/{proxy_id}")
async def delete_proxy(
    proxy_id: str, current_user: dict = Depends(get_current_active_user)
):
    """
    删除代理配置
    """
    try:
        result = mongo.proxies.delete_one({"_id": ObjectId(proxy_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="无效的代理 ID")

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="代理不存在")

    logger.info(f"User {current_user.get('username')} deleted proxy: {proxy_id}")
    return {"message": "代理已删除"}


@router.post("/{proxy_id}/test")
async def test_stored_proxy(
    proxy_id: str, current_user: dict = Depends(get_current_active_user)
):
    """
    测试存储的代理是否可用
    """
    try:
        doc = mongo.proxies.find_one({"_id": ObjectId(proxy_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="无效的代理 ID")

    if not doc:
        raise HTTPException(status_code=404, detail="代理不存在")

    test_url = settings.proxy_test_url
    proxy_params = {
        "server": doc["server"],
        "username": doc.get("username"),
        "password": doc.get("password")
    }
    
    start_time = time.time()
    
    # 构建抓取参数供 Scraper 使用
    scrape_params = {
        "proxy": proxy_params,
        "timeout": 15000,
        "wait_for": "domcontentloaded",
        "screenshot": False,
        "stealth": True
    }
    
    try:
        result = await scraper.scrape(test_url, scrape_params, node_id="test-node")
        latency = time.time() - start_time
        
        if result["status"] == "success":
            return {
                "status": "success",
                "message": "Proxy is working correctly",
                "latency": round(latency, 2),
                "status_code": result["metadata"].get("status_code")
            }
        else:
            return {
                "status": "failed",
                "message": result["error"]["message"],
                "latency": round(latency, 2)
            }
            
    except Exception as e:
        return {
            "status": "failed",
            "message": str(e),
            "latency": round(time.time() - start_time, 2)
        }
