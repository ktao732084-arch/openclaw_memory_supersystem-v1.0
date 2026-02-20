#!/usr/bin/env python3
"""
Memory System v1.2.5 - SQLite Backend (Thread-Safe)
修复并发安全问题，引入连接池和锁机制
"""

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# ============================================================
# 数据库 Schema
# ============================================================

SCHEMA_SQL = """
-- 主表：记忆
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL CHECK(type IN ('fact', 'belief', 'summary')),
    content TEXT NOT NULL,

    -- 评分系统
    importance REAL DEFAULT 0.5,
    score REAL DEFAULT 1.0,
    access_boost REAL DEFAULT 0.0,
    final_score REAL GENERATED ALWAYS AS (score + access_boost) STORED,

    -- 时间字段
    created TEXT NOT NULL,
    updated TEXT,
    last_accessed TEXT,

    -- 访问统计
    access_count INTEGER DEFAULT 0,
    retrieval_count INTEGER DEFAULT 0,

    -- 来源和状态
    source TEXT,
    state INTEGER DEFAULT 0 CHECK(state IN (0, 1, 2)),

    -- 冲突管理
    conflict_downgraded INTEGER DEFAULT 0,
    downgrade_reason TEXT,
    superseded INTEGER DEFAULT 0,
    superseded_by TEXT,

    -- TTL 管理
    ttl_days INTEGER,
    auto_delete_at TEXT,

    -- 类型特有字段
    confidence REAL,
    basis TEXT,
    extract_method TEXT,
    expires_at TEXT,
    is_permanent INTEGER DEFAULT 1
);

-- 实体关联表
CREATE TABLE IF NOT EXISTS memory_entities (
    memory_id TEXT NOT NULL,
    entity TEXT NOT NULL,
    PRIMARY KEY (memory_id, entity),
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

-- 关系三元组表
CREATE TABLE IF NOT EXISTS memory_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    object TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    created TEXT NOT NULL,
    superseded INTEGER DEFAULT 0,
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

-- 摘要来源表
CREATE TABLE IF NOT EXISTS summary_sources (
    summary_id TEXT NOT NULL,
    source_fact_id TEXT NOT NULL,
    PRIMARY KEY (summary_id, source_fact_id),
    FOREIGN KEY (summary_id) REFERENCES memories(id) ON DELETE CASCADE
);

-- 访问日志表（可选）
CREATE TABLE IF NOT EXISTS access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id TEXT NOT NULL,
    access_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_memories_state_score ON memories(state, final_score DESC);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created DESC);
CREATE INDEX IF NOT EXISTS idx_memories_auto_delete ON memories(auto_delete_at) WHERE auto_delete_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_entities_entity ON memory_entities(entity);
CREATE INDEX IF NOT EXISTS idx_relations_subject_type ON memory_relations(subject, relation_type, superseded);
CREATE INDEX IF NOT EXISTS idx_access_log_timestamp ON access_log(timestamp DESC);
"""

# ============================================================
# 线程安全的数据库连接管理
# ============================================================


