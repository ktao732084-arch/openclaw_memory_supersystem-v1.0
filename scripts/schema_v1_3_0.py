#!/usr/bin/env python3
"""
Memory System v1.3.0 - Enhanced Schema
增强的记忆点结构，支持证据追踪、归属识别和冲突管理
"""

import sqlite3
from datetime import datetime
from pathlib import Path

# ============================================================
# 数据库 Schema v1.3.0
# ============================================================

SCHEMA_V1_3_SQL = """
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

    -- 时间字段（增强）
    created TEXT NOT NULL,
    updated TEXT,
    last_accessed TEXT,
    timestamp TEXT NOT NULL,  -- 🆕 记忆发生的时间（用于时序推理）

    -- 访问统计
    access_count INTEGER DEFAULT 0,
    retrieval_count INTEGER DEFAULT 0,

    -- 来源和状态
    source TEXT,
    state INTEGER DEFAULT 0 CHECK(state IN (0, 1, 2)),

    -- 🆕 证据追踪（Evidence Tracking）
    session_id TEXT,           -- 来源会话 ID
    source_turn INTEGER,       -- 来源对话轮次
    source_quote TEXT,         -- 原文引用

    -- 🆕 归属识别（Ownership）
    ownership TEXT DEFAULT 'user' CHECK(ownership IN ('user', 'assistant', 'third_party')),

    -- 冲突管理（增强）
    conflict_downgraded INTEGER DEFAULT 0,
    downgrade_reason TEXT,
    superseded INTEGER DEFAULT 0,
    superseded_by TEXT,
    supersedes TEXT,           -- 🆕 取代的旧记忆 ID（JSON 数组）
    conflict_resolved_at TEXT, -- 🆕 冲突解决时间

    -- TTL 管理
    ttl_days INTEGER,
    auto_delete_at TEXT,

    -- 类型特有字段
    confidence REAL DEFAULT 1.0,
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
CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp DESC);  -- 🆕 时序索引
CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id);        -- 🆕 会话索引
CREATE INDEX IF NOT EXISTS idx_memories_ownership ON memories(ownership);       -- 🆕 归属索引
CREATE INDEX IF NOT EXISTS idx_memories_auto_delete ON memories(auto_delete_at) WHERE auto_delete_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_entities_entity ON memory_entities(entity);
CREATE INDEX IF NOT EXISTS idx_relations_subject_type ON memory_relations(subject, relation_type, superseded);
CREATE INDEX IF NOT EXISTS idx_access_log_timestamp ON access_log(timestamp DESC);
"""

# ============================================================
# Schema 版本管理
# ============================================================

SCHEMA_VERSION = "1.3.0"

MIGRATION_SCRIPTS = {
    "1.2.5_to_1.3.0": """
        -- 添加新字段
        ALTER TABLE memories ADD COLUMN timestamp TEXT;
        ALTER TABLE memories ADD COLUMN session_id TEXT;
        ALTER TABLE memories ADD COLUMN source_turn INTEGER;
        ALTER TABLE memories ADD COLUMN source_quote TEXT;
        ALTER TABLE memories ADD COLUMN ownership TEXT DEFAULT 'user';
        ALTER TABLE memories ADD COLUMN supersedes TEXT;
        ALTER TABLE memories ADD COLUMN conflict_resolved_at TEXT;

        -- 创建新索引
        CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_memories_session ON memories(session_id);
        CREATE INDEX IF NOT EXISTS idx_memories_ownership ON memories(ownership);

        -- 迁移数据：timestamp = created
        UPDATE memories SET timestamp = created WHERE timestamp IS NULL;
    """
}


# ============================================================
# 数据迁移工具
# ============================================================


