#!/usr/bin/env python3
"""
Memory System v1.8.0 - 异步索引更新器
支持后台索引更新、批量处理、向量数据库集成

特性：
- 后台索引：新记忆添加后立即返回，索引在后台更新
- 批量处理：批量索引以提高效率
- 优先级队列：高优先级任务优先处理
- 错误重试：失败任务自动重试
- 向量数据库集成：支持 Qdrant/Pinecone
"""

import contextlib
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass(order=True)
class IndexTask:
    """索引任务"""

    priority: int
    created_at: float = field(compare=False)
    id: str = field(compare=False)
    type: str = field(compare=False)
    data: dict = field(compare=False)
    retry_count: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)


class AsyncIndexer:
    """异步索引更新器"""

    DEFAULT_CONFIG = {
        "batch_size": 100,
        "flush_interval": 5.0,
        "max_queue_size": 10000,
        "max_workers": 4,
        "max_retries": 3,
    }

    def __init__(
        self,
        batch_size: int = 100,
        flush_interval: float = 5.0,
        max_queue_size: int = 10000,
        max_workers: int = 4,
        max_retries: int = 3,
    ):
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_queue_size = max_queue_size
        self.max_workers = max_workers
        self.max_retries = max_retries

        self.task_queue: queue.PriorityQueue = queue.PriorityQueue(maxsize=max_queue_size)

        self.buffer: list[IndexTask] = []
        self.buffer_lock = threading.Lock()

        self.running = False
        self.worker_thread: Optional[threading.Thread] = None
        self.flush_thread: Optional[threading.Thread] = None

        self.handlers: dict[str, Callable] = {}
        self.on_batch_complete: Optional[Callable] = None
        self.on_error: Optional[Callable] = None

        self.total_processed = 0
        self.total_batches = 0
        self.total_errors = 0
        self._stats_lock = threading.Lock()

    def register_handler(self, task_type: str, handler: Callable):
        """注册任务处理器"""
        self.handlers[task_type] = handler

    def start(self):
        """启动索引器"""
        if self.running:
            return

        self.running = True

        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

        self.flush_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self.flush_thread.start()

    def stop(self, timeout: float = 10.0):
        """停止索引器"""
        self.running = False

        if self.worker_thread:
            self.worker_thread.join(timeout=timeout)

        if self.flush_thread:
            self.flush_thread.join(timeout=timeout)

        self._flush_buffer()

    def submit(self, task_id: str, task_type: str, data: dict, priority: int = 0) -> bool:
        """提交索引任务"""
        task = IndexTask(priority=priority, created_at=time.time(), id=task_id, type=task_type, data=data)

        try:
            self.task_queue.put(task, block=False)
            return True
        except queue.Full:
            self._process_single(task)
            return True

    def submit_batch(self, tasks: list[dict], priority: int = 0) -> int:
        """批量提交任务"""
        submitted = 0
        for task in tasks:
            if self.submit(
                task_id=task.get("id", ""),
                task_type=task.get("type", "add"),
                data=task.get("data", {}),
                priority=task.get("priority", priority),
            ):
                submitted += 1
        return submitted

    def _worker_loop(self):
        """工作线程循环"""
        while self.running:
            try:
                task = self.task_queue.get(timeout=1.0)

                with self.buffer_lock:
                    self.buffer.append(task)

                    if len(self.buffer) >= self.batch_size:
                        self._flush_buffer()

            except queue.Empty:
                continue
            except Exception:
                continue

    def _flush_loop(self):
        """定时刷新循环"""
        last_flush = time.time()

        while self.running:
            time.sleep(0.5)

            with self.buffer_lock:
                if self.buffer and time.time() - last_flush >= self.flush_interval:
                    self._flush_buffer()
                    last_flush = time.time()

    def _flush_buffer(self):
        """刷新缓冲区"""
        if not self.buffer:
            return

        tasks_to_process = self.buffer.copy()
        self.buffer.clear()

        grouped: dict[str, list[IndexTask]] = {}
        for task in tasks_to_process:
            if task.type not in grouped:
                grouped[task.type] = []
            grouped[task.type].append(task)

        for task_type, tasks in grouped.items():
            self._process_batch(task_type, tasks)

        with self._stats_lock:
            self.total_batches += 1

    def _process_batch(self, task_type: str, tasks: list[IndexTask]):
        """批量处理任务"""
        handler = self.handlers.get(task_type)

        if not handler:
            return

        try:
            data_list = [t.data for t in tasks]
            handler(data_list)

            with self._stats_lock:
                self.total_processed += len(tasks)

            if self.on_batch_complete:
                self.on_batch_complete(task_type, len(tasks))

        except Exception as e:
            with self._stats_lock:
                self.total_errors += 1

            if self.on_error:
                self.on_error(task_type, tasks, e)

            for task in tasks:
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    with contextlib.suppress(queue.Full):
                        self.task_queue.put(task, block=False)

    def _process_single(self, task: IndexTask):
        """同步处理单个任务"""
        self._process_batch(task.type, [task])

    def get_stats(self) -> dict:
        """获取统计"""
        with self._stats_lock:
            return {
                "running": self.running,
                "queue_size": self.task_queue.qsize(),
                "buffer_size": len(self.buffer),
                "total_processed": self.total_processed,
                "total_batches": self.total_batches,
                "total_errors": self.total_errors,
                "handlers": list(self.handlers.keys()),
            }

    def get_queue_size(self) -> int:
        """获取队列大小"""
        return self.task_queue.qsize()

    def is_idle(self) -> bool:
        """检查是否空闲"""
        return self.task_queue.empty() and len(self.buffer) == 0


