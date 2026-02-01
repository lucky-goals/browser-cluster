"""
Redis 缓存服务模块

提供任务结果缓存功能
"""
import hashlib
import json
import logging
from typing import Optional, Any
from app.db.redis import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)

def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    from datetime import datetime
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


class CacheService:
    """缓存服务类"""

    def generate_cache_key(self, url: str, params: dict) -> str:
        """
        生成通用缓存键 (全量参数)

        Args:
            url: 目标 URL
            params: 抓取参数

        Returns:
            str: MD5 哈希后的缓存键
        """
        # 将参数转换为排序后的 JSON 字符串
        params_str = json.dumps(params, sort_keys=True, default=json_serial)
        # 组合 URL 和参数
        cache_input = f"{url}:{params_str}"
        # 生成 MD5 哈希
        return hashlib.md5(cache_input.encode()).hexdigest()

    def generate_html_cache_key(self, url: str, params: dict) -> str:
        """
        生成网页抓取缓存键 (排除 Agent 提示词等 AI 相关参数)
        """
        # 排除 AI 相关参数
        html_params = params.copy()
        ai_keys = [
            "agent_enabled", "agent_model_id", "agent_prompt", 
            "agent_system_prompt", "agent_parallel_enabled", 
            "agent_parallel_batch_size"
        ]
        for key in ai_keys:
            html_params.pop(key, None)
            
        params_str = json.dumps(html_params, sort_keys=True, default=json_serial)
        cache_input = f"html:{url}:{params_str}"
        return hashlib.md5(cache_input.encode()).hexdigest()

    def generate_llm_cache_key(self, content: str, model_id: str, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        生成 AI 识别结果的缓存键
        Key 基于：内容哈希、模型 ID、提示词内容
        """
        content_hash = hashlib.md5(content.encode()).hexdigest()
        input_data = {
            "content_hash": content_hash,
            "model_id": model_id,
            "prompt": prompt,
            "system_prompt": system_prompt
        }
        input_str = json.dumps(input_data, sort_keys=True, default=json_serial)
        cache_input = f"llm:{input_str}"
        return hashlib.md5(cache_input.encode()).hexdigest()

    async def get(self, url: str, params: dict) -> Optional[dict]:
        """
        从缓存获取数据 (通用/全量)
        """
        if not settings.cache_enabled:
            return None

        cache_key = self.generate_cache_key(url, params)
        return await self.get_by_key(cache_key)

    async def get_html(self, url: str, params: dict) -> Optional[dict]:
        """
        获取网页抓取缓存
        """
        if not settings.cache_enabled:
            return None
        cache_key = self.generate_html_cache_key(url, params)
        return await self.get_by_key(cache_key)

    async def get_llm(self, content: str, model_id: str, prompt: str, system_prompt: Optional[str] = None) -> Optional[dict]:
        """
        获取 AI 识别缓存
        """
        if not settings.cache_enabled:
            return None
        cache_key = self.generate_llm_cache_key(content, model_id, prompt, system_prompt)
        return await self.get_by_key(cache_key)

    async def get_by_key(self, cache_key: str) -> Optional[dict]:
        """根据 Key 获取缓存"""
        try:
            cached_data = redis_client.cache.get(cache_key)
            if cached_data:
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Cache get_by_key error: {e}")
        return None

    async def set(
        self,
        url: str,
        params: dict,
        data: dict,
        ttl: Optional[int] = None,
        task_id: Optional[str] = None
    ) -> bool:
        """设置全量缓存"""
        if not settings.cache_enabled:
            return False
        cache_key = self.generate_cache_key(url, params)
        return await self.set_by_key(cache_key, data, ttl, task_id)

    async def set_html(
        self,
        url: str,
        params: dict,
        data: dict,
        ttl: Optional[int] = None,
        task_id: Optional[str] = None
    ) -> bool:
        """设置网页抓取缓存"""
        if not settings.cache_enabled:
            return False
        cache_key = self.generate_html_cache_key(url, params)
        return await self.set_by_key(cache_key, data, ttl, task_id)

    async def set_llm(
        self,
        content: str,
        model_id: str,
        prompt: str,
        data: dict,
        system_prompt: Optional[str] = None,
        ttl: Optional[int] = None,
        task_id: Optional[str] = None
    ) -> bool:
        """设置 AI 识别缓存"""
        if not settings.cache_enabled:
            return False
        cache_key = self.generate_llm_cache_key(content, model_id, prompt, system_prompt)
        return await self.set_by_key(cache_key, data, ttl, task_id)

    async def set_by_key(
        self,
        cache_key: str,
        data: dict,
        ttl: Optional[int] = None,
        task_id: Optional[str] = None
    ) -> bool:
        """通用设置缓存逻辑"""
        # 使用指定的 TTL 或默认 TTL
        ttl = ttl or settings.default_cache_ttl

        try:
            # 如果提供了 task_id，将其添加到缓存数据中
            if task_id:
                data["task_id"] = task_id
                
            # 设置缓存，带过期时间
            redis_client.cache.setex(
                cache_key,
                ttl,
                json.dumps(data, default=json_serial)
            )
            return True
        except Exception as e:
            logger.error(f"Cache set_by_key error: {e}")
            return False

    async def delete(self, url: str, params: dict) -> bool:
        """
        删除缓存

        Args:
            url: 目标 URL
            params: 抓取参数

        Returns:
            bool: 是否成功删除缓存
        """
        cache_key = self.generate_cache_key(url, params)

        try:
            redis_client.cache.delete(cache_key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False

    async def delete_by_key(self, cache_key: str) -> bool:
        """
        根据缓存键删除缓存

        Args:
            cache_key: 缓存键

        Returns:
            bool: 是否成功删除缓存
        """
        try:
            redis_client.cache.delete(cache_key)
            return True
        except Exception as e:
            logger.error(f"Cache delete by key error: {e}")
            return False

    async def clear_all(self) -> bool:
        """
        清空所有缓存

        Returns:
            bool: 是否成功清空缓存
        """
        try:
            redis_client.cache.flushdb()
            return True
        except Exception as e:
            logger.error(f"Cache clear error: {e}")
            return False


# 全局缓存服务实例
cache_service = CacheService()
