"""
MongoDB 数据库连接管理模块

提供 MongoDB 的单例连接管理、集合访问以及基础索引初始化。
"""

from pymongo import MongoClient

from app.core.config import settings


class MongoDB:
    """MongoDB 单例连接管理类。"""

    _instance = None
    _client = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self, force_reconnect: bool = False):
        """建立连接，并在首次连接或切换数据库时初始化索引。"""
        if self._client is None or force_reconnect:
            if self._client is not None:
                self._client.close()
            self._client = MongoClient(
                settings.mongo_uri,
                serverSelectionTimeoutMS=5000,
                socketTimeoutMS=10000,
                heartbeatFrequencyMS=10000,
            )

        if self._db is None or self._db.name != settings.mongo_db or force_reconnect:
            self._db = self._client[settings.mongo_db]
            self._init_indexes()
        return self._db

    def _init_indexes(self) -> None:
        """初始化需要的查询索引。"""
        try:
            # 旧版本曾创建 domain 唯一索引，规则现在允许同域多条优先级规则。
            self._db.parsing_rules.drop_index("domain_1")
        except Exception:
            pass
        try:
            self._db.parsing_rules.create_index([("domain", 1)])
            self._db.parsing_rules.create_index([("priority", -1)])
        except Exception:
            # Mongo 不可用时保留延迟连接行为，索引会在下次连接时重试。
            pass

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
            self._db = None

    @property
    def db(self):
        if self._db is None:
            self.connect()
        return self._db

    @property
    def tasks(self):
        return self.db.tasks

    @property
    def task_stats(self):
        return self.db.task_stats

    @property
    def configs(self):
        return self.db.configs

    @property
    def parsing_rules(self):
        return self.db.parsing_rules

    @property
    def nodes(self):
        return self.db.nodes

    @property
    def schedules(self):
        return self.db.schedules

    @property
    def users(self):
        return self.db.users

    @property
    def scraper_executions(self):
        return self.db.scraper_executions

    # Fork-specific collections for LLM, prompt, skill and proxy management.
    @property
    def llm_models(self):
        return self.db.llm_models

    @property
    def prompt_templates(self):
        return self.db.prompt_templates

    @property
    def proxies(self):
        return self.db.proxies

    @property
    def skills(self):
        return self.db.skills

    @property
    def skill_bundles(self):
        return self.db.skill_bundles


mongo = MongoDB()