class VectorDBAdapter:
    """向量数据库适配器基类"""

    def __init__(self, config: dict):
        self.config = config

    def upsert(self, vectors: list[dict]) -> bool:
        """插入或更新向量"""
        raise NotImplementedError

    def delete(self, ids: list[str]) -> bool:
        """删除向量"""
        raise NotImplementedError

    def search(self, query_vector: list[float], top_k: int = 10) -> list[dict]:
        """搜索相似向量"""
        raise NotImplementedError

    def health_check(self) -> bool:
        """健康检查"""
        raise NotImplementedError


class QdrantAdapter(VectorDBAdapter):
    """Qdrant 向量数据库适配器"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 6333)
        self.collection = config.get("collection", "memories")
        self._client = None

    @property
    def client(self):
        """延迟初始化客户端"""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient

                self._client = QdrantClient(host=self.host, port=self.port)
            except ImportError:
                raise ImportError("请安装 qdrant-client: pip install qdrant-client") from None
        return self._client

    def upsert(self, vectors: list[dict]) -> bool:
        """插入或更新向量"""
        try:
            from qdrant_client.models import PointStruct

            points = [PointStruct(id=v["id"], vector=v["vector"], payload=v.get("payload", {})) for v in vectors]

            self.client.upsert(collection_name=self.collection, points=points)
            return True
        except Exception:
            return False

    def delete(self, ids: list[str]) -> bool:
        """删除向量"""
        try:
            self.client.delete(collection_name=self.collection, points_selector=ids)
            return True
        except Exception:
            return False

    def search(self, query_vector: list[float], top_k: int = 10) -> list[dict]:
        """搜索相似向量"""
        try:
            results = self.client.search(collection_name=self.collection, query_vector=query_vector, limit=top_k)

            return [{"id": str(r.id), "score": r.score, "payload": r.payload} for r in results]
        except Exception:
            return []

    def health_check(self) -> bool:
        """健康检查"""
        try:
            self.client.get_collections()
            return True
        except Exception:
            return False


class PineconeAdapter(VectorDBAdapter):
    """Pinecone 向量数据库适配器"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.environment = config.get("environment", "us-west1-gcp")
        self.index_name = config.get("index_name", "memories")
        self._index = None

    @property
    def index(self):
        """延迟初始化索引"""
        if self._index is None:
            try:
                import pinecone

                pinecone.init(api_key=self.api_key, environment=self.environment)
                self._index = pinecone.Index(self.index_name)
            except ImportError:
                raise ImportError("请安装 pinecone-client: pip install pinecone-client") from None
        return self._index

    def upsert(self, vectors: list[dict]) -> bool:
        """插入或更新向量"""
        try:
            batch = [(v["id"], v["vector"], v.get("payload", {})) for v in vectors]

            self.index.upsert(vectors=batch)
            return True
        except Exception:
            return False

    def delete(self, ids: list[str]) -> bool:
        """删除向量"""
        try:
            self.index.delete(ids=ids)
            return True
        except Exception:
            return False

    def search(self, query_vector: list[float], top_k: int = 10) -> list[dict]:
        """搜索相似向量"""
        try:
            results = self.index.query(vector=query_vector, top_k=top_k, include_metadata=True)

            return [{"id": r.id, "score": r.score, "payload": r.metadata} for r in results.matches]
        except Exception:
            return []

    def health_check(self) -> bool:
        """健康检查"""
        try:
            self.index.describe_index_stats()
            return True
        except Exception:
            return False


