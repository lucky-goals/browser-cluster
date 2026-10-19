"""Redis 代理池的数据模型。"""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field


class Proxy(BaseModel):
    """代理 IP 模型。"""

    id: Optional[str] = Field(None, description="代理唯一标识，通常为 ip:port")
    protocol: str = Field("http", description="协议类型: http, https, socks5")
    ip: str = Field(..., description="代理 IP 地址")
    port: int = Field(..., description="代理端口")
    username: Optional[str] = Field(None, description="用户名")
    password: Optional[str] = Field(None, description="密码")
    group: str = Field("default", description="代理分组")
    priority: int = Field(10, description="优先级，数值越大优先级越高")
    status: str = Field("active", description="状态: active, inactive, testing")
    fail_count: int = Field(0, description="连续失败次数")
    success_count: int = Field(0, description="累计成功次数")
    total_count: int = Field(0, description="累计使用次数")
    last_check_at: Optional[datetime] = Field(None, description="最后检测时间")
    last_used_at: Optional[datetime] = Field(None, description="最后使用时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")

    @property
    def server(self) -> str:
        return f"{self.protocol}://{self.ip}:{self.port}"

    @property
    def auth(self) -> Optional[dict]:
        if self.username and self.password:
            return {"username": self.username, "password": self.password}
        return None

    def to_redis_val(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_redis_val(cls, val: str) -> "Proxy":
        return cls.model_validate_json(val)


class ProxyCreate(BaseModel):
    """创建代理的请求模型。"""

    protocol: str = "http"
    ip: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    group: str = "default"
    priority: int = 10


class ProxyUpdate(BaseModel):
    """更新代理的请求模型。"""

    protocol: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    group: Optional[str] = None
    priority: Optional[int] = None
    status: Optional[str] = None


class ProxyFilter(BaseModel):
    """代理查询过滤器。"""

    group: Optional[str] = None
    status: Optional[str] = None
    protocol: Optional[str] = None


class ProxyListResponse(BaseModel):
    total: int
    items: List[Proxy]


class GroupDetail(BaseModel):
    name: str
    total: int
    active: int


class ProxyStats(BaseModel):
    total: int = Field(..., description="总代理数")
    active: int = Field(..., description="可用代理数")
    inactive: int = Field(..., description="不可用代理数")
    groups: List[str] = Field(..., description="所有分组列表")
    groups_detail: List[GroupDetail] = Field(default_factory=list, description="分组详情列表")
    storage_type: Optional[str] = Field(None, description="存储类型")
    redis_host: Optional[str] = Field(None, description="Redis 主机")
    redis_port: Optional[int] = Field(None, description="Redis 端口")
    redis_db: Optional[int] = Field(None, description="Redis 数据库索引")
    redis_key_prefix: Optional[str] = Field(None, description="Redis Key 前缀")


class ProxyConfig(BaseModel):
    """代理检测配置模型。"""

    proxy_enable_check: bool = Field(..., description="是否启用代理检测")
    proxy_check_url: str = Field(..., description="代理检测 URL")
    proxy_check_interval: int = Field(..., description="代理检测间隔（秒）")
    proxy_check_timeout: float = Field(..., description="代理检测超时（秒）")
    proxy_fail_threshold: int = Field(..., description="代理失效阈值")
