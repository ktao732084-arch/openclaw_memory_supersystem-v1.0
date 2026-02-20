#!/usr/bin/env python3
"""
Memory System v1.8.0 - 分片索引管理器
支持百万级记忆存储，自动分片，并行检索

特性：
- 自动分片：超过阈值自动创建新分片
- 并行检索：多线程并行搜索所有分片
- 全文索引：FTS5 支持高效文本搜索
- 线程安全：支持并发读写
"""

import hashlib
import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


@dataclass
class ShardInfo:
    """分片信息"""

    id: str
    path: Path
    count: int
    created_at: datetime
    is_active: bool = False


@dataclass
class MemoryRecord:
    """记忆记录"""

    id: str
    type: str
    content: str
    importance: float = 0.5
    confidence: float = 0.5
    entities: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    access_count: int = 0
    score: float = 0.5


class ShardedIndexManager:
    """分片索引管理器"""

    DEFAULT_SHARD_SIZE = 10000

    def __init__(self, base_dir: Path, shard_size: int = DEFAULT_SHARD_SIZE):
        self.base_dir = Path(base_dir)
        self.shard_size = shard_size
        self.shards: dict[str, ShardInfo] = {}
        self.active_shard_id: Optional[str] = None
        self._lock = threading.RLock()
        self._connection_pool: dict[str, sqlite3.Connection] = {}

        self._init_shards()

    def _init_shards(self):
        """初始化分片"""
        self.base_dir.mkdir(parents=True, exist_ok=True)

        for shard_file in self.base_dir.glob("shard_*.db"):
            shard_id = shard_file.stem
            count = self._get_shard_count(shard_file)

            self.shards[shard_id] = ShardInfo(
                id=shard_id,
                path=shard_file,
                count=count,
                created_at=datetime.fromtimestamp(shard_file.stat().st_ctime),
                is_active=False,
            )

        if self.shards:
            for shard_id, info in sorted(self.shards.items(), key=lambda x: x[1].created_at, reverse=True):
                if info.count < self.shard_size:
                    self.active_shard_id = shard_id
                    info.is_active = True
                    break

            if not self.active_shard_id:
                self._create_new_shard()
        else:
            self._create_new_shard()

    def _create_new_shard(self) -> str:
        """创建新分片"""
        with self._lock:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            shard_id = f"shard_{timestamp}"
            shard_path = self.base_dir / f"{shard_id}.db"

            self._init_shard_db(shard_path)

            self.shards[shard_id] = ShardInfo(
                id=shard_id, path=shard_path, count=0, created_at=datetime.now(), is_active=True
            )

            if self.active_shard_id and self.active_shard_id in self.shards:
                self.shards[self.active_shard_id].is_active = False
            self.active_shard_id = shard_id

            return shard_id

    def _init_shard_db(self, shard_path: Path):
        """初始化分片数据库"""
        conn = sqlite3.connect(shard_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                importance REAL DEFAULT 0.5,
                confidence REAL DEFAULT 0.5,
                score REAL DEFAULT 0.5,
                entities TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                access_count INTEGER DEFAULT 0,
                state INTEGER DEFAULT 0
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_score ON memories(score)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_state ON memories(state)")

        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(id, content, entities, content='memories', content_rowid='rowid')
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, id, content, entities)
                VALUES (new.rowid, new.id, new.content, COALESCE(new.entities, ''));
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, id, content, entities)
                VALUES('delete', old.rowid, old.id, old.content, COALESCE(old.entities, ''));
            END
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, id, content, entities)
                VALUES('delete', old.rowid, old.id, old.content, COALESCE(old.entities, ''));
                INSERT INTO memories_fts(rowid, id, content, entities)
                VALUES (new.rowid, new.id, new.content, COALESCE(new.entities, ''));
            END
        """)

        conn.commit()
        conn.close()

    def _get_shard_count(self, shard_path: Path) -> int:
        """获取分片记录数"""
        conn = sqlite3.connect(shard_path)
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM memories WHERE state = 0")
            count = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            count = 0
        conn.close()
        return count

    def _get_connection(self, shard_path: Path) -> sqlite3.Connection:
        """获取数据库连接（带连接池）"""
        path_str = str(shard_path)
        if path_str not in self._connection_pool:
            conn = sqlite3.connect(shard_path, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.row_factory = sqlite3.Row
            self._connection_pool[path_str] = conn
        return self._connection_pool[path_str]

    def insert(self, memory: dict) -> str:
        """插入记忆到合适的分片"""
        with self._lock:
            active_shard = self.shards[self.active_shard_id]
            if active_shard.count >= self.shard_size:
                self._create_new_shard()
                active_shard = self.shards[self.active_shard_id]

            conn = self._get_connection(active_shard.path)
            cursor = conn.cursor()

            memory_id = memory.get("id") or self._generate_id(memory.get("type", "fact"), memory.get("content", ""))

            cursor.execute(
                """
                INSERT INTO memories (id, type, content, importance, confidence, score, entities, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    memory_id,
                    memory.get("type", "fact"),
                    memory["content"],
                    memory.get("importance", 0.5),
                    memory.get("confidence", 0.5),
                    memory.get("score", memory.get("importance", 0.5)),
                    json.dumps(memory.get("entities", []), ensure_ascii=False),
                    json.dumps(memory.get("metadata", {}), ensure_ascii=False),
                    memory.get("created_at") or datetime.utcnow().isoformat() + "Z",
                ),
            )

            conn.commit()
            active_shard.count += 1

            return memory_id

    def batch_insert(self, memories: list[dict]) -> list[str]:
        """批量插入记忆"""
        inserted_ids = []
        with self._lock:
            for memory in memories:
                inserted_ids.append(self.insert(memory))
        return inserted_ids

    def get_by_id(self, memory_id: str) -> Optional[dict]:
        """根据 ID 获取记忆"""
        for shard_info in self.shards.values():
            conn = self._get_connection(shard_info.path)
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_dict(row)

        return None

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        """将数据库行转换为字典"""
        return {
            "id": row["id"],
            "type": row["type"],
            "content": row["content"],
            "importance": row["importance"],
            "confidence": row["confidence"],
            "score": row["score"],
            "entities": json.loads(row["entities"]) if row["entities"] else [],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "access_count": row["access_count"],
            "state": row["state"],
        }

    def search_parallel(self, query: str, top_k: int = 10, filters: Optional[dict] = None) -> list[dict]:
        """并行搜索所有分片"""
        results = []

        def search_shard(shard_info: ShardInfo) -> list[dict]:
            """搜索单个分片"""
            try:
                conn = self._get_connection(shard_info.path)
                cursor = conn.cursor()

                fts_query = query.replace("'", "''")
                if not fts_query:
                    fts_query = "*"

                sql = """
                    SELECT m.*, bm25(memories_fts) as bm25_score
                    FROM memories m
                    JOIN memories_fts fts ON m.id = fts.id
                    WHERE memories_fts MATCH ? AND m.state = 0
                """
                params = [fts_query]

                if filters:
                    if filters.get("type"):
                        sql += " AND m.type = ?"
                        params.append(filters["type"])
                    if filters.get("min_importance"):
                        sql += " AND m.importance >= ?"
                        params.append(filters["min_importance"])

                sql += " ORDER BY bm25_score LIMIT ?"
                params.append(top_k * 2)

                cursor.execute(sql, params)

                shard_results = []
                for row in cursor.fetchall():
                    result = self._row_to_dict(row)
                    result["score"] = -row["bm25_score"] if row["bm25_score"] else 0
                    result["shard_id"] = shard_info.id
                    shard_results.append(result)

                return shard_results
            except Exception:
                try:
                    conn = self._get_connection(shard_info.path)
                    cursor = conn.cursor()

                    sql = """
                        SELECT m.*, 0 as bm25_score
                        FROM memories m
                        WHERE m.content LIKE ? AND m.state = 0
                    """
                    params = [f"%{query}%"]

                    if filters:
                        if filters.get("type"):
                            sql += " AND m.type = ?"
                            params.append(filters["type"])
                        if filters.get("min_importance"):
                            sql += " AND m.importance >= ?"
                            params.append(filters["min_importance"])

                    sql += " ORDER BY m.score DESC LIMIT ?"
                    params.append(top_k * 2)

                    cursor.execute(sql, params)

                    shard_results = []
                    for row in cursor.fetchall():
                        result = self._row_to_dict(row)
                        result["score"] = row["score"] if row["score"] else 0
                        result["shard_id"] = shard_info.id
                        shard_results.append(result)

                    return shard_results
                except Exception:
                    return []

        with ThreadPoolExecutor(max_workers=min(len(self.shards), 8)) as executor:
            futures = {executor.submit(search_shard, info): shard_id for shard_id, info in self.shards.items()}

            for future in as_completed(futures):
                try:
                    shard_results = future.result()
                    results.extend(shard_results)
                except Exception:
                    pass

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:top_k]

    def search_by_entities(self, entities: list[str], top_k: int = 10) -> list[dict]:
        """通过实体搜索记忆"""
        results = []

        def search_shard_entities(shard_info: ShardInfo) -> list[dict]:
            """在单个分片中搜索实体"""
            try:
                conn = self._get_connection(shard_info.path)
                cursor = conn.cursor()

                results_local = []
                for entity in entities:
                    cursor.execute(
                        """
                        SELECT * FROM memories
                        WHERE entities LIKE ? AND state = 0
                        ORDER BY score DESC
                        LIMIT ?
                    """,
                        (f"%{entity}%", top_k),
                    )

                    for row in cursor.fetchall():
                        result = self._row_to_dict(row)
                        result["matched_entity"] = entity
                        result["shard_id"] = shard_info.id
                        results_local.append(result)

                return results_local
            except Exception:
                return []

        with ThreadPoolExecutor(max_workers=min(len(self.shards), 8)) as executor:
            futures = {executor.submit(search_shard_entities, info): shard_id for shard_id, info in self.shards.items()}

            for future in as_completed(futures):
                try:
                    shard_results = future.result()
                    results.extend(shard_results)
                except Exception:
                    pass

        seen_ids = set()
        unique_results = []
        for r in results:
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                unique_results.append(r)

        unique_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return unique_results[:top_k]

    def update(self, memory_id: str, updates: dict) -> bool:
        """更新记忆"""
        for shard_info in self.shards.values():
            conn = self._get_connection(shard_info.path)
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM memories WHERE id = ?", (memory_id,))
            if cursor.fetchone():
                set_clauses = []
                params = []

                for key, value in updates.items():
                    if key in ["entities", "metadata"]:
                        set_clauses.append(f"{key} = ?")
                        params.append(json.dumps(value, ensure_ascii=False))
                    elif key in ["importance", "confidence", "score", "access_count", "state"]:
                        set_clauses.append(f"{key} = ?")
                        params.append(value)

                if set_clauses:
                    set_clauses.append("updated_at = ?")
                    params.append(datetime.utcnow().isoformat() + "Z")
                    params.append(memory_id)

                    cursor.execute(f"UPDATE memories SET {', '.join(set_clauses)} WHERE id = ?", params)
                    conn.commit()
                    return True

        return False

    def delete(self, memory_id: str) -> bool:
        """删除记忆（软删除）"""
        return self.update(memory_id, {"state": 2})

    def get_stats(self) -> dict:
        """获取分片统计"""
        total_count = sum(s.count for s in self.shards.values())

        return {
            "total_memories": total_count,
            "shard_count": len(self.shards),
            "active_shard": self.active_shard_id,
            "shard_size_limit": self.shard_size,
            "shards": [
                {"id": s.id, "count": s.count, "is_active": s.is_active, "created_at": s.created_at.isoformat()}
                for s in sorted(self.shards.values(), key=lambda x: x.created_at, reverse=True)
            ],
        }

    def close(self):
        """关闭所有连接"""
        for conn in self._connection_pool.values():
            conn.close()
        self._connection_pool.clear()

    def _generate_id(self, prefix: str, content: str) -> str:
        """生成唯一ID"""
        date_str = datetime.now().strftime("%Y%m%d")
        hash_str = hashlib.md5(content.encode()).hexdigest()[:6]
        return f"{prefix[0]}_{date_str}_{hash_str}"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class ShardedIndexConfig:
    """分片索引配置"""

    DEFAULT_CONFIG = {
        "shard_size": 10000,
        "max_workers": 8,
        "connection_pool_size": 10,
        "wal_mode": True,
        "synchronous": "NORMAL",
    }

    @classmethod
    def load(cls, config_path: Path) -> dict:
        """加载配置"""
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)
                return {**cls.DEFAULT_CONFIG, **config.get("sharded_index", {})}
        return cls.DEFAULT_CONFIG.copy()

    @classmethod
    def save(cls, config_path: Path, config: dict):
        """保存配置"""
        existing = {}
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                existing = json.load(f)

        existing["sharded_index"] = {**cls.DEFAULT_CONFIG, **config}

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
