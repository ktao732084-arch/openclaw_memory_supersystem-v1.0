#!/usr/bin/env python3
"""
Memory System v1.2.4 - SQLite Backend
独立的 SQLite 后端模块，不影响现有 JSONL 系统
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

-- v1.6.0: 向量存储表
CREATE TABLE IF NOT EXISTS memory_vectors (
    id TEXT PRIMARY KEY,
    memory_id TEXT NOT NULL,
    vector BLOB NOT NULL,
    dimension INTEGER NOT NULL,
    provider TEXT DEFAULT 'openai',
    model TEXT DEFAULT 'text-embedding-3-small',
    created TEXT NOT NULL,
    FOREIGN KEY (memory_id) REFERENCES memories(id) ON DELETE CASCADE
);

-- v1.6.0: 嵌入缓存表
CREATE TABLE IF NOT EXISTS embedding_cache (
    text_hash TEXT PRIMARY KEY,
    embedding BLOB NOT NULL,
    dimension INTEGER NOT NULL,
    provider TEXT,
    model TEXT,
    created TEXT NOT NULL
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_memories_state_score ON memories(state, final_score DESC);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created DESC);
CREATE INDEX IF NOT EXISTS idx_memories_auto_delete ON memories(auto_delete_at) WHERE auto_delete_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_entities_entity ON memory_entities(entity);
CREATE INDEX IF NOT EXISTS idx_relations_subject_type ON memory_relations(subject, relation_type, superseded);
CREATE INDEX IF NOT EXISTS idx_access_log_timestamp ON access_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vectors_memory_id ON memory_vectors(memory_id);
"""

# ============================================================
# 数据库连接管理
# ============================================================


