"""
LLM 模型配置数据模型

定义大语言模型配置相关的数据结构
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """LLM 服务商枚举"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    CUSTOM = "custom"


class LLMModelBase(BaseModel):
    """LLM 模型基础配置"""

    name: str  # 模型显示名称，如 "GPT-4o"
    provider: LLMProvider  # 服务商
    model_name: str  # 实际模型名，如 "gpt-4o"
    base_url: str  # API 地址
    api_key: Optional[str] = None  # API 密钥
    temperature: float = Field(default=0.7, ge=0, le=2)  # 温度参数
    max_tokens: int = Field(default=4096, ge=1)  # 最大输出 tokens
    supports_vision: bool = False  # 是否支持视觉/图片输入
    supports_stream: bool = False  # 是否支持流式输出
    max_retries: int = 3  # 最大重试次数
    is_default: bool = False  # 是否默认模型
    is_enabled: bool = True  # 是否启用


class LLMModelCreate(LLMModelBase):
    """创建 LLM 模型配置请求"""

    pass


class LLMModelUpdate(BaseModel):
    """更新 LLM 模型配置请求"""

    name: Optional[str] = None
    provider: Optional[LLMProvider] = None
    model_name: Optional[str] = None
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: Optional[float] = Field(default=None, ge=0, le=2)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    supports_vision: Optional[bool] = None
    supports_stream: Optional[bool] = None
    max_retries: Optional[int] = None
    is_default: Optional[bool] = None
    is_enabled: Optional[bool] = None


class LLMModelResponse(LLMModelBase):
    """LLM 模型配置响应"""

    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    class Config:
        populate_by_name = True


class LLMModelListResponse(BaseModel):
    """LLM 模型列表响应"""

    items: List[LLMModelResponse]
    total: int


class LLMTestRequest(BaseModel):
    """测试 LLM 模型连接请求"""

    prompt: str = "Hello, please respond with 'OK' if you can receive this message."


class LLMTestResponse(BaseModel):
    """测试 LLM 模型连接响应"""

    success: bool
    message: str
    response: Optional[str] = None
    latency_ms: Optional[float] = None


# ============ Agent 相关模型 ============


class AgentStatus(str, Enum):
    """Agent 处理状态枚举"""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentResult(BaseModel):
    """Agent 识别结果模型"""

    status: AgentStatus = AgentStatus.PENDING  # 处理状态
    model_id: Optional[str] = None  # 使用的模型 ID
    model_name: Optional[str] = None  # 使用的模型名称
    user_prompt: Optional[str] = None  # 用户的提取要求
    system_prompt: Optional[str] = None  # 系统提示词内容
    extracted_items: Optional[List[Dict[str, Any]]] = None  # 提取的结构化数据
    raw_response: Optional[str] = None  # LLM 原始响应
    token_usage: Optional[Dict[str, Any]] = None  # tokens 使用量，可能包含嵌套结构
    processing_time: Optional[float] = None  # 处理耗时（秒）
    error: Optional[str] = None  # 错误信息
    parallel_info: Optional[Dict[str, Any]] = None  # 并行提取信息 (chunks, batch_size 等)
    cache_hits: int = 0  # 缓存命中块数
    total_chunks: int = 0  # 总块数
    created_at: Optional[datetime] = None  # 开始处理时间
    completed_at: Optional[datetime] = None  # 完成时间
