"""
技能包相关的数据模型

允许将多个技能组合在一起，方便快速复用
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.task import InteractionStep


class SkillBundleModel(BaseModel):
    """技能包数据模型"""
    id: Optional[str] = Field(None, alias="_id")
    name: str = Field(..., description="技能包名称")
    description: Optional[str] = None
    steps: List[InteractionStep] = Field(default_factory=list, description="包含的交互步骤列表")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True


class SkillBundleCreate(BaseModel):
    """创建技能包请求"""
    name: str
    description: Optional[str] = None
    steps: List[InteractionStep] = Field(default_factory=list)


class SkillBundleUpdate(BaseModel):
    """更新技能包请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[InteractionStep]] = None
