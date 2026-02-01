"""
技能包管理 API 路由模块

提供技能包的增删改查接口
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from app.models.skill_bundle import SkillBundleModel, SkillBundleCreate, SkillBundleUpdate
from app.services.skill_bundle_service import skill_bundle_service
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/v1/skill-bundles", tags=["Skill Bundles"])


def serialize_bundle(doc: dict) -> dict:
    """序列化 MongoDB 文档为响应格式"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


@router.get("/", response_model=List[SkillBundleModel])
async def list_bundles(current_user: dict = Depends(get_current_user)):
    """获取技能包列表"""
    bundles = await skill_bundle_service.list_bundles()
    return [serialize_bundle(doc) for doc in bundles]


@router.get("/{bundle_id}", response_model=SkillBundleModel)
async def get_bundle(bundle_id: str, current_user: dict = Depends(get_current_user)):
    """获取技能包详情"""
    bundle = await skill_bundle_service.get_bundle(bundle_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Skill bundle not found")
    return serialize_bundle(bundle)


@router.post("/", response_model=SkillBundleModel)
async def create_bundle(data: SkillBundleCreate, current_user: dict = Depends(get_current_user)):
    """创建新技能包"""
    bundle_id = await skill_bundle_service.create_bundle(data)
    bundle = await skill_bundle_service.get_bundle(bundle_id)
    return serialize_bundle(bundle)


@router.put("/{bundle_id}")
async def update_bundle(
    bundle_id: str, 
    data: SkillBundleUpdate, 
    current_user: dict = Depends(get_current_user)
):
    """更新技能包"""
    success = await skill_bundle_service.update_bundle(bundle_id, data)
    if not success:
         raise HTTPException(status_code=404, detail="Skill bundle not found or no changes made")
    return {"status": "success", "message": "Skill bundle updated"}


@router.delete("/{bundle_id}")
async def delete_bundle(bundle_id: str, current_user: dict = Depends(get_current_user)):
    """删除技能包"""
    success = await skill_bundle_service.delete_bundle(bundle_id)
    if not success:
        raise HTTPException(status_code=404, detail="Skill bundle not found")
    return {"status": "success", "message": "Skill bundle deleted"}
