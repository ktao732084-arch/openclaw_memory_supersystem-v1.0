#!/usr/bin/env python3
"""
Memory System v1.8.0 - 百万级扩展后端
整合分片索引、多级缓存、异步索引器

特性：
- 自动选择后端：小数据用 SQLite，大数据用分片索引
- 透明缓存：自动缓存热点记忆和查询结果
- 异步索引：后台更新向量索引
- 向量检索：支持 Qdrant/Pinecone
"""

import json
import threading
from pathlib import Path
from typing import Any, Optional

try:
    from async_indexer import AsyncIndexer, VectorIndexer, create_vector_db
    from cache_manager import CacheManager
    from sharded_index import ShardedIndexManager

    SCALING_AVAILABLE = True
except ImportError:
    SCALING_AVAILABLE = False

try:
    from sqlite_backend import SQLiteBackend

    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False


class ScalingConfig:
    """扩展配置"""

    DEFAULT_CONFIG = {
        "enabled": True,
        "shard_size": 10000,
        "cache": {"l1_size": 1000, "l2_size": 10000, "l3_size": 50000, "l1_ttl": 3600, "l2_ttl": 300, "l3_ttl": 86400},
        "async_indexer": {"batch_size": 100, "flush_interval": 5.0, "max_queue_size": 10000, "max_workers": 4},
        "vector_db": {"enabled": False, "type": "qdrant", "host": "localhost", "port": 6333, "collection": "memories"},
        "thresholds": {"auto_scale": 50000},
    }

    @classmethod
    def load(cls, config_path: Path) -> dict:
        """加载配置"""
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
                return cls._merge_config(config.get("scaling", {}))
        return cls.DEFAULT_CONFIG.copy()

    @classmethod
    def _merge_config(cls, user_config: dict) -> dict:
        """合并配置"""
        result = cls.DEFAULT_CONFIG.copy()
        for key, value in user_config.items():
            if isinstance(value, dict) and key in result:
                result[key] = {**result[key], **value}
            else:
                result[key] = value
        return result


