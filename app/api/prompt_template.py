"""
提示词模板管理 API

提供提示词模板的 CRUD 和搜索功能
"""

import logging
from datetime import datetime
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Query

from app.models.prompt_template import (
    PromptTemplateCreate,
    PromptTemplateUpdate,
    PromptTemplateResponse,
    PromptTemplateListResponse,
)
from app.core.auth import get_current_active_user
from app.db.mongo import mongo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/prompt-templates", tags=["Prompt Templates"])


def serialize_template(doc: dict) -> dict:
    """序列化模板文档"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("", response_model=PromptTemplateListResponse)
async def list_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    current_user: dict = Depends(get_current_active_user),
):
    """
    获取提示词模板列表，支持模糊搜索
    """
    query = {}

    # 模糊搜索：按名称或内容搜索
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"content": {"$regex": search, "$options": "i"}},
            {"description": {"$regex": search, "$options": "i"}},
        ]

    cursor = (
        mongo.prompt_templates.find(query)
        .skip(skip)
        .limit(limit)
        .sort("created_at", -1)
    )
    items = [serialize_template(doc) for doc in cursor]
    total = mongo.prompt_templates.count_documents(query)

    return PromptTemplateListResponse(items=items, total=total)


@router.get("/{template_id}", response_model=PromptTemplateResponse)
async def get_template(
    template_id: str, current_user: dict = Depends(get_current_active_user)
):
    """
    获取单个提示词模板详情
    """
    try:
        doc = mongo.prompt_templates.find_one({"_id": ObjectId(template_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="无效的模板 ID")

    if not doc:
        raise HTTPException(status_code=404, detail="模板不存在")

    return serialize_template(doc)


@router.post("", response_model=PromptTemplateResponse)
async def create_template(
    data: PromptTemplateCreate, current_user: dict = Depends(get_current_active_user)
):
    """
    创建新的提示词模板
    """
    now = datetime.utcnow()
    doc = {
        **data.model_dump(),
        "user_id": current_user.get("id"),
        "username": current_user.get("username"),
        "created_at": now,
        "updated_at": now,
    }

    result = mongo.prompt_templates.insert_one(doc)
    doc["_id"] = str(result.inserted_id)

    logger.info(f"User {current_user.get('username')} created template: {data.name}")
    return doc


@router.put("/{template_id}", response_model=PromptTemplateResponse)
async def update_template(
    template_id: str,
    data: PromptTemplateUpdate,
    current_user: dict = Depends(get_current_active_user),
):
    """
    更新提示词模板（仅创建者或管理员可操作）
    """
    try:
        doc = mongo.prompt_templates.find_one({"_id": ObjectId(template_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="无效的模板 ID")

    if not doc:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 权限检查：仅创建者或管理员可修改
    if (
        doc.get("user_id") != current_user.get("id")
        and current_user.get("role") != "admin"
    ):
        raise HTTPException(status_code=403, detail="无权修改此模板")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = datetime.utcnow()

    mongo.prompt_templates.update_one(
        {"_id": ObjectId(template_id)}, {"$set": update_data}
    )

    updated_doc = mongo.prompt_templates.find_one({"_id": ObjectId(template_id)})
    return serialize_template(updated_doc)


@router.delete("/{template_id}")
async def delete_template(
    template_id: str, current_user: dict = Depends(get_current_active_user)
):
    """
    删除提示词模板（仅创建者或管理员可操作）
    """
    try:
        doc = mongo.prompt_templates.find_one({"_id": ObjectId(template_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="无效的模板 ID")

    if not doc:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 权限检查：仅创建者或管理员可删除
    if (
        doc.get("user_id") != current_user.get("id")
        and current_user.get("role") != "admin"
    ):
        raise HTTPException(status_code=403, detail="无权删除此模板")

    mongo.prompt_templates.delete_one({"_id": ObjectId(template_id)})

    logger.info(f"User {current_user.get('username')} deleted template: {template_id}")
    return {"message": "模板已删除"}
