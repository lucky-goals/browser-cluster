"""
LLM 模型管理 API 路由

提供大语言模型配置的增删改查接口
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from bson import ObjectId

from app.models.llm import (
    LLMModelCreate,
    LLMModelUpdate,
    LLMModelResponse,
    LLMModelListResponse,
    LLMTestRequest,
    LLMTestResponse,
)
from app.core.auth import get_current_active_user, get_current_admin
from app.db.mongo import mongo

router = APIRouter(prefix="/api/v1/llm", tags=["LLM Models"])


def serialize_model(doc: dict) -> dict:
    """序列化 MongoDB 文档为响应格式"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("/models", response_model=LLMModelListResponse)
async def list_models(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_enabled: Optional[bool] = None,
    current_user: dict = Depends(get_current_active_user),
):
    """
    获取 LLM 模型列表

    Args:
        skip: 跳过记录数
        limit: 返回记录数上限
        is_enabled: 可选，按启用状态过滤
    """
    query = {}
    if is_enabled is not None:
        query["is_enabled"] = is_enabled

    cursor = mongo.llm_models.find(query).skip(skip).limit(limit).sort("created_at", -1)
    items = [serialize_model(doc) for doc in cursor]
    total = mongo.llm_models.count_documents(query)

    return LLMModelListResponse(items=items, total=total)


@router.get("/models/{model_id}", response_model=LLMModelResponse)
async def get_model(
    model_id: str, current_user: dict = Depends(get_current_active_user)
):
    """
    获取单个 LLM 模型详情
    """
    try:
        doc = mongo.llm_models.find_one({"_id": ObjectId(model_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid model ID format")

    if not doc:
        raise HTTPException(status_code=404, detail="Model not found")

    return serialize_model(doc)


@router.post("/models", response_model=LLMModelResponse)
async def create_model(
    data: LLMModelCreate, current_user: dict = Depends(get_current_admin)
):
    """
    创建新的 LLM 模型配置（仅管理员）
    """
    now = datetime.now()

    # 如果设置为默认模型，先取消其他默认
    if data.is_default:
        mongo.llm_models.update_many(
            {"is_default": True}, {"$set": {"is_default": False, "updated_at": now}}
        )

    doc = {**data.model_dump(), "created_at": now, "updated_at": now}

    result = mongo.llm_models.insert_one(doc)
    doc["_id"] = str(result.inserted_id)

    return doc


@router.put("/models/{model_id}", response_model=LLMModelResponse)
async def update_model(
    model_id: str, data: LLMModelUpdate, current_user: dict = Depends(get_current_admin)
):
    """
    更新 LLM 模型配置（仅管理员）
    """
    try:
        oid = ObjectId(model_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid model ID format")

    existing = mongo.llm_models.find_one({"_id": oid})
    if not existing:
        raise HTTPException(status_code=404, detail="Model not found")

    now = datetime.now()
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}

    # 如果设置为默认模型，先取消其他默认
    if update_data.get("is_default"):
        mongo.llm_models.update_many(
            {"is_default": True, "_id": {"$ne": oid}},
            {"$set": {"is_default": False, "updated_at": now}},
        )

    update_data["updated_at"] = now

    mongo.llm_models.update_one({"_id": oid}, {"$set": update_data})

    updated = mongo.llm_models.find_one({"_id": oid})
    return serialize_model(updated)


@router.delete("/models/{model_id}")
async def delete_model(model_id: str, current_user: dict = Depends(get_current_admin)):
    """
    删除 LLM 模型配置（仅管理员）
    """
    try:
        oid = ObjectId(model_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid model ID format")

    result = mongo.llm_models.delete_one({"_id": oid})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Model not found")

    return {"message": "Model deleted successfully"}


@router.post("/models/{model_id}/test", response_model=LLMTestResponse)
async def test_model(
    model_id: str,
    request: LLMTestRequest = None,
    current_user: dict = Depends(get_current_admin),
):
    """
    测试 LLM 模型连接（仅管理员）

    发送一个简单的测试请求验证模型配置是否正确
    """
    import time

    try:
        oid = ObjectId(model_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid model ID format")

    model_config = mongo.llm_models.find_one({"_id": oid})
    if not model_config:
        raise HTTPException(status_code=404, detail="Model not found")

    # 默认测试提示
    test_prompt = (
        request.prompt
        if request
        else "Hello, please respond with 'OK' if you can receive this message."
    )

    start_time = time.time()

    try:
        # 延迟导入，避免循环依赖
        from app.services.llm_agent import LLMAgent

        agent = LLMAgent(model_config)
        response = await agent.test_connection(test_prompt)

        latency_ms = (time.time() - start_time) * 1000

        return LLMTestResponse(
            success=True,
            message="Connection successful",
            response=response,
            latency_ms=round(latency_ms, 2),
        )
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return LLMTestResponse(
            success=False,
            message=f"Connection failed: {str(e)}",
            latency_ms=round(latency_ms, 2),
        )