class ScaledBackend:
    """扩展后端"""

    def __init__(self, memory_dir: Path, config: Optional[dict] = None):
        self.memory_dir = Path(memory_dir)
        self.config = config or ScalingConfig.DEFAULT_CONFIG
        self.enabled = self.config.get("enabled", True) and SCALING_AVAILABLE

        self._lock = threading.RLock()

        self._init_backends()

    def _init_backends(self):
        """初始化后端"""
        if not self.enabled:
            if SQLITE_AVAILABLE:
                self.sqlite_backend = SQLiteBackend(self.memory_dir)
            else:
                raise RuntimeError("没有可用的后端")
            self.sharded_backend = None
            self.cache = None
            self.async_indexer = None
            self.vector_indexer = None
            return

        cache_config = self.config.get("cache", {})
        self.cache = CacheManager.get_instance(cache_config)

        shard_dir = self.memory_dir / "shards"
        shard_size = self.config.get("shard_size", 10000)
        self.sharded_backend = ShardedIndexManager(shard_dir, shard_size)

        if SQLITE_AVAILABLE:
            self.sqlite_backend = SQLiteBackend(self.memory_dir)
        else:
            self.sqlite_backend = None

        indexer_config = self.config.get("async_indexer", {})
        self.async_indexer = AsyncIndexer(
            batch_size=indexer_config.get("batch_size", 100),
            flush_interval=indexer_config.get("flush_interval", 5.0),
            max_queue_size=indexer_config.get("max_queue_size", 10000),
            max_workers=indexer_config.get("max_workers", 4),
        )

        vector_config = self.config.get("vector_db", {})
        if vector_config.get("enabled", False):
            try:
                self.vector_db = create_vector_db(vector_config)
                self.vector_indexer = VectorIndexer(
                    vector_db=self.vector_db, embedding_func=self._default_embedding, async_indexer=self.async_indexer
                )
                self.async_indexer.start()
            except Exception:
                self.vector_indexer = None
        else:
            self.vector_indexer = None

    def _default_embedding(self, text: str) -> list[float]:
        """默认嵌入函数（简单哈希，生产环境应替换）"""
        import hashlib

        hash_bytes = hashlib.sha256(text.encode()).digest()
        return [float(b) / 255.0 for b in hash_bytes[:64]]

    def _should_use_sharded(self) -> bool:
        """判断是否使用分片后端"""
        if not self.enabled or not self.sharded_backend:
            return False

        stats = self.sharded_backend.get_stats()
        return stats["total_memories"] >= self.config.get("thresholds", {}).get("auto_scale", 50000)

    def insert_memory(self, record: dict[str, Any]) -> bool:
        """插入记忆"""
        with self._lock:
            if self._should_use_sharded() and self.sharded_backend:
                memory_id = self.sharded_backend.insert(record)
                success = memory_id is not None
            elif self.sqlite_backend:
                success = self.sqlite_backend.insert_memory(record)
                memory_id = record.get("id")
            else:
                return False

            if success and self.cache:
                self.cache.cache.set_memory(memory_id, record)

                if self.vector_indexer:
                    self.vector_indexer.index_memory(record, async_mode=True)

            return success

    def get_memory(self, memory_id: str) -> Optional[dict[str, Any]]:
        """获取记忆"""
        if self.cache:
            cached = self.cache.cache.get_memory(memory_id)
            if cached:
                return cached

        with self._lock:
            if self._should_use_sharded() and self.sharded_backend:
                memory = self.sharded_backend.get_by_id(memory_id)
            elif self.sqlite_backend:
                memory = self.sqlite_backend.get_memory(memory_id)
            else:
                memory = None

            if memory and self.cache:
                self.cache.cache.set_memory(memory_id, memory)

            return memory

    def search_memories(
        self, query: str, top_k: int = 10, filters: Optional[dict] = None, use_vector: bool = True
    ) -> list[dict[str, Any]]:
        """搜索记忆"""
        if self.cache:
            cached = self.cache.cache.get_query_result(query)
            if cached:
                return cached[:top_k]

        results = []

        if use_vector and self.vector_indexer:
            try:
                vector_results = self.vector_indexer.search_similar(query, top_k=top_k)
                for vr in vector_results:
                    memory = self.get_memory(vr["id"])
                    if memory:
                        memory["vector_score"] = vr["score"]
                        results.append(memory)
            except Exception:
                pass

        if len(results) < top_k:
            with self._lock:
                if self._should_use_sharded() and self.sharded_backend:
                    text_results = self.sharded_backend.search_parallel(query, top_k=top_k, filters=filters)
                elif self.sqlite_backend:
                    text_results = self._sqlite_search(query, top_k, filters)
                else:
                    text_results = []

            existing_ids = {r["id"] for r in results}
            for r in text_results:
                if r["id"] not in existing_ids:
                    results.append(r)

        results = results[:top_k]

        if self.cache and results:
            self.cache.cache.set_query_result(query, results)

        return results

    def _sqlite_search(self, query: str, top_k: int, filters: Optional[dict] = None) -> list[dict[str, Any]]:
        """SQLite 搜索（简单实现）"""
        if not self.sqlite_backend:
            return []

        if filters and filters.get("entities"):
            return self.sqlite_backend.search_by_entities(filters["entities"], limit=top_k)

        return self.sqlite_backend.get_all_active_memories()[:top_k]

    def update_access_stats(self, memory_id: str, access_type: str) -> bool:
        """更新访问统计"""
        if self.cache:
            self.cache.cache.invalidate_memory(memory_id)

        with self._lock:
            if self._should_use_sharded() and self.sharded_backend:
                return self.sharded_backend.update(memory_id, {"access_count": 1})
            elif self.sqlite_backend:
                return self.sqlite_backend.update_access_stats(memory_id, access_type)

        return False

    def archive_memory(self, memory_id: str) -> bool:
        """归档记忆"""
        if self.cache:
            self.cache.cache.invalidate_memory(memory_id)

        with self._lock:
            if self._should_use_sharded() and self.sharded_backend:
                return self.sharded_backend.delete(memory_id)
            elif self.sqlite_backend:
                return self.sqlite_backend.archive_memory(memory_id)

        return False

    def get_stats(self) -> dict[str, Any]:
        """获取统计信息"""
        stats = {
            "scaling_enabled": self.enabled,
            "backend_type": "sharded" if self._should_use_sharded() else "sqlite",
            "cache_stats": None,
            "shard_stats": None,
            "indexer_stats": None,
        }

        if self.cache:
            stats["cache_stats"] = self.cache.cache.get_stats()

        if self.sharded_backend:
            stats["shard_stats"] = self.sharded_backend.get_stats()

        if self.async_indexer:
            stats["indexer_stats"] = self.async_indexer.get_stats()

        return stats

    def close(self):
        """关闭后端"""
        if self.async_indexer:
            self.async_indexer.stop()

        if self.sharded_backend:
            self.sharded_backend.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def get_scaled_backend(memory_dir: Path, config_path: Optional[Path] = None) -> ScaledBackend:
    """获取扩展后端实例"""
    config = ScalingConfig.load(config_path) if config_path else ScalingConfig.DEFAULT_CONFIG
    return ScaledBackend(memory_dir, config)


def migrate_to_scaled(
    memory_dir: Path,
    config: Optional[dict] = None,
    batch_size: int = 1000,
    progress_callback: Optional[callable] = None,
) -> tuple[int, int]:
    """
    迁移到扩展后端

    返回: (成功数, 失败数)
    """
    config = config or ScalingConfig.DEFAULT_CONFIG

    if not SCALING_AVAILABLE:
        raise RuntimeError("扩展模块不可用")

    backend = ScaledBackend(memory_dir, config)

    success_count = 0
    fail_count = 0

    if backend.sqlite_backend:
        for mem_type in ["fact", "belief", "summary"]:
            memories = backend.sqlite_backend.get_all_active_memories(mem_type)

            for i in range(0, len(memories), batch_size):
                batch = memories[i : i + batch_size]

                for memory in batch:
                    try:
                        memory["type"] = mem_type
                        if backend.sharded_backend:
                            backend.sharded_backend.insert(memory)
                        success_count += 1
                    except Exception:
                        fail_count += 1

                if progress_callback:
                    progress_callback(success_count, fail_count, len(memories))

    return success_count, fail_count