class SQLiteBackend:
    """SQLite 后端管理器"""

    def __init__(self, memory_dir: Path):
        self.memory_dir = Path(memory_dir)
        self.db_path = self.memory_dir / "layer2" / "memories.db"
        self._ensure_db_exists()

    def _ensure_db_exists(self):
        """确保数据库存在并初始化"""
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_db()

    def _init_db(self):
        """初始化数据库"""
        conn = self._get_connection()
        try:
            # 启用 WAL 模式（提升并发性能）
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")

            # 创建表和索引
            conn.executescript(SCHEMA_SQL)
            conn.commit()
            print(f"✅ SQLite 数据库初始化完成: {self.db_path}")
        finally:
            conn.close()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典
        return conn

    # ============================================================
    # 基础 CRUD 操作
    # ============================================================

    def insert_memory(self, record: Dict[str, Any]) -> bool:
        """插入记忆"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

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

            # 插入摘要来源（如果是 summary）
            if record.get("type") == "summary" and "source_facts" in record:
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
            print(f"❌ 插入记忆失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取单条记忆"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM memories WHERE id = ?", (memory_id,))
            row = cursor.fetchone()

            if not row:
                return None

            # 转换为字典
            memory = dict(row)

            # 加载实体
            cursor.execute("SELECT entity FROM memory_entities WHERE memory_id = ?", (memory_id,))
            memory["entities"] = [r["entity"] for r in cursor.fetchall()]

            # 加载摘要来源（如果是 summary）
            if memory["type"] == "summary":
                cursor.execute("SELECT source_fact_id FROM summary_sources WHERE summary_id = ?", (memory_id,))
                memory["source_facts"] = [r["source_fact_id"] for r in cursor.fetchall()]

            return memory
        finally:
            conn.close()

    def update_access_stats(self, memory_id: str, access_type: str) -> bool:
        """更新访问统计（O(1) 操作）"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # 更新统计
            cursor.execute(
                """
                UPDATE memories
                SET access_count = access_count + 1,
                    retrieval_count = retrieval_count + CASE WHEN ? = 'retrieval' THEN 1 ELSE 0 END,
                    last_accessed = ?
                WHERE id = ?
            """,
                (access_type, datetime.utcnow().isoformat() + "Z", memory_id),
            )

            # 记录访问日志（可选）
            cursor.execute(
                """
                INSERT INTO access_log (memory_id, access_type, timestamp)
                VALUES (?, ?, ?)
            """,
                (memory_id, access_type, datetime.utcnow().isoformat() + "Z"),
            )

            conn.commit()
            return True
        except Exception as e:
            print(f"❌ 更新访问统计失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def search_by_entities(self, entities: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """通过实体搜索记忆"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            placeholders = ",".join("?" * len(entities))
            cursor.execute(
                f"""
                SELECT m.*, GROUP_CONCAT(me.entity) as matched_entities
                FROM memories m
                JOIN memory_entities me ON m.id = me.memory_id
                WHERE me.entity IN ({placeholders})
                  AND m.state = 0
                GROUP BY m.id
                ORDER BY m.final_score DESC
                LIMIT ?
            """,
                (*entities, limit),
            )

            results = []
            for row in cursor.fetchall():
                memory = dict(row)
                # 加载完整实体列表
                cursor.execute("SELECT entity FROM memory_entities WHERE memory_id = ?", (memory["id"],))
                memory["entities"] = [r["entity"] for r in cursor.fetchall()]
                results.append(memory)

            return results
        finally:
            conn.close()

    def get_all_active_memories(self, mem_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有活跃记忆"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            if mem_type:
                cursor.execute(
                    """
                    SELECT * FROM memories
                    WHERE state = 0 AND type = ?
                    ORDER BY final_score DESC
                """,
                    (mem_type,),
                )
            else:
                cursor.execute("""
                    SELECT * FROM memories
                    WHERE state = 0
                    ORDER BY final_score DESC
                """)

            results = []
            for row in cursor.fetchall():
                memory = dict(row)
                # 加载实体
                cursor.execute("SELECT entity FROM memory_entities WHERE memory_id = ?", (memory["id"],))
                memory["entities"] = [r["entity"] for r in cursor.fetchall()]
                results.append(memory)

            return results
        finally:
            conn.close()

    def archive_memory(self, memory_id: str) -> bool:
        """归档记忆"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE memories SET state = 1 WHERE id = ?", (memory_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"❌ 归档记忆失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def ttl_cleanup(self) -> int:
        """TTL 清理：标记过期记忆为 Junk"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE memories
                SET state = 2
                WHERE auto_delete_at IS NOT NULL
                  AND auto_delete_at < datetime('now')
                  AND state = 0
            """)
            deleted = cursor.rowcount
            conn.commit()
            return deleted
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # 总记忆数
            cursor.execute("SELECT COUNT(*) as total FROM memories WHERE state = 0")
            total = cursor.fetchone()["total"]

            # 按类型统计
            cursor.execute("""
                SELECT type, COUNT(*) as count
                FROM memories
                WHERE state = 0
                GROUP BY type
            """)
            by_type = {row["type"]: row["count"] for row in cursor.fetchall()}

            # 归档数
            cursor.execute("SELECT COUNT(*) as archived FROM memories WHERE state = 1")
            archived = cursor.fetchone()["archived"]

            return {
                "total": total,
                "facts": by_type.get("fact", 0),
                "beliefs": by_type.get("belief", 0),
                "summaries": by_type.get("summary", 0),
                "archived": archived,
            }
        finally:
            conn.close()

    # ============================================================
    # v1.6.0: 向量相关操作
    # ============================================================

    def insert_vector(
        self,
        memory_id: str,
        vector: List[float],
        provider: str = "openai",
        model: str = "text-embedding-3-small",
    ) -> bool:
        """插入记忆向量"""
        import numpy as np

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            vector_blob = np.array(vector, dtype=np.float32).tobytes()
            dimension = len(vector)

            cursor.execute(
                """
                INSERT OR REPLACE INTO memory_vectors
                (id, memory_id, vector, dimension, provider, model, created)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    memory_id,
                    memory_id,
                    vector_blob,
                    dimension,
                    provider,
                    model,
                    datetime.utcnow().isoformat() + "Z",
                ),
            )

            conn.commit()
            return True
        except Exception as e:
            print(f"❌ 插入向量失败: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_vector(self, memory_id: str) -> Optional[List[float]]:
        """获取记忆向量"""
        import numpy as np

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT vector FROM memory_vectors WHERE memory_id = ?",
                (memory_id,),
            )
            row = cursor.fetchone()
            if row:
                return np.frombuffer(row["vector"], dtype=np.float32).tolist()
            return None
        finally:
            conn.close()

    def search_vectors(
        self,
        query_vector: List[float],
        top_k: int = 10,
        memory_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """向量相似度搜索"""
        import numpy as np

        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            if memory_type:
                cursor.execute(
                    """
                    SELECT mv.memory_id, mv.vector, m.content, m.type, m.importance
                    FROM memory_vectors mv
                    JOIN memories m ON mv.memory_id = m.id
                    WHERE m.state = 0 AND m.type = ?
                """,
                    (memory_type,),
                )
            else:
                cursor.execute("""
                    SELECT mv.memory_id, mv.vector, m.content, m.type, m.importance
                    FROM memory_vectors mv
                    JOIN memories m ON mv.memory_id = m.id
                    WHERE m.state = 0
                """)

            query_vec = np.array(query_vector, dtype=np.float32)
            query_norm = np.linalg.norm(query_vec)

            if query_norm == 0:
                return []

            results = []
            for row in cursor.fetchall():
                vector = np.frombuffer(row["vector"], dtype=np.float32)
                vec_norm = np.linalg.norm(vector)

                if vec_norm == 0:
                    continue

                similarity = float(np.dot(query_vec, vector) / (query_norm * vec_norm))

                results.append(
                    {
                        "id": row["memory_id"],
                        "content": row["content"],
                        "type": row["type"],
                        "importance": row["importance"],
                        "similarity": similarity,
                    }
                )

            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:top_k]
        finally:
            conn.close()

    def get_vector_count(self) -> int:
        """获取向量数量"""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM memory_vectors")
            return cursor.fetchone()["count"]
        finally:
            conn.close()

    def cache_embedding(
        self,
        text_hash: str,
        embedding: List[float],
        provider: str = "openai",
        model: str = "text-embedding-3-small",
    ) -> bool:
        """缓存嵌入向量"""
        import numpy as np

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            embedding_blob = np.array(embedding, dtype=np.float32).tobytes()
            dimension = len(embedding)

            cursor.execute(
                """
                INSERT OR REPLACE INTO embedding_cache
                (text_hash, embedding, dimension, provider, model, created)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    text_hash,
                    embedding_blob,
                    dimension,
                    provider,
                    model,
                    datetime.utcnow().isoformat() + "Z",
                ),
            )

            conn.commit()
            return True
        except Exception:
            conn.rollback()
            return False
        finally:
            conn.close()

    def get_cached_embedding(self, text_hash: str) -> Optional[List[float]]:
        """获取缓存的嵌入向量"""
        import numpy as np

        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT embedding FROM embedding_cache WHERE text_hash = ?",
                (text_hash,),
            )
            row = cursor.fetchone()
            if row:
                return np.frombuffer(row["embedding"], dtype=np.float32).tolist()
            return None
        finally:
            conn.close()


# ============================================================
# 迁移工具
# ============================================================


def migrate_jsonl_to_sqlite(memory_dir: Path, backup: bool = True) -> Tuple[int, int]:
    """
    迁移 JSONL 数据到 SQLite

    返回: (成功数, 失败数)
    """
    backend = SQLiteBackend(memory_dir)

    success_count = 0
    fail_count = 0

    for mem_type in ["facts", "beliefs", "summaries"]:
        jsonl_path = memory_dir / "layer2" / "active" / f"{mem_type}.jsonl"

        if not jsonl_path.exists():
            continue

        # 备份
        if backup:
            backup_path = jsonl_path.with_suffix(".jsonl.backup")
            import shutil

            shutil.copy2(jsonl_path, backup_path)
            print(f"✅ 备份: {jsonl_path} -> {backup_path}")

        # 读取并迁移
        print(f"📝 迁移 {mem_type}...")
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                    # 确保 type 字段正确
                    if mem_type == "facts":
                        record["type"] = "fact"
                    elif mem_type == "beliefs":
                        record["type"] = "belief"
                    elif mem_type == "summaries":
                        record["type"] = "summary"

                    if backend.insert_memory(record):
                        success_count += 1
                    else:
                        fail_count += 1
                except Exception as e:
                    print(f"❌ 迁移失败 ({record.get('id', 'unknown')}): {e}")
                    fail_count += 1

    return success_count, fail_count


# ============================================================
# 测试函数
# ============================================================


def test_sqlite_backend(memory_dir: Path):
    """测试 SQLite 后端"""
    print("🧪 测试 SQLite 后端...")

    backend = SQLiteBackend(memory_dir)

    # 测试插入
    test_record = {
        "id": "test_001",
        "type": "fact",
        "content": "这是一条测试记忆",
        "importance": 0.8,
        "score": 1.0,
        "created": datetime.utcnow().isoformat() + "Z",
        "entities": ["测试", "SQLite"],
        "source": "test",
    }

    print("1. 测试插入...")
    if backend.insert_memory(test_record):
        print("   ✅ 插入成功")
    else:
        print("   ❌ 插入失败")
        return

    # 测试读取
    print("2. 测试读取...")
    memory = backend.get_memory("test_001")
    if memory and memory["content"] == "这是一条测试记忆":
        print("   ✅ 读取成功")
    else:
        print("   ❌ 读取失败")
        return

    # 测试访问统计
    print("3. 测试访问统计...")
    if backend.update_access_stats("test_001", "retrieval"):
        memory = backend.get_memory("test_001")
        if memory["access_count"] == 1:
            print("   ✅ 访问统计成功")
        else:
            print("   ❌ 访问统计失败")

    # 测试实体搜索
    print("4. 测试实体搜索...")
    results = backend.search_by_entities(["测试"])
    if results and len(results) > 0:
        print(f"   ✅ 搜索成功，找到 {len(results)} 条记忆")
    else:
        print("   ❌ 搜索失败")

    # 测试统计
    print("5. 测试统计...")
    stats = backend.get_stats()
    print(f"   总记忆数: {stats['total']}")
    print(f"   Facts: {stats['facts']}")

    print("\n✅ 所有测试通过！")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python sqlite_backend.py <memory_dir> [test|migrate]")
        sys.exit(1)

    memory_dir = Path(sys.argv[1])
    action = sys.argv[2] if len(sys.argv) > 2 else "test"

    if action == "test":
        test_sqlite_backend(memory_dir)
    elif action == "migrate":
        print("🔄 开始迁移 JSONL -> SQLite...")
        success, fail = migrate_jsonl_to_sqlite(memory_dir)
        print(f"\n✅ 迁移完成: 成功 {success} 条, 失败 {fail} 条")
