#!/usr/bin/env python3
"""
Memory System v1.8.0 - 多级缓存管理器
支持热点记忆缓存、查询结果缓存、向量缓存

特性：
- L1 缓存：热点记忆（TTL 1小时）
- L2 缓存：查询结果（TTL 5分钟）
- L3 缓存：嵌入向量（TTL 24小时）
- LRU 淘汰策略
- 线程安全
- 缓存命中率统计
"""

import hashlib
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class CacheEntry:
    """缓存条目"""

    key: str
    value: Any
    created_at: float
    last_access: float
    access_count: int
    ttl: Optional[float] = None

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() - self.created_at > self.ttl


class LRUCache:
    """LRU 缓存"""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._hit_count = 0
        self._miss_count = 0

    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            if key not in self.cache:
                self._miss_count += 1
                return None

            entry = self.cache[key]

            if entry.is_expired():
                del self.cache[key]
                self._miss_count += 1
                return None

            entry.last_access = time.time()
            entry.access_count += 1

            self.cache.move_to_end(key)

            self._hit_count += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        """设置缓存"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]

            while len(self.cache) >= self.max_size:
                self.cache.popitem(last=False)

            now = time.time()
            self.cache[key] = CacheEntry(key=key, value=value, created_at=now, last_access=now, access_count=1, ttl=ttl)

    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            if key in self.cache:
                del self.cache[key]
                return True
            return False

    def clear(self):
        """清空缓存"""
        with self._lock:
            self.cache.clear()

    def get_stats(self) -> dict:
        """获取缓存统计"""
        with self._lock:
            total_requests = self._hit_count + self._miss_count
            hit_rate = self._hit_count / total_requests if total_requests > 0 else 0

            total_access = sum(e.access_count for e in self.cache.values())

            hot_entries = sorted(self.cache.values(), key=lambda x: x.access_count, reverse=True)[:10]

            return {
                "size": len(self.cache),
                "max_size": self.max_size,
                "hit_count": self._hit_count,
                "miss_count": self._miss_count,
                "hit_rate": hit_rate,
                "total_access": total_access,
                "hot_entries": [
                    {
                        "key": e.key[:30] + "..." if len(e.key) > 30 else e.key,
                        "access_count": e.access_count,
                        "age_seconds": time.time() - e.created_at,
                    }
                    for e in hot_entries
                ],
            }


class MultiLevelCache:
    """多级缓存管理器"""

    DEFAULT_CONFIG = {
        "l1_size": 1000,
        "l2_size": 10000,
        "l3_size": 50000,
        "l1_ttl": 3600,
        "l2_ttl": 300,
        "l3_ttl": 86400,
    }

    def __init__(
        self,
        l1_size: int = 1000,
        l2_size: int = 10000,
        l3_size: int = 50000,
        l1_ttl: float = 3600,
        l2_ttl: float = 300,
        l3_ttl: float = 86400,
    ):
        self.l1 = LRUCache(max_size=l1_size)
        self.l2 = LRUCache(max_size=l2_size)
        self.l3 = LRUCache(max_size=l3_size)

        self.l1_ttl = l1_ttl
        self.l2_ttl = l2_ttl
        self.l3_ttl = l3_ttl

        self._total_hits = 0
        self._total_misses = 0
        self._lock = threading.RLock()

    def get_memory(self, memory_id: str) -> Optional[dict]:
        """获取记忆（L1 缓存）"""
        result = self.l1.get(memory_id)
        if result is not None:
            with self._lock:
                self._total_hits += 1
            return result

        with self._lock:
            self._total_misses += 1
        return None

    def set_memory(self, memory_id: str, memory: dict):
        """设置记忆缓存（L1）"""
        self.l1.set(memory_id, memory, ttl=self.l1_ttl)

    def get_query_result(self, query: str) -> Optional[list[dict]]:
        """获取查询结果（L2 缓存）"""
        cache_key = self._hash_key(query)
        result = self.l2.get(cache_key)
        if result is not None:
            with self._lock:
                self._total_hits += 1
            return result

        with self._lock:
            self._total_misses += 1
        return None

    def set_query_result(self, query: str, results: list[dict]):
        """设置查询结果缓存（L2）"""
        cache_key = self._hash_key(query)
        self.l2.set(cache_key, results, ttl=self.l2_ttl)

    def get_embedding(self, text: str) -> Optional[list[float]]:
        """获取嵌入向量（L3 缓存）"""
        cache_key = self._hash_key(text)
        result = self.l3.get(cache_key)
        if result is not None:
            with self._lock:
                self._total_hits += 1
            return result

        with self._lock:
            self._total_misses += 1
        return None

    def set_embedding(self, text: str, embedding: list[float]):
        """设置嵌入向量缓存（L3）"""
        cache_key = self._hash_key(text)
        self.l3.set(cache_key, embedding, ttl=self.l3_ttl)

    def invalidate_memory(self, memory_id: str):
        """使记忆缓存失效"""
        self.l1.delete(memory_id)

    def invalidate_query(self, query: str):
        """使查询缓存失效"""
        cache_key = self._hash_key(query)
        self.l2.delete(cache_key)

    def invalidate_pattern(self, pattern: str):
        """使匹配模式的缓存失效"""
        import re

        try:
            regex = re.compile(pattern)

            for cache in [self.l1, self.l2, self.l3]:
                with cache._lock:
                    keys_to_delete = [key for key in cache.cache if regex.search(key)]
                    for key in keys_to_delete:
                        del cache.cache[key]
        except re.error:
            pass

    def clear_all(self):
        """清空所有缓存"""
        self.l1.clear()
        self.l2.clear()
        self.l3.clear()

    def get_stats(self) -> dict:
        """获取缓存统计"""
        with self._lock:
            total = self._total_hits + self._total_misses
            overall_hit_rate = self._total_hits / total if total > 0 else 0

            return {
                "overall": {
                    "hit_count": self._total_hits,
                    "miss_count": self._total_misses,
                    "hit_rate": overall_hit_rate,
                },
                "l1": self.l1.get_stats(),
                "l2": self.l2.get_stats(),
                "l3": self.l3.get_stats(),
            }

    def _hash_key(self, key: str) -> str:
        """生成缓存键的哈希"""
        return hashlib.md5(key.encode("utf-8")).hexdigest()


class CacheManager:
    """缓存管理器（单例模式）"""

    _instance: Optional["CacheManager"] = None
    _lock = threading.Lock()

    def __new__(cls, _config: Optional[dict] = None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, config: Optional[dict] = None):
        if self._initialized:
            return

        config = config or MultiLevelCache.DEFAULT_CONFIG

        self.cache = MultiLevelCache(
            l1_size=config.get("l1_size", 1000),
            l2_size=config.get("l2_size", 10000),
            l3_size=config.get("l3_size", 50000),
            l1_ttl=config.get("l1_ttl", 3600),
            l2_ttl=config.get("l2_ttl", 300),
            l3_ttl=config.get("l3_ttl", 86400),
        )

        self._initialized = True

    @classmethod
    def get_instance(cls, config: Optional[dict] = None) -> "CacheManager":
        """获取单例实例"""
        return cls(config)

    @classmethod
    def reset(cls):
        """重置单例"""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.cache.clear_all()
            cls._instance = None


class CachedMemoryAccessor:
    """带缓存的记忆访问器"""

    def __init__(self, backend, cache_manager: Optional[CacheManager] = None):
        self.backend = backend
        self.cache = cache_manager or CacheManager.get_instance()

    def get_memory(self, memory_id: str) -> Optional[dict]:
        """获取记忆（带缓存）"""
        cached = self.cache.cache.get_memory(memory_id)
        if cached is not None:
            return cached

        memory = self.backend.get_memory(memory_id)
        if memory:
            self.cache.cache.set_memory(memory_id, memory)

        return memory

    def search(self, query: str, **kwargs) -> list[dict]:
        """搜索记忆（带缓存）"""
        cache_key = f"{query}:{hash(str(kwargs))}"
        cached = self.cache.cache.get_query_result(cache_key)
        if cached is not None:
            return cached

        results = self.backend.search(query, **kwargs)
        self.cache.cache.set_query_result(cache_key, results)

        return results

    def insert(self, memory: dict) -> str:
        """插入记忆"""
        memory_id = self.backend.insert(memory)

        self.cache.cache.invalidate_memory(memory_id)

        return memory_id

    def update(self, memory_id: str, updates: dict) -> bool:
        """更新记忆"""
        result = self.backend.update(memory_id, updates)

        if result:
            self.cache.cache.invalidate_memory(memory_id)

        return result

    def delete(self, memory_id: str) -> bool:
        """删除记忆"""
        result = self.backend.delete(memory_id)

        if result:
            self.cache.cache.invalidate_memory(memory_id)

        return result


def get_cache_stats() -> dict:
    """获取缓存统计（便捷函数）"""
    return CacheManager.get_instance().cache.get_stats()


def clear_cache():
    """清空缓存（便捷函数）"""
    CacheManager.get_instance().cache.clear_all()
