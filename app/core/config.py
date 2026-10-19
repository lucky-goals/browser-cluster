"""
应用配置管理模块

使用 pydantic_settings 从环境变量或 .env 文件加载配置。
SQLite 中的配置只覆盖可热更新的应用参数；数据库、缓存和消息队列连接
信息始终以环境变量为准，避免运行中的连接被后台配置意外切换。
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类。"""

    # FastAPI
    app_name: str = Field(default="BrowserCluster", description="应用名称")
    app_version: str = Field(default="1.0.0", description="应用版本")
    debug: bool = Field(default=True, description="调试模式")
    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=8000, description="监听端口")

    # MongoDB
    mongo_uri: str = Field(default="mongodb://localhost:27017/", description="MongoDB 连接地址")
    mongo_db: str = Field(default="browser_cluster", description="MongoDB 数据库名称")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", description="任务队列 Redis 连接地址")
    redis_cache_url: str = Field(default="redis://localhost:6379/1", description="结果缓存 Redis 连接地址")

    # RabbitMQ
    rabbitmq_url: str = Field(default="amqp://guest:guest@localhost:5672/", description="RabbitMQ 连接地址")
    rabbitmq_queue: str = Field(default="scrape_tasks", description="任务队列名称")
    rabbitmq_exchange: str = Field(default="browser_cluster", description="交换机名称")
    rabbitmq_heartbeat: int = Field(default=60, description="RabbitMQ 心跳间隔（秒）")
    rabbitmq_blocked_timeout: int = Field(default=300, description="RabbitMQ 阻塞超时（秒）")

    # Browser
    browser_type: str = Field(default="chromium", description="浏览器类型")
    browser_engine: str = Field(default="playwright", description="浏览器引擎：playwright 或 drissionpage")
    headless: bool = Field(default=True, description="是否无头模式")
    block_images: bool = Field(default=False, description="是否拦截图片")
    block_media: bool = Field(default=False, description="是否拦截媒体")
    default_timeout: int = Field(default=30000, description="默认超时时间（毫秒）")
    default_wait_for: str = Field(default="networkidle", description="默认等待策略")
    default_viewport_width: int = Field(default=1920, description="默认视口宽度")
    default_viewport_height: int = Field(default=1080, description="默认视口高度")
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
        description="默认 User-Agent",
    )
    browser_idle_timeout: int = Field(default=1800, description="浏览器空闲超时（秒）")
    stealth_mode: bool = Field(default=True, description="默认启用反检测")
    proxy_test_url: str = Field(default="https://www.github.com", description="代理测试地址")
    agent_max_html_length: int = Field(default=200000, description="Agent 提取时最大 HTML 长度")

    # Worker
    worker_concurrency: int = Field(default=3, description="Worker 并发数")
    retry_enabled: bool = Field(default=True, description="是否启用自动重试")
    max_retries: int = Field(default=3, description="最大重试次数")
    retry_delay: int = Field(default=5, description="重试延迟（秒）")

    # Cache
    cache_enabled: bool = Field(default=True, description="是否启用缓存")
    default_cache_ttl: int = Field(default=3600, description="默认缓存 TTL（秒）")

    # Node
    node_id: str = Field(default="node-1", description="节点 ID")
    node_type: str = Field(default="worker", description="节点类型")
    heartbeat_interval: int = Field(default=30, description="心跳间隔（秒）")
    max_node_auto_retries: int = Field(default=5, description="节点自动重启最大次数")

    # LLM / parser
    llm_api_base: str = Field(default="https://api.openai.com/v1", description="大模型 API 地址")
    llm_api_key: str = Field(default="", description="大模型 API Key")
    llm_model: str = Field(default="gpt-3.5-turbo", description="大模型名称")

    # OSS
    oss_enabled: bool = Field(default=False, description="是否启用 OSS")
    oss_endpoint: str = Field(default="oss-cn-hangzhou.aliyuncs.com", description="OSS Endpoint")
    oss_access_key_id: str = Field(default="", description="OSS AccessKey ID")
    oss_access_key_secret: str = Field(default="", description="OSS AccessKey Secret")
    oss_bucket_name: str = Field(default="", description="OSS Bucket 名称")
    oss_bucket_domain: str = Field(default="", description="OSS 自定义域名")

    # Proxy pool
    proxy_enable_check: bool = Field(default=True, description="是否启用代理检测")
    proxy_redis_db: int = Field(default=6, description="代理池 Redis DB")
    proxy_redis_key_prefix: str = Field(default="proxy_pool", description="代理池 Redis key 前缀")
    proxy_check_url: str = Field(default="https://myip.ipip.net/", description="代理检测地址")
    proxy_check_interval: int = Field(default=300, description="代理检测间隔（秒）")
    proxy_check_timeout: float = Field(default=10.0, description="代理检测超时（秒）")
    proxy_fail_threshold: int = Field(default=3, description="代理失效阈值")

    # Cookie pool
    cookie_enable_check: bool = Field(default=True, description="是否启用 Cookie 检测")
    cookie_redis_db: int = Field(default=7, description="Cookie 池 Redis DB")
    cookie_redis_key_prefix: str = Field(default="cookie_pool", description="Cookie 池 Redis key 前缀")
    cookie_check_interval: int = Field(default=300, description="Cookie 检测间隔（秒）")
    cookie_check_timeout: float = Field(default=15.0, description="Cookie 检测超时（秒）")
    cookie_fail_threshold: int = Field(default=3, description="Cookie 失效阈值")
    cookie_default_rate_limit: int = Field(default=60, description="Cookie 默认频率限制")

    # Logging / security
    log_level: str = Field(default="INFO", description="日志级别")
    log_file: str = Field(default="logs/app.log", description="日志文件")
    secret_key: str = Field(default="your-secret-key-here", description="Token 签名密钥")
    algorithm: str = Field(default="HS256", description="Token 签名算法")
    access_token_expire_minutes: int = Field(default=60 * 24 * 7, description="Token 有效期（分钟）")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def load_from_db(self) -> None:
        """同步 SQLite 中的热配置，并在删除配置后恢复基准值。"""
        try:
            from app.db.sqlite import sqlite_db

            db_configs = {item["key"]: item["value"] for item in sqlite_db.get_all_configs()}
            base_settings = type(self)()
            # 连接端点属于部署环境，永远不由管理页面覆盖。
            infrastructure_keys = {
                "mongo_uri",
                "mongo_db",
                "redis_url",
                "redis_cache_url",
                "rabbitmq_url",
            }
            updated_count = 0
            reset_count = 0

            for key in self.model_fields:
                if key in infrastructure_keys:
                    continue
                base_value = getattr(base_settings, key)
                if key in db_configs:
                    value = db_configs[key]
                    target_type = type(base_value)
                    try:
                        if target_type is bool:
                            new_value = value if isinstance(value, bool) else str(value).lower() in {
                                "true", "1", "yes", "on"
                            }
                        elif target_type is int:
                            new_value = int(value)
                        elif target_type is float:
                            new_value = float(value)
                        else:
                            new_value = str(value)
                        setattr(self, key, new_value)
                        updated_count += 1
                    except (TypeError, ValueError):
                        setattr(self, key, base_value)
                elif getattr(self, key) != base_value:
                    setattr(self, key, base_value)
                    reset_count += 1

            if updated_count or reset_count:
                print(
                    f"Configuration sync complete: {updated_count} updated from DB, "
                    f"{reset_count} reset to defaults"
                )
        except Exception as exc:
            print(f"Error loading configs from DB: {exc}")


settings = Settings()
