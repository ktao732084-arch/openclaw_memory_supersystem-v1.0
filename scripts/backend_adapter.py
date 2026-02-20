#!/usr/bin/env python3
"""
Memory System v1.2.4 - 双后端适配器
支持 JSONL 和 SQLite 双后端，平滑过渡
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# 尝试导入 SQLite 后端
try:
    from sqlite_backend import SQLiteBackend

    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False
    print("⚠️ SQLite 后端不可用，使用 JSONL 后端")


class MemoryBackend:
    """记忆后端适配器"""

    def __init__(self, memory_dir: Path, use_sqlite: bool = False):
        self.memory_dir = Path(memory_dir)
        self.use_sqlite = use_sqlite and SQLITE_AVAILABLE

        if self.use_sqlite:
            self.sqlite = SQLiteBackend(memory_dir)
            print("✅ 使用 SQLite 后端")
        else:
            self.sqlite = None
            print("✅ 使用 JSONL 后端")

    def insert_memory(self, record: Dict[str, Any]) -> bool:
        """插入记忆（双写）"""
        success = True

        # 写入 JSONL（保持兼容）
        try:
            mem_type = record.get("type", "fact")
            if mem_type == "fact":
                jsonl_path = self.memory_dir / "layer2/active/facts.jsonl"
            elif mem_type == "belief":
                jsonl_path = self.memory_dir / "layer2/active/beliefs.jsonl"
            elif mem_type == "summary":
                jsonl_path = self.memory_dir / "layer2/active/summaries.jsonl"
            else:
                jsonl_path = self.memory_dir / "layer2/active/facts.jsonl"

            with open(jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"❌ JSONL 写入失败: {e}")
            success = False

        # 写入 SQLite（如果启用）
        if self.use_sqlite:
            try:
                if not self.sqlite.insert_memory(record):
                    success = False
            except Exception as e:
                print(f"❌ SQLite 写入失败: {e}")
                success = False

        return success

    def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """获取记忆"""
        if self.use_sqlite:
            return self.sqlite.get_memory(memory_id)
        else:
            # JSONL 后端：需要扫描所有文件
            for mem_type in ["facts", "beliefs", "summaries"]:
                jsonl_path = self.memory_dir / f"layer2/active/{mem_type}.jsonl"
                if not jsonl_path.exists():
                    continue

                with open(jsonl_path, encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        record = json.loads(line)
                        if record.get("id") == memory_id:
                            return record
            return None

    def update_access_stats(self, memory_id: str, access_type: str) -> bool:
        """更新访问统计"""
        if self.use_sqlite:
            # SQLite: O(1) 更新
            return self.sqlite.update_access_stats(memory_id, access_type)
        else:
            # JSONL: O(N) 全文件读写（保持原有逻辑）
            # 这里不实现，保持与原 memory.py 一致
            return True

    def search_by_entities(self, entities: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """通过实体搜索"""
        if self.use_sqlite:
            return self.sqlite.search_by_entities(entities, limit)
        else:
            # JSONL 后端：使用原有的 entity_search 逻辑
            # 这里不实现，保持与原 memory.py 一致
            return []

    def get_all_active_memories(self, mem_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取所有活跃记忆"""
        if self.use_sqlite:
            return self.sqlite.get_all_active_memories(mem_type)
        else:
            # JSONL 后端
            results = []
            types_to_load = [mem_type] if mem_type else ["fact", "belief", "summary"]

            for t in types_to_load:
                if t == "fact":
                    jsonl_path = self.memory_dir / "layer2/active/facts.jsonl"
                elif t == "belief":
                    jsonl_path = self.memory_dir / "layer2/active/beliefs.jsonl"
                elif t == "summary":
                    jsonl_path = self.memory_dir / "layer2/active/summaries.jsonl"
                else:
                    continue

                if not jsonl_path.exists():
                    continue

                with open(jsonl_path, encoding="utf-8") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        record = json.loads(line)
                        results.append(record)

            return results

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        if self.use_sqlite:
            return self.sqlite.get_stats()
        else:
            # JSONL 后端：统计文件行数
            stats = {"total": 0, "facts": 0, "beliefs": 0, "summaries": 0, "archived": 0}

            for mem_type in ["facts", "beliefs", "summaries"]:
                jsonl_path = self.memory_dir / f"layer2/active/{mem_type}.jsonl"
                if jsonl_path.exists():
                    count = sum(1 for line in open(jsonl_path) if line.strip())
                    stats[mem_type[:-1] if mem_type.endswith("s") else mem_type] = count
                    stats["total"] += count

            return stats


# ============================================================
# 配置管理
# ============================================================


def get_backend_config(memory_dir: Path) -> Dict[str, Any]:
    """获取后端配置"""
    config_path = memory_dir / "config.json"

    if not config_path.exists():
        return {"backend": "jsonl"}  # 默认使用 JSONL

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    return config.get("storage", {"backend": "jsonl"})


def set_backend_config(memory_dir: Path, backend: str):
    """设置后端配置"""
    config_path = memory_dir / "config.json"

    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)
    else:
        config = {}

    if "storage" not in config:
        config["storage"] = {}

    config["storage"]["backend"] = backend

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"✅ 后端配置已更新: {backend}")


# ============================================================
# 测试函数
# ============================================================


def test_backend_adapter(memory_dir: Path):
    """测试后端适配器"""
    print("🧪 测试后端适配器...")

    # 测试 JSONL 后端
    print("\n1. 测试 JSONL 后端:")
    backend_jsonl = MemoryBackend(memory_dir, use_sqlite=False)
    stats = backend_jsonl.get_stats()
    print(f"   总记忆数: {stats['total']}")

    # 测试 SQLite 后端
    if SQLITE_AVAILABLE:
        print("\n2. 测试 SQLite 后端:")
        backend_sqlite = MemoryBackend(memory_dir, use_sqlite=True)
        stats = backend_sqlite.get_stats()
        print(f"   总记忆数: {stats['total']}")

        # 测试搜索
        print("\n3. 测试 SQLite 搜索:")
        results = backend_sqlite.search_by_entities(["Ktao"], limit=3)
        print(f"   找到 {len(results)} 条记忆")
    else:
        print("\n2. SQLite 后端不可用")

    print("\n✅ 测试完成！")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python backend_adapter.py <memory_dir> [test|config]")
        sys.exit(1)

    memory_dir = Path(sys.argv[1])
    action = sys.argv[2] if len(sys.argv) > 2 else "test"

    if action == "test":
        test_backend_adapter(memory_dir)
    elif action == "config":
        backend = sys.argv[3] if len(sys.argv) > 3 else "jsonl"
        set_backend_config(memory_dir, backend)