class VectorIndexer:
    """向量索引器"""

    def __init__(
        self, vector_db: VectorDBAdapter, embedding_func: Callable, async_indexer: Optional[AsyncIndexer] = None
    ):
        self.vector_db = vector_db
        self.embedding_func = embedding_func
        self.async_indexer = async_indexer

        if async_indexer:
            async_indexer.register_handler("add", self._handle_add)
            async_indexer.register_handler("update", self._handle_update)
            async_indexer.register_handler("delete", self._handle_delete)

    def index_memory(self, memory: dict, async_mode: bool = True) -> bool:
        """索引记忆"""
        if async_mode and self.async_indexer:
            return self.async_indexer.submit(task_id=memory["id"], task_type="add", data=memory)
        else:
            return self._index_single(memory)

    def index_batch(self, memories: list[dict], async_mode: bool = True) -> int:
        """批量索引"""
        if async_mode and self.async_indexer:
            tasks = [{"id": m["id"], "type": "add", "data": m} for m in memories]
            return self.async_indexer.submit_batch(tasks)
        else:
            count = 0
            for memory in memories:
                if self._index_single(memory):
                    count += 1
            return count

    def delete_vectors(self, memory_ids: list[str], async_mode: bool = True) -> bool:
        """删除向量"""
        if async_mode and self.async_indexer:
            for mid in memory_ids:
                self.async_indexer.submit(task_id=mid, task_type="delete", data={"id": mid})
            return True
        else:
            return self.vector_db.delete(memory_ids)

    def search_similar(self, query: str, top_k: int = 10) -> list[dict]:
        """搜索相似记忆"""
        query_vector = self.embedding_func(query)
        return self.vector_db.search(query_vector, top_k)

    def _index_single(self, memory: dict) -> bool:
        """索引单个记忆"""
        try:
            vector = self.embedding_func(memory["content"])

            return self.vector_db.upsert(
                [
                    {
                        "id": memory["id"],
                        "vector": vector,
                        "payload": {
                            "type": memory.get("type", "fact"),
                            "content": memory["content"][:500],
                            "importance": memory.get("importance", 0.5),
                            "entities": memory.get("entities", []),
                        },
                    }
                ]
            )
        except Exception:
            return False

    def _handle_add(self, data_list: list[dict]):
        """处理添加任务"""
        vectors = []
        for data in data_list:
            try:
                vector = self.embedding_func(data["content"])
                vectors.append(
                    {
                        "id": data["id"],
                        "vector": vector,
                        "payload": {
                            "type": data.get("type", "fact"),
                            "content": data["content"][:500],
                            "importance": data.get("importance", 0.5),
                            "entities": data.get("entities", []),
                        },
                    }
                )
            except Exception:
                continue

        if vectors:
            self.vector_db.upsert(vectors)

    def _handle_update(self, data_list: list[dict]):
        """处理更新任务"""
        self._handle_add(data_list)

    def _handle_delete(self, data_list: list[dict]):
        """处理删除任务"""
        ids = [d["id"] for d in data_list]
        self.vector_db.delete(ids)


def create_vector_db(config: dict) -> VectorDBAdapter:
    """创建向量数据库适配器"""
    db_type = config.get("type", "qdrant")

    if db_type == "qdrant":
        return QdrantAdapter(config)
    elif db_type == "pinecone":
        return PineconeAdapter(config)
    else:
        raise ValueError(f"不支持的向量数据库类型: {db_type}")
