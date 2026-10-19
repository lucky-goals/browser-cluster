"""MongoDB 代理配置模型 used by the legacy ``/api/v1/proxies`` API."""

from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class ProxyProtocol(str, Enum):
    HTTP = "http"
    SOCKS5 = "socks5"


class SessionType(str, Enum):
    RANDOM = "random"
    STICKY = "sticky"


class ProxyBase(BaseModel):
    name: str = Field(..., description="代理名称")
    protocol: ProxyProtocol = ProxyProtocol.HTTP
    server: str = Field(..., description="服务器地址，如 us.example.com:3010")
    username: Optional[str] = None
    password: Optional[str] = None
    session_type: SessionType = SessionType.RANDOM
    location: Optional[str] = None
    is_enabled: bool = True


class ProxyCreate(ProxyBase):
    pass


class ProxyUpdate(BaseModel):
    name: Optional[str] = None
    protocol: Optional[ProxyProtocol] = None
    server: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    session_type: Optional[SessionType] = None
    location: Optional[str] = None
    is_enabled: Optional[bool] = None


class ProxyResponse(ProxyBase):
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}


class ProxyListResponse(BaseModel):
    items: List[ProxyResponse]
    total: int
