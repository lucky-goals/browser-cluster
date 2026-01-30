"""
提示词模板数据模型

定义提取要求模板的数据结构，支持用户创建和管理常用的提取提示词
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class PromptTemplateBase(BaseModel):
    """提示词模板基础配置"""

    name: str  # 模板名称
    content: str  # 提示词内容
    description: Optional[str] = None  # 模板描述（可选）


class PromptTemplateCreate(PromptTemplateBase):
    """创建提示词模板请求"""

    pass


class PromptTemplateUpdate(BaseModel):
    """更新提示词模板请求"""

    name: Optional[str] = None
    content: Optional[str] = None
    description: Optional[str] = None


class PromptTemplateResponse(PromptTemplateBase):
    """提示词模板响应"""

    id: str = Field(alias="_id")
    user_id: int  # 创建者用户 ID
    username: str  # 创建者用户名
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True


class PromptTemplateListResponse(BaseModel):
    """提示词模板列表响应"""

    items: List[PromptTemplateResponse]
    total: int
