#!/usr/bin/env python3
"""
Memory System v1.8.0 - 数据迁移脚本
从单文件 SQLite/JSONL 迁移到分片存储

用法:
    python migrate_to_sharded.py <memory_dir> [--shard-size 10000] [--backup]
"""

import argparse
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Optional


def migrate_jsonl_to_sharded(
    memory_dir: Path,
    shard_dir: Path,
    shard_size: int = 10000,
    backup: bool = True,
    progress_callback: Optional[callable] = None,
) -> tuple[int, int]:
    """
    从 JSONL 迁移到分片存储

    返回: (成功数, 失败数)
    """
    from sharded_index import ShardedIndexManager

    shard_dir.mkdir(parents=True, exist_ok=True)
    manager = ShardedIndexManager(shard_dir, shard_size)

    success_count = 0
    fail_count = 0

    for mem_type in ["facts", "beliefs", "summaries"]:
        jsonl_path = memory_dir / "layer2" / "active" / f"{mem_type}.jsonl"

        if not jsonl_path.exists():
            continue

        if backup:
            backup_path = jsonl_path.with_suffix(".jsonl.migration_backup")
            if not backup_path.exists():
                shutil.copy2(jsonl_path, backup_path)
                print(f"✅ 备份: {jsonl_path} -> {backup_path}")

        print(f"📝 迁移 {mem_type}...")

        with open(jsonl_path, encoding="utf-8") as f:
            batch = []
            for line_num, line in enumerate(f, 1):
                if not line.strip():
                    continue

                try:
                    record = json.loads(line)
                    record["type"] = mem_type.rstrip("s")

                    batch.append(record)

                    if len(batch) >= 1000:
                        for m in batch:
                            try:
                                manager.insert(m)
                                success_count += 1
                            except Exception as e:
                                print(f"   ⚠️ 插入失败: {m.get('id', 'unknown')}: {e}")
                                fail_count += 1

                        if progress_callback:
                            progress_callback(success_count, fail_count)

                        batch = []

                except json.JSONDecodeError as e:
                    print(f"   ⚠️ JSON 解析失败 (行 {line_num}): {e}")
                    fail_count += 1

            for m in batch:
                try:
                    manager.insert(m)
                    success_count += 1
                except Exception as e:
                    print(f"   ⚠️ 插入失败: {m.get('id', 'unknown')}: {e}")
                    fail_count += 1

    stats = manager.get_stats()
    print("\n📊 迁移统计:")
    print(f"   总记忆数: {stats['total_memories']}")
    print(f"   分片数: {stats['shard_count']}")
    print(f"   成功: {success_count}")
    print(f"   失败: {fail_count}")

    manager.close()

    return success_count, fail_count


def migrate_sqlite_to_sharded(
    sqlite_path: Path,
    shard_dir: Path,
    shard_size: int = 10000,
    backup: bool = True,
    progress_callback: Optional[callable] = None,
) -> tuple[int, int]:
    """
    从单文件 SQLite 迁移到分片存储

    返回: (成功数, 失败数)
    """
    from sharded_index import ShardedIndexManager

    if not sqlite_path.exists():
        print(f"❌ SQLite 文件不存在: {sqlite_path}")
        return 0, 0

    if backup:
        backup_path = sqlite_path.with_suffix(".db.migration_backup")
        if not backup_path.exists():
            shutil.copy2(sqlite_path, backup_path)
            print(f"✅ 备份: {sqlite_path} -> {backup_path}")

    shard_dir.mkdir(parents=True, exist_ok=True)
    manager = ShardedIndexManager(shard_dir, shard_size)

    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    success_count = 0
    fail_count = 0

    try:
        cursor.execute("SELECT * FROM memories WHERE state = 0")

        batch = []
        for row in cursor.fetchall():
            try:
                record = {
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
                }

                batch.append(record)

                if len(batch) >= 1000:
                    for m in batch:
                        try:
                            manager.insert(m)
                            success_count += 1
                        except Exception:
                            fail_count += 1

                    if progress_callback:
                        progress_callback(success_count, fail_count)

                    batch = []

            except Exception as e:
                print(f"   ⚠️ 处理记录失败: {row['id']}: {e}")
                fail_count += 1

        for m in batch:
            try:
                manager.insert(m)
                success_count += 1
            except Exception:
                fail_count += 1

    finally:
        conn.close()

    stats = manager.get_stats()
    print("\n📊 迁移统计:")
    print(f"   总记忆数: {stats['total_memories']}")
    print(f"   分片数: {stats['shard_count']}")
    print(f"   成功: {success_count}")
    print(f"   失败: {fail_count}")

    manager.close()

    return success_count, fail_count


