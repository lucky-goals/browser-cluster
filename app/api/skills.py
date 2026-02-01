"""
技能管理 API 路由模块

提供技能的增删改查接口
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from app.models.skill import SkillModel, SkillCreate, SkillUpdate, SkillType
from app.services.skill_service import skill_service
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/v1/skills", tags=["Skills"])


def serialize_skill(doc: dict) -> dict:
    """序列化 MongoDB 文档为响应格式"""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


BUILT_IN_SKILLS = [
    {"name": "scroll", "display_name": "滚动 (Scroll)", "type": "interaction"},
    {"name": "infinite_scroll", "display_name": "流式滚动 (Infinite)", "type": "interaction"},
    {"name": "click", "display_name": "点击 (Click)", "type": "interaction"},
    {"name": "pagination", "display_name": "翻页 (Pagination)", "type": "interaction"},
    {"name": "fill", "display_name": "填充 (Fill)", "type": "interaction"},
    {"name": "zoom", "display_name": "缩放 (Zoom)", "type": "interaction"},
    {"name": "wait", "display_name": "等待 (Wait)", "type": "interaction"},
    {"name": "extract_coordinates", "display_name": "提取坐标 (Coordinates)", "type": "extraction"},
    {"name": "block_container", "display_name": "块状容器 (Block Container)", "type": "extraction"},
    {"name": "exclude_elements", "display_name": "排除元素 (Exclude Elements)", "type": "interaction"},
]


@router.get("/built-in", response_model=List[dict])
async def list_built_in_skills(current_user: dict = Depends(get_current_user)):
    """获取内置技能列表"""
    return BUILT_IN_SKILLS


@router.get("/", response_model=List[SkillModel])
async def list_skills(
    is_enabled: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    """获取技能列表"""
    skills = await skill_service.list_skills(is_enabled=is_enabled)
    return [serialize_skill(doc) for doc in skills]


@router.get("/{skill_id}", response_model=SkillModel)
async def get_skill(skill_id: str, current_user: dict = Depends(get_current_user)):
    """获取技能详情"""
    skill = await skill_service.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return serialize_skill(skill)


@router.post("/", response_model=SkillModel)
async def create_skill(data: SkillCreate, current_user: dict = Depends(get_current_user)):
    """创建新技能"""
    # 检查名称是否冲突
    existing = await skill_service.get_skill_by_name(data.name)
    if existing:
        raise HTTPException(status_code=400, detail=f"Skill name '{data.name}' already exists")
    
    skill_id = await skill_service.create_skill(data)
    skill = await skill_service.get_skill(skill_id)
    return serialize_skill(skill)


@router.put("/{skill_id}")
async def update_skill(
    skill_id: str, 
    data: SkillUpdate, 
    current_user: dict = Depends(get_current_user)
):
    """更新技能"""
    success = await skill_service.update_skill(skill_id, data)
    if not success:
         raise HTTPException(status_code=404, detail="Skill not found or no changes made")
    return {"status": "success", "message": "Skill updated"}


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str, current_user: dict = Depends(get_current_user)):
    """删除技能"""
    success = await skill_service.delete_skill(skill_id)
    if not success:
        raise HTTPException(status_code=404, detail="Skill not found")
    return {"status": "success", "message": "Skill deleted"}