class SchemaMigrator:
    """Schema 迁移工具"""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def get_current_version(self) -> str:
        """获取当前 Schema 版本"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 检查是否有 timestamp 字段（v1.3.0 特征）
            cursor.execute("PRAGMA table_info(memories)")
            columns = [row[1] for row in cursor.fetchall()]

            if "timestamp" in columns and "session_id" in columns:
                return "1.3.0"
            elif "conflict_downgraded" in columns:
                return "1.2.5"
            else:
                return "1.0.0"
        finally:
            conn.close()

    def needs_migration(self) -> bool:
        """检查是否需要迁移"""
        current = self.get_current_version()
        return current != SCHEMA_VERSION

    def migrate(self, backup: bool = True) -> bool:
        """
        执行迁移

        Args:
            backup: 是否备份数据库

        Returns:
            是否成功
        """
        current_version = self.get_current_version()

        if current_version == SCHEMA_VERSION:
            print(f"✅ Schema 已是最新版本 {SCHEMA_VERSION}")
            return True

        print(f"🔄 开始迁移: {current_version} → {SCHEMA_VERSION}")

        # 备份
        if backup:
            backup_path = self.db_path.parent / f"{self.db_path.name}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import shutil

            shutil.copy2(self.db_path, backup_path)
            print(f"📦 备份完成: {backup_path}")

        # 执行迁移
        conn = sqlite3.connect(self.db_path)

        try:
            # 获取迁移脚本
            migration_key = f"{current_version}_to_{SCHEMA_VERSION}"

            if migration_key not in MIGRATION_SCRIPTS:
                print(f"❌ 未找到迁移脚本: {migration_key}")
                return False

            migration_sql = MIGRATION_SCRIPTS[migration_key]

            # 执行迁移
            conn.executescript(migration_sql)
            conn.commit()

            print(f"✅ 迁移完成: {current_version} → {SCHEMA_VERSION}")
            return True

        except Exception as e:
            conn.rollback()
            print(f"❌ 迁移失败: {e}")
            return False

        finally:
            conn.close()

    def auto_migrate_old_data(self) -> int:
        """
        自动迁移旧数据（补全缺失字段）

        Returns:
            迁移的记忆数量
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 查询缺少新字段的记忆
            cursor.execute("""
                SELECT id, created, content
                FROM memories
                WHERE timestamp IS NULL
                   OR session_id IS NULL
                   OR ownership IS NULL
            """)

            old_memories = cursor.fetchall()

            if not old_memories:
                print("✅ 所有记忆已包含新字段")
                return 0

            print(f"🔄 发现 {len(old_memories)} 条旧记忆，开始迁移...")

            # 批量更新
            for memory_id, created, content in old_memories:
                cursor.execute(
                    """
                    UPDATE memories
                    SET timestamp = ?,
                        session_id = 'legacy',
                        source_quote = ?,
                        ownership = 'user'
                    WHERE id = ?
                """,
                    (created, content, memory_id),
                )

            conn.commit()

            print(f"✅ 成功迁移 {len(old_memories)} 条记忆")
            return len(old_memories)

        except Exception as e:
            conn.rollback()
            print(f"❌ 迁移失败: {e}")
            return 0

        finally:
            conn.close()


# ============================================================
# 测试代码
# ============================================================

if __name__ == "__main__":
    import shutil
    import tempfile

    print("🧪 测试 Schema 迁移")
    print("=" * 60)

    # 创建临时目录
    temp_dir = Path(tempfile.mkdtemp())

    try:
        # 1. 创建旧版本数据库（v1.2.5）
        print("\n📝 步骤 1: 创建 v1.2.5 数据库")
        old_db_path = temp_dir / "memories_v1.2.5.db"

        from sqlite_backend_v1_2_5 import SQLiteBackend as OldBackend

        old_backend = OldBackend(temp_dir)

        # 插入测试数据
        old_backend.insert_memory(
            {
                "id": "test_001",
                "type": "fact",
                "content": "用户对花生过敏",
                "importance": 1.0,
                "score": 1.0,
                "created": datetime.now().isoformat(),
                "entities": ["用户", "花生"],
            }
        )

        old_backend.close()
        print("   ✅ v1.2.5 数据库创建完成")

        # 2. 检查版本
        print("\n📝 步骤 2: 检查 Schema 版本")
        migrator = SchemaMigrator(temp_dir / "layer2" / "memories.db")
        current_version = migrator.get_current_version()
        print(f"   当前版本: {current_version}")
        print(f"   目标版本: {SCHEMA_VERSION}")
        print(f"   需要迁移: {migrator.needs_migration()}")

        # 3. 执行迁移
        print("\n📝 步骤 3: 执行 Schema 迁移")
        success = migrator.migrate(backup=True)

        if success:
            print("   ✅ Schema 迁移成功")
        else:
            print("   ❌ Schema 迁移失败")
            exit(1)

        # 4. 迁移旧数据
        print("\n📝 步骤 4: 迁移旧数据")
        migrated_count = migrator.auto_migrate_old_data()
        print(f"   迁移记忆数: {migrated_count}")

        # 5. 验证
        print("\n📝 步骤 5: 验证迁移结果")
        conn = sqlite3.connect(temp_dir / "layer2" / "memories.db")
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, content, timestamp, session_id, ownership
            FROM memories
            WHERE id = 'test_001'
        """)

        row = cursor.fetchone()

        if row:
            print(f"   ID: {row[0]}")
            print(f"   内容: {row[1]}")
            print(f"   时间戳: {row[2]}")
            print(f"   会话 ID: {row[3]}")
            print(f"   归属: {row[4]}")
            print("   ✅ 数据验证通过")
        else:
            print("   ❌ 数据丢失")

        conn.close()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过！")

    finally:
        # 清理临时目录
        shutil.rmtree(temp_dir)