def verify_migration(source_path: Path, shard_dir: Path, sample_size: int = 100) -> dict:
    """
    验证迁移结果

    返回验证报告
    """
    from sharded_index import ShardedIndexManager

    manager = ShardedIndexManager(shard_dir)

    report = {
        "source_type": None,
        "source_count": 0,
        "target_count": 0,
        "verified_count": 0,
        "missing_count": 0,
        "corrupted_count": 0,
        "sample_verified": 0,
        "success": False,
    }

    jsonl_count = 0
    for mem_type in ["facts", "beliefs", "summaries"]:
        jsonl_path = source_path / "layer2" / "active" / f"{mem_type}.jsonl"
        if jsonl_path.exists():
            with open(jsonl_path, encoding="utf-8") as f:
                jsonl_count += sum(1 for line in f if line.strip())

    sqlite_path = source_path / "layer2" / "memories.db"
    sqlite_count = 0
    if sqlite_path.exists():
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM memories WHERE state = 0")
        sqlite_count = cursor.fetchone()[0]
        conn.close()

    if jsonl_count > 0:
        report["source_type"] = "jsonl"
        report["source_count"] = jsonl_count
    elif sqlite_count > 0:
        report["source_type"] = "sqlite"
        report["source_count"] = sqlite_count

    stats = manager.get_stats()
    report["target_count"] = stats["total_memories"]

    if sqlite_path.exists():
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM memories WHERE state = 0 LIMIT ?", (sample_size,))

        for row in cursor.fetchall():
            memory_id = row["id"]
            target_memory = manager.get_by_id(memory_id)

            if target_memory is None:
                report["missing_count"] += 1
            else:
                report["verified_count"] += 1

        conn.close()
        report["sample_verified"] = sample_size

    report["success"] = (
        report["missing_count"] == 0
        and report["corrupted_count"] == 0
        and report["target_count"] >= report["source_count"] * 0.99
    )

    manager.close()

    return report


def print_migration_report(report: dict):
    """打印迁移报告"""
    print("\n" + "=" * 50)
    print("📋 迁移验证报告")
    print("=" * 50)
    print(f"源类型: {report['source_type']}")
    print(f"源记录数: {report['source_count']}")
    print(f"目标记录数: {report['target_count']}")
    print(f"验证样本: {report['sample_verified']}")
    print(f"验证通过: {report['verified_count']}")
    print(f"缺失记录: {report['missing_count']}")
    print(f"损坏记录: {report['corrupted_count']}")
    print("=" * 50)

    if report["success"]:
        print("✅ 迁移验证通过")
    else:
        print("⚠️ 迁移验证发现问题")


def main():
    parser = argparse.ArgumentParser(
        description="Memory System 数据迁移工具", formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("memory_dir", help="记忆系统目录")

    parser.add_argument("--shard-size", type=int, default=10000, help="分片大小（默认 10000）")

    parser.add_argument("--backup", action="store_true", default=True, help="备份原始数据（默认启用）")

    parser.add_argument("--no-backup", action="store_true", help="不备份原始数据")

    parser.add_argument("--verify", action="store_true", help="迁移后验证")

    parser.add_argument("--verify-only", action="store_true", help="仅验证（不执行迁移）")

    args = parser.parse_args()

    memory_dir = Path(args.memory_dir)
    shard_dir = memory_dir / "shards"

    backup = args.backup and not args.no_backup

    if args.verify_only:
        print("🔍 仅验证模式")
        report = verify_migration(memory_dir, shard_dir)
        print_migration_report(report)
        return

    print("🚀 开始迁移...")
    print(f"   源目录: {memory_dir}")
    print(f"   目标目录: {shard_dir}")
    print(f"   分片大小: {args.shard_size}")
    print(f"   备份: {'是' if backup else '否'}")
    print()

    sqlite_path = memory_dir / "layer2" / "memories.db"

    if sqlite_path.exists():
        print("📦 检测到 SQLite 数据库，从 SQLite 迁移...")
        success, fail = migrate_sqlite_to_sharded(sqlite_path, shard_dir, args.shard_size, backup)
    else:
        print("📦 从 JSONL 文件迁移...")
        success, fail = migrate_jsonl_to_sharded(memory_dir, shard_dir, args.shard_size, backup)

    print(f"\n✅ 迁移完成: 成功 {success}, 失败 {fail}")

    if args.verify:
        print("\n🔍 验证迁移结果...")
        report = verify_migration(memory_dir, shard_dir)
        print_migration_report(report)


if __name__ == "__main__":
    main()
