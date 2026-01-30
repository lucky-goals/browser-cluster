"""
代理服务器配置数据模型

定义代理服务器的基本信息、认证信息及会话配置
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ProxyProtocol(str, Enum):
    """代理协议枚举"""
    HTTP = "http"
    SOCKS5 = "socks5"


class SessionType(str, Enum):
    """会话类型枚举"""
    RANDOM = "random"  # 随机 IP
    STICKY = "sticky"  # 粘性 IP


class ProxyBase(BaseModel):
    """代理服务器基础配置"""
    name: str = Field(..., description="代理名称")
    protocol: ProxyProtocol = Field(default=ProxyProtocol.HTTP)
    server: str = Field(..., description="服务器地址，如 us.arxlabs.io:3010")
    username: Optional[str] = None
    password: Optional[str] = None
    session_type: SessionType = Field(default=SessionType.RANDOM)
    location: Optional[str] = Field(None, description="国家城市文本")
    is_enabled: bool = True


class ProxyCreate(ProxyBase):
    """创建代理请求"""
    pass


class ProxyUpdate(BaseModel):
    """更新代理请求"""
    name: Optional[str] = None
    protocol: Optional[ProxyProtocol] = None
    server: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    session_type: Optional[SessionType] = None
    location: Optional[str] = None
    is_enabled: Optional[bool] = None


class ProxyResponse(ProxyBase):
    """代理配置响应"""
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True


class ProxyListResponse(BaseModel):
    """代理列表响应"""
    items: List[ProxyResponse]
    total: int
