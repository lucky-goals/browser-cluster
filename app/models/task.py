"""任务请求、结果和状态模型。"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from app.models.llm import AgentResult


class StorageType(str, Enum):
    MONGO = "mongo"
    OSS = "oss"


class ProxyConfig(BaseModel):
    """浏览器代理配置。"""

    server: str
    username: Optional[str] = None
    password: Optional[str] = None


class InteractionStep(BaseModel):
    """浏览器交互或技能步骤。"""

    action: str
    params: Dict[str, Any] = Field(default_factory=dict)


class ScrapeParams(BaseModel):
    """抓取参数，同时覆盖 Playwright、DrissionPage 和 Agent 配置。"""

    engine: str = "playwright"
    wait_for: str = "networkidle"
    wait_time: int = 3000
    timeout: int = 30000
    selector: Optional[str] = None
    screenshot: bool = False
    is_fullscreen: bool = False
    block_images: bool = False
    block_media: bool = False
    user_agent: Optional[str] = None
    viewport: Dict[str, int] = Field(default_factory=lambda: {"width": 1920, "height": 1080})
    proxy: Optional[Union[ProxyConfig, Dict[str, Any]]] = None
    proxy_pool_group: Optional[str] = None
    cookies: Optional[Union[str, List[Dict[str, Any]], Dict[str, str]]] = None
    cookie_group: Optional[str] = None
    return_cookies: bool = False
    stealth: bool = True
    intercept_apis: Optional[List[str]] = None
    intercept_continue: bool = False
    save_html: bool = True
    parser: Optional[str] = None
    parser_config: Optional[Dict[str, Any]] = None
    storage_type: StorageType = StorageType.MONGO
    mongo_collection: Optional[str] = None
    oss_path: Optional[str] = None
    max_retries: int = 0
    matched_rule: Optional[str] = None

    # Session/list scraping options
    max_pages: int = 1
    list_xpath: Optional[str] = None
    title_xpath: Optional[str] = None
    link_xpath: Optional[str] = None
    time_xpath: Optional[str] = None
    pagination_next_xpath: Optional[str] = None
    no_images: bool = True
    no_css: bool = True

    # Fork Agent and skill options
    interaction_steps: Optional[List[InteractionStep]] = None
    agent_enabled: bool = False
    agent_model_id: Optional[str] = None
    agent_system_prompt: Optional[str] = None
    agent_prompt: Optional[str] = None
    agent_parallel_enabled: bool = False
    agent_parallel_batch_size: int = 10


class CacheConfig(BaseModel):
    enabled: bool = True
    ttl: int = 3600


class ScrapeRequest(BaseModel):
    url: str
    params: ScrapeParams = Field(default_factory=ScrapeParams)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    priority: int = 1
    schedule_id: Optional[str] = None
    retry_enabled: Optional[bool] = None
    max_retries: Optional[int] = None
    execution_type: str = "production"


class TaskMetadata(BaseModel):
    title: Optional[str] = None
    url: str
    actual_url: Optional[str] = None
    load_time: float
    timestamp: datetime = Field(default_factory=datetime.now)
    status_code: Optional[int] = None
    engine: Optional[str] = None
    proxy: Optional[str] = None


class ScrapedResult(BaseModel):
    # HTML may be omitted when OSS storage is selected or save_html is false.
    html: Optional[str] = None
    screenshot: Optional[str] = None
    oss_html: Optional[str] = None
    oss_screenshot: Optional[str] = None
    storage_type: str = "mongo"
    metadata: Optional[TaskMetadata] = None
    cookies: Optional[Union[str, Dict[str, str], List[Dict[str, Any]]]] = None
    intercepted_apis: Optional[Dict[str, List[Dict[str, Any]]]] = None
    parsed_data: Optional[Union[Dict[str, Any], List[Any]]] = None
    agent_result: Optional[AgentResult] = None
    skill_results: Optional[Dict[str, Any]] = None
    visual_content: Optional[str] = None
    html_cached: bool = False
    agent_cached: bool = False


class TaskError(BaseModel):
    message: str
    stack: Optional[str] = None
    type: Optional[str] = None


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class RetryRequest(BaseModel):
    url: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    cache: Optional[Dict[str, Any]] = None


class TaskModel(BaseModel):
    task_id: Optional[str] = None
    url: str
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 1
    params: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[ScrapedResult] = None
    error: Optional[TaskError] = None
    cache_key: Optional[str] = None
    cached: bool = False
    html_cached: bool = False
    agent_cached: bool = False
    node_id: Optional[str] = None
    retry_count: int = 0
    retry_enabled: bool = True
    max_retries: int = 3
    execution_type: str = "production"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class TaskResponse(BaseModel):
    task_id: str
    url: str
    node_id: Optional[str] = None
    status: str
    retry_count: int = 0
    retry_enabled: bool = True
    max_retries: int = 3
    execution_type: str = "production"
    params: Optional[Dict[str, Any]] = None
    priority: Optional[int] = 1
    cache: Optional[Dict[str, Any]] = None
    result: Optional[ScrapedResult] = None
    error: Optional[TaskError] = None
    cached: bool = False
    html_cached: bool = False
    agent_cached: bool = False
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class BatchScrapeRequest(BaseModel):
    tasks: List[ScrapeRequest]


class BatchScrapeResponse(BaseModel):
    task_ids: List[str]


class BatchDeleteRequest(BaseModel):
    task_ids: List[str]


class ProxyTestRequest(BaseModel):
    proxy: ProxyConfig


class StatsResponse(BaseModel):
    today: Dict[str, Any]
    yesterday: Dict[str, Any]
    trends: Dict[str, float]
    queue: Dict[str, Any]
    history: List[Dict[str, Any]]
    today_hourly: Optional[List[Dict[str, Any]]] = None
    nodes: Optional[Dict[str, Any]] = None
    system_load: Optional[float] = 0.0
    total_scraped: Optional[int] = 0