class SQLiteBackend:
    """SQLite 后端管理器（线程安全）"""

    def __init__(self, memory_dir: Path):
        self.memory_dir = Path(memory_dir)
        self.db_path = self.memory_dir / "layer2" / "memories.db"

        # 线程安全：单例连接 + 可重入锁
        self._conn = None
        self._lock = threading.RLock()  # 可重入锁，允许同一线程多次获取

        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """确保数据库存在并初始化"""
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_db()

    def _init_db(self):
        """初始化数据库"""
        with self._get_connection(write=True) as conn:
            # 启用 WAL 模式（提升并发性能）
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA busy_timeout=30000")  # 30秒超时
            conn.execute("PRAGMA cache_size=-64000")  # 64MB 缓存

            # 创建表和索引
            conn.executescript(SCHEMA_SQL)
            conn.commit()
            print(f"✅ SQLite 数据库初始化完成: {self.db_path}")

    @contextmanager
    def _get_connection(self, write: bool = False):
        """
        获取数据库连接（上下文管理器）

        Args:
            write: 是否为写操作（写操作会获取独占锁）

        Yields:
            sqlite3.Connection: 数据库连接
        """
        with self._lock:
            try:
                if self._conn is None:
                    self._conn = sqlite3.connect(
                        self.db_path,
                        check_same_thread=False,  # 允许多线程访问
                        timeout=30.0,  # 30秒超时
                    )
                    self._conn.row_factory = sqlite3.Row  # 返回字典

                    # 启用 WAL 模式
                    self._conn.execute("PRAGMA journal_mode=WAL")
                    self._conn.execute("PRAGMA busy_timeout=30000")

                yield self._conn

            except sqlite3.OperationalError as e:
                if "database is locked" in str(e):
                    raise RuntimeError(f"数据库锁定超时（30秒）。可能有其他进程正在写入。错误: {e}")
                raise

    def close(self):
        """关闭数据库连接"""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    # ============================================================
    # 基础 CRUD 操作
    # ============================================================

    def insert_memory(self, record: Dict[str, Any]) -> bool:
        """插入记忆（线程安全）"""
        with self._get_connection(write=True) as conn:
            cursor = conn.cursor()

            try:
                # 插入主表
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO memories (
                        id, type, content, importance, score, access_boost,
                        created, updated, last_accessed,
                        access_count, retrieval_count,
                        source, state,
                        conflict_downgraded, downgrade_reason, superseded, superseded_by,
                        ttl_days, auto_delete_at,
                        confidence, basis, extract_method, expires_at, is_permanent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        record["id"],
                        record.get("type", "fact"),
                        record["content"],
                        record.get("importance", 0.5),
                        record.get("score", 1.0),
                        record.get("access_boost", 0.0),
                        record.get("created", record.get("created_at")),
                        record.get("updated"),
                        record.get("last_accessed"),
                        record.get("access_count", 0),
                        record.get("retrieval_count", 0),
                        record.get("source", "unknown"),
                        0,  # state: Active
                        1 if record.get("conflict_downgraded") else 0,
                        record.get("downgrade_reason"),
                        1 if record.get("superseded") else 0,
                        record.get("superseded_by"),
                        record.get("ttl_days"),
                        record.get("auto_delete_at"),
                        record.get("confidence"),
                        record.get("basis"),
                        record.get("extract_method"),
                        record.get("expires_at"),
                        1 if record.get("is_permanent", True) else 0,
                    ),
                )

                # 插入实体
                for entity in record.get("entities", []):
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO memory_entities (memory_id, entity)
                        VALUES (?, ?)
                    """,
                        (record["id"], entity),
                    )

                # 插入摘要来源
                if record.get("type") == "summary" and record.get("source_facts"):
                    for source_id in record["source_facts"]:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO summary_sources (summary_id, source_fact_id)
                            VALUES (?, ?)
                        """,
                            (record["id"], source_id),
                        )

                conn.commit()
                return True

            except Exception as e:
                conn.rollback()
                print(f"❌ 插入记忆失败: {e}")
                return False

    def get_memory(self, memory_id: str) -> Optional[Dict]:
        """获取单条记忆（线程安全）"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 查询主表
            cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
            row = cursor.fetchone()

            if not row:
                return None

            memory = dict(row)

            # 查询实体
            cursor.execute("SELECT entity FROM memory_entities WHERE memory_id = ?", (memory_id,))
            memory["entities"] = [r["entity"] for r in cursor.fetchall()]

            # 查询摘要来源
            if memory["type"] == "summary":
                cursor.execute("SELECT source_fact_id FROM summary_sources WHERE summary_id = ?", (memory_id,))
                memory["source_facts"] = [r["source_fact_id"] for r in cursor.fetchall()]

            return memory

    def get_all_memories(self, state: int = 0) -> List[Dict]:
        """
        获取所有记忆（优化版，两次查询）

        Args:
            state: 0=活跃, 1=归档, 2=删除

        Returns:
            记忆列表
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 第一次查询：获取所有记忆
            cursor.execute(
                """
                SELECT * FROM memories
                WHERE state = ?
                ORDER BY final_score DESC
            """,
                (state,),
            )

            memories = [dict(row) for row in cursor.fetchall()]

            if not memories:
                return []

            # 第二次查询：批量获取实体
            memory_ids = [m["id"] for m in memories]
            placeholders = ",".join(["?"] * len(memory_ids))

            cursor.execute(
                f"""
                SELECT memory_id, entity
                FROM memory_entities
                WHERE memory_id IN ({placeholders})
            """,
                memory_ids,
            )

            # 应用层合并
            entity_map = {}
            for row in cursor.fetchall():
                mid = row["memory_id"]
                if mid not in entity_map:
                    entity_map[mid] = []
                entity_map[mid].append(row["entity"])

            # 合并结果
            for m in memories:
                m["entities"] = entity_map.get(m["id"], [])

            return memories

    def search_by_entities(self, entities: List[str], limit: int = 50) -> List[Dict]:
        """
        按实体搜索（参数化查询，防止 SQL 注入）

        Args:
            entities: 实体列表
            limit: 返回数量

        Returns:
            记忆列表
        """
        if not entities:
            return []

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 参数化查询
            placeholders = ",".join(["?"] * len(entities))
            query = f"""
                SELECT DISTINCT m.*
                FROM memories m
                JOIN memory_entities me ON m.id = me.memory_id
                WHERE me.entity IN ({placeholders})
                AND m.state = 0
                ORDER BY m.final_score DESC
                LIMIT ?
            """

            cursor.execute(query, entities + [limit])
            memories = [dict(row) for row in cursor.fetchall()]

            # 批量获取实体
            if memories:
                memory_ids = [m["id"] for m in memories]
                placeholders = ",".join(["?"] * len(memory_ids))

                cursor.execute(
                    f"""
                    SELECT memory_id, entity
                    FROM memory_entities
                    WHERE memory_id IN ({placeholders})
                """,
                    memory_ids,
                )

                entity_map = {}
                for row in cursor.fetchall():
                    mid = row["memory_id"]
                    if mid not in entity_map:
                        entity_map[mid] = []
                    entity_map[mid].append(row["entity"])

                for m in memories:
                    m["entities"] = entity_map.get(m["id"], [])

            return memories

    def update_access_stats(self, memory_id: str, access_type: str = "retrieval") -> bool:
        """
        更新访问统计（O(1) 操作）

        Args:
            memory_id: 记忆 ID
            access_type: 访问类型（retrieval/update）

        Returns:
            是否成功
        """
        with self._get_connection(write=True) as conn:
            cursor = conn.cursor()

            try:
                # 更新访问统计
                if access_type == "retrieval":
                    cursor.execute(
                        """
                        UPDATE memories
                        SET retrieval_count = retrieval_count + 1,
                            last_accessed = ?
                        WHERE id = ?
                    """,
                        (datetime.now().isoformat(), memory_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE memories
                        SET access_count = access_count + 1,
                            last_accessed = ?
                        WHERE id = ?
                    """,
                        (datetime.now().isoformat(), memory_id),
                    )

                # 记录访问日志（可选）
                cursor.execute(
                    """
                    INSERT INTO access_log (memory_id, access_type, timestamp)
                    VALUES (?, ?, ?)
                """,
                    (memory_id, access_type, datetime.now().isoformat()),
                )

                conn.commit()
                return True

            except Exception as e:
                conn.rollback()
                print(f"❌ 更新访问统计失败: {e}")
                return False

    def archive_memory(self, memory_id: str) -> bool:
        """归档记忆"""
        with self._get_connection(write=True) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE memories SET state = 1 WHERE id = ?", (memory_id,))
            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            # 总数
            cursor.execute("SELECT COUNT(*) as total FROM memories WHERE state = 0")
            stats["total"] = cursor.fetchone()["total"]

            # 按类型统计
            cursor.execute("""
                SELECT type, COUNT(*) as count
                FROM memories
                WHERE state = 0
                GROUP BY type
            """)
            stats["by_type"] = {row["type"]: row["count"] for row in cursor.fetchall()}

            # 归档数量
            cursor.execute("SELECT COUNT(*) as archived FROM memories WHERE state = 1")
            stats["archived"] = cursor.fetchone()["archived"]

            return stats

    def cleanup_expired(self) -> int:
        """清理过期记忆"""
        with self._get_connection(write=True) as conn:
            cursor = conn.cursor()

            now = datetime.now().isoformat()
            cursor.execute(
                """
                UPDATE memories
                SET state = 2
                WHERE auto_delete_at IS NOT NULL
                AND auto_delete_at < ?
                AND state = 0
            """,
                (now,),
            )

            conn.commit()
            return cursor.rowcount


# ============================================================
# 动态衰减计算（Lazy Update）
# ============================================================


class DecayCalculator:
    """衰减计算器"""

    # 衰减率（每天）
    DECAY_RATES = {
        "fact": 0.992,  # 0.8%/天
        "belief": 0.93,  # 7%/天
        "summary": 0.975,  # 2.5%/天
    }

    @classmethod
    def calculate_dynamic_score(cls, memory: Dict) -> float:
        """
        动态计算衰减后的分数

        Args:
            memory: 记忆字典

        Returns:
            衰减后的分数
        """
        created = datetime.fromisoformat(memory["created"])
        now = datetime.now()
        days_elapsed = (now - created).days

        # 基础衰减率
        base_decay = cls.DECAY_RATES.get(memory["type"], 0.992)

        # 重要性影响衰减（重要的记忆衰减更慢）
        importance = memory.get("importance", 0.5)
        actual_decay = base_decay ** (1 - importance * 0.5)

        # 计算衰减后的分数
        decayed_score = memory["score"] * (actual_decay**days_elapsed)

        return decayed_score + memory.get("access_boost", 0.0)

    @classmethod
    def add_dynamic_scores(cls, memories: List[Dict]) -> List[Dict]:
        """
        为记忆列表添加动态分数

        Args:
            memories: 记忆列表

        Returns:
            添加了 dynamic_score 字段的记忆列表
        """
        for m in memories:
            m["dynamic_score"] = cls.calculate_dynamic_score(m)

        # 按动态分数排序
        memories.sort(key=lambda x: x["dynamic_score"], reverse=True)

        return memories


# ============================================================
# 测试代码
# ============================================================

if __name__ == "__main__":
    import shutil
    import tempfile

    # 创建临时目录
    temp_dir = Path(tempfile.mkdtemp())

    try:
        print("🧪 测试 SQLite 后端（线程安全）")
        print("=" * 50)

        # 初始化
        backend = SQLiteBackend(temp_dir)

        # 插入测试数据
        test_memory = {
            "id": "test_001",
            "type": "fact",
            "content": "用户对花生过敏",
            "importance": 1.0,
            "score": 1.0,
            "created": datetime.now().isoformat(),
            "entities": ["用户", "花生"],
        }

        print("\n1. 插入记忆...")
        success = backend.insert_memory(test_memory)
        print(f"   {'✅' if success else '❌'} 插入{'成功' if success else '失败'}")

        # 查询
        print("\n2. 查询记忆...")
        memory = backend.get_memory("test_001")
        print(f"   ✅ 查询成功: {memory['content']}")

        # 按实体搜索
        print("\n3. 按实体搜索...")
        results = backend.search_by_entities(["用户"])
        print(f"   ✅ 找到 {len(results)} 条记忆")

        # 更新访问统计
        print("\n4. 更新访问统计...")
        backend.update_access_stats("test_001")
        memory = backend.get_memory("test_001")
        print(f"   ✅ 访问次数: {memory['retrieval_count']}")

        # 动态衰减计算
        print("\n5. 动态衰减计算...")
        dynamic_score = DecayCalculator.calculate_dynamic_score(memory)
        print(f"   ✅ 动态分数: {dynamic_score:.4f}")

        # 统计信息
        print("\n6. 统计信息...")
        stats = backend.get_stats()
        print(f"   ✅ 总记忆数: {stats['total']}")
        print(f"   ✅ 按类型: {stats['by_type']}")

        # 关闭连接
        backend.close()

        print("\n" + "=" * 50)
        print("✅ 所有测试通过！")

    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
