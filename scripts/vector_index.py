#!/usr/bin/env python3
"""
Memory System v1.6.0 - 向量索引模块
支持 SQLite 向量存储和 Qdrant 后端
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class VectorRecord:
    """向量记录"""

    id: str
    vector: list[float]
    metadata: dict = field(default_factory=dict)
    content: str = ""


class SQLiteVectorIndex:
    """SQLite 向量索引"""

    def __init__(self, db_path: Path, dimension: int):
        self.db_path = Path(db_path)
        self.dimension = dimension
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                vector BLOB NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_vectors_created
            ON vectors(created_at)
        """)

        conn.commit()
        conn.close()

    def insert(self, record: VectorRecord) -> bool:
        """插入向量记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            vector_blob = np.array(record.vector, dtype=np.float32).tobytes()

            cursor.execute(
                """
                INSERT OR REPLACE INTO vectors (id, content, vector, metadata)
                VALUES (?, ?, ?, ?)
            """,
                (
                    record.id,
                    record.content,
                    vector_blob,
                    json.dumps(record.metadata, ensure_ascii=False),
                ),
            )

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ 插入向量失败: {e}")
            return False

    def insert_batch(self, records: list[VectorRecord]) -> int:
        """批量插入"""
        success_count = 0
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for record in records:
            try:
                vector_blob = np.array(record.vector, dtype=np.float32).tobytes()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO vectors (id, content, vector, metadata)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        record.id,
                        record.content,
                        vector_blob,
                        json.dumps(record.metadata, ensure_ascii=False),
                    ),
                )
                success_count += 1
            except Exception:
                pass

        conn.commit()
        conn.close()
        return success_count

    def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filter_metadata: dict | None = None,
    ) -> list[tuple[VectorRecord, float]]:
        """搜索相似向量"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if filter_metadata:
            conditions = []
            values = []
            for key, value in filter_metadata.items():
                conditions.append(f"json_extract(metadata, '$.{key}') = ?")
                values.append(str(value))

            query = f"SELECT id, content, vector, metadata FROM vectors WHERE {' AND '.join(conditions)}"
            cursor.execute(query, values)
        else:
            cursor.execute("SELECT id, content, vector, metadata FROM vectors")

        results = []
        query_vec = np.array(query_vector, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0:
            conn.close()
            return []

        for row in cursor.fetchall():
            id_, content, vector_blob, metadata_json = row
            vector = np.frombuffer(vector_blob, dtype=np.float32)

            vec_norm = np.linalg.norm(vector)
            if vec_norm == 0:
                continue

            similarity = float(np.dot(query_vec, vector) / (query_norm * vec_norm))

            record = VectorRecord(
                id=id_,
                vector=vector.tolist(),
                metadata=json.loads(metadata_json) if metadata_json else {},
                content=content,
            )

            results.append((record, similarity))

        conn.close()

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def delete(self, id_: str) -> bool:
        """删除向量"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vectors WHERE id = ?", (id_,))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def count(self) -> int:
        """统计向量数量"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vectors")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_all_ids(self) -> list[str]:
        """获取所有向量ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM vectors")
        ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        return ids


class QdrantVectorIndex:
    """Qdrant 向量索引（可选高级后端）"""

    def __init__(
        self,
        collection_name: str = "memory",
        host: str = "localhost",
        port: int = 6333,
        dimension: int = 1536,
    ):
        self.collection_name = collection_name
        self.host = host
        self.port = port
        self.dimension = dimension
        self._client = None

    def _get_client(self):
        """获取 Qdrant 客户端"""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient

                self._client = QdrantClient(host=self.host, port=self.port)
                self._ensure_collection()
            except ImportError as err:
                raise ImportError("请安装 qdrant-client: pip install qdrant-client") from err
        return self._client

    def _ensure_collection(self):
        """确保集合存在"""
        from qdrant_client.models import Distance, VectorParams

        client = self._get_client()
        collections = client.get_collections().collections
        collection_names = [c.name for c in collections]

        if self.collection_name not in collection_names:
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.dimension, distance=Distance.COSINE),
            )

    def insert(self, record: VectorRecord) -> bool:
        """插入向量"""
        from qdrant_client.models import PointStruct

        client = self._get_client()
        try:
            client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=record.id,
                        vector=record.vector,
                        payload={"content": record.content, **record.metadata},
                    )
                ],
            )
            return True
        except Exception:
            return False

    def insert_batch(self, records: list[VectorRecord]) -> int:
        """批量插入"""
        from qdrant_client.models import PointStruct

        client = self._get_client()
        points = [
            PointStruct(
                id=r.id,
                vector=r.vector,
                payload={"content": r.content, **r.metadata},
            )
            for r in records
        ]

        try:
            client.upsert(collection_name=self.collection_name, points=points)
            return len(records)
        except Exception:
            return 0

    def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filter_metadata: dict | None = None,
    ) -> list[tuple[VectorRecord, float]]:
        """搜索相似向量"""
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        client = self._get_client()

        query_filter = None
        if filter_metadata:
            conditions = [FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filter_metadata.items()]
            query_filter = Filter(must=conditions)

        results = client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=query_filter,
        )

        return [
            (
                VectorRecord(
                    id=str(r.id),
                    vector=r.vector if hasattr(r, "vector") else [],
                    metadata={k: v for k, v in r.payload.items() if k != "content"},
                    content=r.payload.get("content", ""),
                ),
                r.score,
            )
            for r in results
        ]

    def delete(self, id_: str) -> bool:
        """删除向量"""
        client = self._get_client()
        try:
            client.delete(collection_name=self.collection_name, points_selector=[id_])
            return True
        except Exception:
            return False

    def count(self) -> int:
        """统计向量数量"""
        client = self._get_client()
        return client.get_collection(self.collection_name).points_count


class VectorIndexManager:
    """向量索引管理器"""

    def __init__(
        self,
        memory_dir: Path,
        dimension: int = 1536,
        backend: str = "sqlite",
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
    ):
        self.memory_dir = Path(memory_dir)
        self.dimension = dimension
        self.backend = backend

        if backend == "sqlite":
            db_path = self.memory_dir / "layer2" / "vectors.db"
            self.index = SQLiteVectorIndex(db_path, dimension)
        elif backend == "qdrant":
            self.index = QdrantVectorIndex(
                collection_name="memory",
                host=qdrant_host,
                port=qdrant_port,
                dimension=dimension,
            )
        else:
            raise ValueError(f"Unknown backend: {backend}")

    def add_memory(self, memory_id: str, content: str, vector: list[float], metadata: dict | None = None) -> bool:
        """添加记忆向量"""
        record = VectorRecord(
            id=memory_id,
            vector=vector,
            metadata=metadata or {},
            content=content,
        )
        return self.index.insert(record)

    def add_memories_batch(
        self,
        memories: list[dict],
        vectors: list[list[float]],
    ) -> int:
        """批量添加记忆向量"""
        records = [
            VectorRecord(
                id=m["id"],
                vector=v,
                metadata={"type": m.get("type", "fact"), "importance": m.get("importance", 0.5)},
                content=m.get("content", ""),
            )
            for m, v in zip(memories, vectors)
        ]
        return self.index.insert_batch(records)

    def search_similar(
        self,
        query_vector: list[float],
        top_k: int = 10,
        memory_type: str | None = None,
    ) -> list[tuple[str, str, float, dict]]:
        """
        搜索相似记忆

        返回: [(memory_id, content, similarity, metadata), ...]
        """
        filter_metadata = None
        if memory_type:
            filter_metadata = {"type": memory_type}

        results = self.index.search(query_vector, top_k=top_k, filter_metadata=filter_metadata)

        return [(r.id, r.content, score, r.metadata) for r, score in results]

    def remove_memory(self, memory_id: str) -> bool:
        """移除记忆向量"""
        return self.index.delete(memory_id)

    def get_vector_count(self) -> int:
        """获取向量数量"""
        return self.index.count()

    def get_indexed_ids(self) -> list[str]:
        """获取已索引的记忆ID列表"""
        if hasattr(self.index, "get_all_ids"):
            return self.index.get_all_ids()
        return []


def build_vector_index(
    memory_dir: Path,
    embedding_engine,
    backend: str = "sqlite",
    batch_size: int = 100,
) -> dict[str, int]:
    """
    构建向量索引

    返回: {"total": 总数, "indexed": 已索引数, "failed": 失败数}
    """
    memory_dir = Path(memory_dir)

    manager = VectorIndexManager(
        memory_dir=memory_dir,
        dimension=embedding_engine.dimension,
        backend=backend,
    )

    indexed_ids = set(manager.get_indexed_ids())

    stats = {"total": 0, "indexed": 0, "failed": 0, "skipped": 0}

    for mem_type in ["facts", "beliefs", "summaries"]:
        jsonl_path = memory_dir / "layer2" / "active" / f"{mem_type}.jsonl"
        if not jsonl_path.exists():
            continue

        memories = []
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        record = json.loads(line)
                        memories.append(record)
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON解析失败: {e}")

        stats["total"] += len(memories)

        to_index = [m for m in memories if m["id"] not in indexed_ids]
        stats["skipped"] += len(memories) - len(to_index)

        for i in range(0, len(to_index), batch_size):
            batch = to_index[i : i + batch_size]
            contents = [m.get("content", "") for m in batch]

            try:
                vectors = embedding_engine.embed_batch(contents)
                count = manager.add_memories_batch(batch, vectors)
                stats["indexed"] += count
                stats["failed"] += len(batch) - count
            except Exception as e:
                print(f"⚠️ 批量索引失败: {e}")
                stats["failed"] += len(batch)

    return stats
