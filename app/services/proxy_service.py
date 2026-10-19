import httpx
import asyncio
import random
import logging
from typing import List, Optional, Union, Dict
from datetime import datetime
from app.db.redis import redis_client
from app.models.proxy import Proxy, ProxyCreate, ProxyUpdate, ProxyFilter, ProxyConfig
from app.db.sqlite import sqlite_db
from app.core.config import settings

logger = logging.getLogger(__name__)

class ProxyService:
    """代理池服务类"""
    
    def __init__(self, storage_type: str = "set"):
        """
        初始化代理服务
        :param storage_type: 存储类型, 'set' 或 'list'
        """
        # 强制从数据库重新加载配置，确保单例初始化时使用最新配置
        settings.load_from_db()
        
        self.storage_type = storage_type
        self._config_callbacks = []

    def register_config_callback(self, callback):
        """注册配置变更回调"""
        if callback not in self._config_callbacks:
            self._config_callbacks.append(callback)

    @property
    def base_key(self) -> str:
        return settings.proxy_redis_key_prefix

    @property
    def details_key(self) -> str:
        return f"{self.base_key}:details"

    @property
    def pool_set_key(self) -> str:
        return f"{self.base_key}:pool:set"

    @property
    def pool_list_key(self) -> str:
        return f"{self.base_key}:pool:list"

    @property
    def stats_key(self) -> str:
        return f"{self.base_key}:stats"

    @property
    def redis(self):
        return redis_client.proxy  # 使用代理池专用 Redis 实例

    async def add_proxy(self, proxy_data: ProxyCreate) -> Proxy:
        """添加代理"""
        proxy_id = f"{proxy_data.ip}:{proxy_data.port}"
        proxy = Proxy(
            id=proxy_id,
            **proxy_data.model_dump()
        )
        
        # 保存详情
        self.redis.hset(self.details_key, proxy_id, proxy.to_redis_val())
        
        # 如果是 active 状态，添加到池中
        if proxy.status == "active":
            await self._add_to_pool(proxy_id, proxy.group)
            
        return proxy

    async def get_proxy(self, proxy_id: str) -> Optional[Proxy]:
        """获取代理详情"""
        val = self.redis.hget(self.details_key, proxy_id)
        if val:
            return Proxy.from_redis_val(val)
        return None

    async def update_proxy(self, proxy_id: str, update_data: ProxyUpdate) -> Optional[Proxy]:
        """更新代理"""
        proxy = await self.get_proxy(proxy_id)
        if not proxy:
            return None
            
        old_group = proxy.group
        old_status = proxy.status
        
        # 更新字段
        data = update_data.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(proxy, key, value)
            
        new_group = proxy.group
        new_status = proxy.status
        
        # 处理状态和分组变更
        if old_status == "active" and new_status == "inactive":
            # 状态从 active 变为 inactive，从池中移除
            await self._remove_from_pool(proxy_id, old_group)
        elif old_status == "inactive" and new_status == "active":
            # 状态从 inactive 变为 active，添加到新池中
            await self._add_to_pool(proxy_id, new_group)
        elif old_status == "active" and new_status == "active":
            # 状态保持 active，但分组可能变更
            if old_group != new_group:
                # 移除旧分组，添加新分组 (全局池不用动，因为 ID 没变)
                await self._remove_from_pool(proxy_id, old_group)
                await self._add_to_pool(proxy_id, new_group)
            
        # 保存更新后的详情
        self.redis.hset(self.details_key, proxy_id, proxy.to_redis_val())
        return proxy

    async def delete_proxy(self, proxy_id: str) -> bool:
        """删除代理"""
        # 从池中移除
        await self._remove_from_pool(proxy_id)
        # 删除详情
        return self.redis.hdel(self.details_key, proxy_id) > 0

    async def bulk_delete_proxies(self, proxy_ids: List[str]) -> int:
        """批量删除代理"""
        count = 0
        for proxy_id in proxy_ids:
            if await self.delete_proxy(proxy_id):
                count += 1
        return count

    async def list_proxies(self, filter_data: Optional[ProxyFilter] = None, skip: int = 0, limit: int = 100) -> Dict:
        """列出代理"""
        # 获取所有详情
        all_details = self.redis.hgetall(self.details_key)
        proxies = []
        for val in all_details.values():
            proxy = Proxy.from_redis_val(val)
            
            # 应用过滤
            if filter_data:
                if filter_data.group and proxy.group != filter_data.group:
                    continue
                if filter_data.status and proxy.status != filter_data.status:
                    continue
                if filter_data.protocol and proxy.protocol != filter_data.protocol:
                    continue
            
            proxies.append(proxy)
        
        # 按优先级排序
        proxies.sort(key=lambda x: x.priority, reverse=True)
        
        total = len(proxies)
        # 分页
        paged_proxies = proxies[skip : skip + limit]
        
        return {
            "total": total,
            "items": paged_proxies
        }

    async def get_random_proxy(self, group: str = "default") -> Optional[Proxy]:
        """
        随机获取一个代理
        
        Args:
            group: 代理分组名称，默认为 "default"
        """
        proxy_id = None
        
        # 构建分组特定的 Key
        suffix = "set" if self.storage_type == "set" else "list"
        group_pool_key = f"{self.base_key}:pool:{suffix}:{group}"
        
        if self.storage_type == "set":
            # 从分组集合中随机获取
            proxy_id = self.redis.srandmember(group_pool_key)
            # 如果分组中没有，且不是 default，则尝试从全局池中获取 (可选，但通常按分组匹配更严格)
            if not proxy_id and group == "default":
                proxy_id = self.redis.srandmember(self.pool_set_key)
        else:
            # List 模式下
            length = self.redis.llen(group_pool_key)
            if length > 0:
                idx = random.randint(0, length - 1)
                proxy_id = self.redis.lindex(group_pool_key, idx)
            elif group == "default":
                length = self.redis.llen(self.pool_list_key)
                if length > 0:
                    idx = random.randint(0, length - 1)
                    proxy_id = self.redis.lindex(self.pool_list_key, idx)
        
        if proxy_id:
            proxy = await self.get_proxy(proxy_id)
            if proxy:
                # 校验分组是否匹配 (防止池中数据过期或不一致)
                if proxy.group != group and group != "default":
                    logger.warning(f"Proxy {proxy_id} group mismatch: expected {group}, got {proxy.group}")
                    # 如果不匹配，递归尝试 (或者直接返回不匹配)
                    # 这里为了简单直接返回，后续通过 _add_to_pool 保证一致性
                
                # 更新统计
                proxy.last_used_at = datetime.now()
                self.redis.hset(self.details_key, proxy_id, proxy.to_redis_val())
                return proxy
        return None

    async def bulk_import(self, proxies_data: List[ProxyCreate]) -> int:
        """批量导入代理"""
        count = 0
        for data in proxies_data:
            await self.add_proxy(data)
            count += 1
        return count

    async def bulk_export(self) -> List[ProxyCreate]:
        """批量导出代理"""
        result = await self.list_proxies(limit=10000)  # 导出时给一个较大的限制
        return [ProxyCreate(**p.model_dump()) for p in result["items"]]

    async def _remove_from_pool(self, proxy_id: str, group: Optional[str] = None):
        """从池中移除"""
        # 获取代理详情以确定其分组
        if not group:
            proxy = await self.get_proxy(proxy_id)
            if proxy:
                group = proxy.group
        
        # 移除全局池
        if self.storage_type == "set":
            self.redis.srem(self.pool_set_key, proxy_id)
        else:
            self.redis.lrem(self.pool_list_key, 0, proxy_id)
            
        # 移除分组池
        if group:
            suffix = "set" if self.storage_type == "set" else "list"
            group_pool_key = f"{self.base_key}:pool:{suffix}:{group}"
            if self.storage_type == "set":
                self.redis.srem(group_pool_key, proxy_id)
            else:
                self.redis.lrem(group_pool_key, 0, proxy_id)

    async def _add_to_pool(self, proxy_id: str, group: Optional[str] = None):
        """添加到池中"""
        # 获取代理详情以确定其分组
        if not group:
            proxy = await self.get_proxy(proxy_id)
            if proxy:
                group = proxy.group
                
        # 添加到全局池
        if self.storage_type == "set":
            self.redis.sadd(self.pool_set_key, proxy_id)
        else:
            # 避免重复
            self.redis.lrem(self.pool_list_key, 0, proxy_id)
            self.redis.rpush(self.pool_list_key, proxy_id)
            
        # 添加到分组池
        if group:
            suffix = "set" if self.storage_type == "set" else "list"
            group_pool_key = f"{self.base_key}:pool:{suffix}:{group}"
            if self.storage_type == "set":
                self.redis.sadd(group_pool_key, proxy_id)
            else:
                # 避免重复
                self.redis.lrem(group_pool_key, 0, proxy_id)
                self.redis.rpush(group_pool_key, proxy_id)

    async def check_proxy(self, proxy: Proxy) -> bool:
        """检测代理有效性"""
        if not settings.proxy_enable_check:
            # 如果关闭了检测，认为所有代理都是 active 的
            if proxy.status != "active":
                proxy.status = "active"
                await self._add_to_pool(proxy.id, proxy.group)
                self.redis.hset(self.details_key, proxy.id, proxy.to_redis_val())
            return True

        test_url = settings.proxy_check_url
        try:
            # 如果有账密，需要构造带认证的代理 URL
            if proxy.username and proxy.password:
                proxy_url = f"{proxy.protocol}://{proxy.username}:{proxy.password}@{proxy.ip}:{proxy.port}"
            else:
                proxy_url = proxy.server
            
            async with httpx.AsyncClient(
                proxy=proxy_url, 
                timeout=settings.proxy_check_timeout,
                verify=False,  # 某些代理在处理 HTTPS 时可能会有证书问题，检测时可以放宽
                trust_env=False, # 禁用环境变量中的代理，确保检测的是目标代理
                headers={
                    "User-Agent": settings.user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            ) as client:
                response = await client.get(test_url)
                if response.status_code == 200:
                    proxy.fail_count = 0
                    proxy.status = "active"
                    await self._add_to_pool(proxy.id, proxy.group)
                else:
                    logger.warning(f"Proxy check returned status {response.status_code} for {proxy.id}")
                    proxy.fail_count += 1
                    if proxy.fail_count >= settings.proxy_fail_threshold:
                        proxy.status = "inactive"
                        await self._remove_from_pool(proxy.id, proxy.group)
                
        except Exception as e:
            logger.error(f"Proxy check failed for {proxy.id} ({proxy.protocol}): {str(e)}")
            proxy.fail_count += 1
            if proxy.fail_count >= settings.proxy_fail_threshold:
                proxy.status = "inactive"
                await self._remove_from_pool(proxy.id, proxy.group)
        
        proxy.last_check_at = datetime.now()
        self.redis.hset(self.details_key, proxy.id, proxy.to_redis_val())
        return proxy.status == "active"

    async def check_all_proxies(self):
        """检测所有代理"""
        result = await self.list_proxies(limit=10000)
        proxies = result["items"]
        tasks = [self.check_proxy(p) for p in proxies]
        if tasks:
            await asyncio.gather(*tasks)
            logger.info(f"Finished checking {len(tasks)} proxies")

    async def update_stats(self, proxy_id: str, success: bool):
        """
        手动更新代理使用统计
        
        Args:
            proxy_id: 代理 ID (ip:port)
            success: 是否成功
        """
        proxy = await self.get_proxy(proxy_id)
        if not proxy:
            return
            
        proxy.total_count += 1
        if success:
            proxy.success_count += 1
        else:
            # 失败处理：如果连续失败次数达到阈值，设置为 inactive
            # 注意：这里的失败是指业务层面的失败（如被反爬），不一定是网络不通
            # 我们先仅增加失败计数，由 check_proxy 决定是否下架
            pass
            
        self.redis.hset(self.details_key, proxy_id, proxy.to_redis_val())

    async def get_stats(self) -> Dict:
        """获取统计信息"""
        result = await self.list_proxies(limit=10000)
        proxies = result["items"]
        
        # 计算每个分组的统计信息
        group_map = {}
        for p in proxies:
            if p.group not in group_map:
                group_map[p.group] = {"name": p.group, "total": 0, "active": 0}
            
            group_map[p.group]["total"] += 1
            if p.status == "active":
                group_map[p.group]["active"] += 1
        
        # 转换为列表并按名称排序
        groups_detail = sorted(group_map.values(), key=lambda x: x["name"])
        
        return {
            "total": len(proxies),
            "active": len([p for p in proxies if p.status == "active"]),
            "inactive": len([p for p in proxies if p.status == "inactive"]),
            "groups": [g["name"] for g in groups_detail],  # 保持向后兼容
            "groups_detail": groups_detail,
            "storage_type": self.storage_type,
            "redis_db": settings.proxy_redis_db,
            "redis_key_prefix": self.base_key
        }

    async def get_config(self) -> ProxyConfig:
        """获取代理检测配置"""
        return ProxyConfig(
            proxy_enable_check=settings.proxy_enable_check,
            proxy_check_url=settings.proxy_check_url,
            proxy_check_interval=settings.proxy_check_interval,
            proxy_check_timeout=settings.proxy_check_timeout,
            proxy_fail_threshold=settings.proxy_fail_threshold
        )

    async def update_config(self, config: ProxyConfig) -> bool:
        """更新代理检测配置"""
        data = config.model_dump()
        for key, value in data.items():
            sqlite_db.set_config(key, value)
        
        # 重新加载配置
        settings.load_from_db()
        
        # 触发回调
        for cb in self._config_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb()
                else:
                    cb()
            except Exception as e:
                logger.error(f"Error in proxy config callback: {e}")
                
        return True

# 单例
proxy_service = ProxyService()
