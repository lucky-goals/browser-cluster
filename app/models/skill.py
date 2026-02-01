"""
技能相关的数据模型

定义可扩展的浏览器操作和数据提取技能模型
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class SkillType(str, Enum):
    """技能类型"""
    INTERACTION = "interaction"  # 纯交互操作（无返回值）
    EXTRACTION = "extraction"    # 数据提取（有返回值）


class SkillModel(BaseModel):
    """技能数据模型"""
    id: Optional[str] = Field(None, alias="_id")
    name: str = Field(..., description="技能唯一标识符，如 'extract_prices'")
    display_name: str = Field(..., description="技能显示名称")
    type: SkillType = Field(SkillType.INTERACTION)
    description: Optional[str] = None
    js_code: str = Field(..., description="要执行的 JavaScript 代码。如果是提取类，应包含 return 语句")
    params_schema: Optional[Dict[str, Any]] = Field(None, description="参数定义及其默认值")
    is_builtin: bool = Field(False, description="是否为内置技能")
    is_enabled: bool = Field(True, description="是否启用")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        populate_by_name = True


class SkillCreate(BaseModel):
    """创建技能请求"""
    name: str
    display_name: str
    type: SkillType = SkillType.INTERACTION
    description: Optional[str] = None
    js_code: str
    params_schema: Optional[Dict[str, Any]] = None
    is_enabled: bool = True


class SkillUpdate(BaseModel):
    """更新技能请求"""
    display_name: Optional[str] = None
    type: Optional[SkillType] = None
    description: Optional[str] = None
    js_code: Optional[str] = None
    params_schema: Optional[Dict[str, Any]] = None
    is_enabled: Optional[bool] = None
