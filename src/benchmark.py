#!/usr/bin/env python3
"""
Memory System v1.2.4 - 性能对比测试
对比 JSONL vs SQLite 的性能差异
"""

import time
import json
from pathlib import Path
from backend_adapter import MemoryBackend

def benchmark_access_update(memory_dir: Path, iterations: int = 100):
    """测试访问统计更新性能"""
    print(f"\n📊 访问统计更新性能测试 ({iterations} 次)")
    print("=" * 60)
    
    # 获取一个测试 ID
    backend = MemoryBackend(memory_dir, use_sqlite=True)
    memories = backend.get_all_active_memories('fact')
    if not memories:
        print("❌ 没有可用的记忆进行测试")
        return
    
    test_id = memories[0]['id']
    
    # 测试 SQLite
    print("\n1. SQLite 后端:")
    backend_sqlite = MemoryBackend(memory_dir, use_sqlite=True)
    start = time.time()
    for i in range(iterations):
        backend_sqlite.update_access_stats(test_id, 'retrieval')
    sqlite_time = time.time() - start
    print(f"   总耗时: {sqlite_time:.3f}s")
    print(f"   平均: {sqlite_time/iterations*1000:.2f}ms/次")
    
    print(f"\n✅ SQLite 性能: {sqlite_time/iterations*1000:.2f}ms/次")

def benchmark_entity_search(memory_dir: Path, iterations: int = 50):
    """测试实体搜索性能"""
    print(f"\n📊 实体搜索性能测试 ({iterations} 次)")
    print("=" * 60)
    
    test_entities = ['[用户]', '用户', '记忆系统']
    
    # 测试 SQLite
    print("\n1. SQLite 后端:")
    backend_sqlite = MemoryBackend(memory_dir, use_sqlite=True)
    start = time.time()
    for i in range(iterations):
        results = backend_sqlite.search_by_entities(test_entities, limit=10)
    sqlite_time = time.time() - start
    print(f"   总耗时: {sqlite_time:.3f}s")
    print(f"   平均: {sqlite_time/iterations*1000:.2f}ms/次")
    print(f"   结果数: {len(results)}")
    
    print(f"\n✅ SQLite 性能: {sqlite_time/iterations*1000:.2f}ms/次")

def benchmark_get_all(memory_dir: Path, iterations: int = 20):
    """测试获取所有记忆性能"""
    print(f"\n📊 获取所有记忆性能测试 ({iterations} 次)")
    print("=" * 60)
    
    # 测试 JSONL
    print("\n1. JSONL 后端:")
    backend_jsonl = MemoryBackend(memory_dir, use_sqlite=False)
    start = time.time()
    for i in range(iterations):
        results = backend_jsonl.get_all_active_memories()
    jsonl_time = time.time() - start
    print(f"   总耗时: {jsonl_time:.3f}s")
    print(f"   平均: {jsonl_time/iterations*1000:.2f}ms/次")
    print(f"   记忆数: {len(results)}")
    
    # 测试 SQLite
    print("\n2. SQLite 后端:")
    backend_sqlite = MemoryBackend(memory_dir, use_sqlite=True)
    start = time.time()
    for i in range(iterations):
        results = backend_sqlite.get_all_active_memories()
    sqlite_time = time.time() - start
    print(f"   总耗时: {sqlite_time:.3f}s")
    print(f"   平均: {sqlite_time/iterations*1000:.2f}ms/次")
    print(f"   记忆数: {len(results)}")
    
    # 对比
    speedup = jsonl_time / sqlite_time
    print(f"\n✅ SQLite 比 JSONL 快 {speedup:.1f}x")

def run_all_benchmarks(memory_dir: Path):
    """运行所有性能测试"""
    print("🚀 Memory System v1.2.4 性能对比测试")
    print("=" * 60)
    
    benchmark_access_update(memory_dir, iterations=100)
    benchmark_entity_search(memory_dir, iterations=50)
    benchmark_get_all(memory_dir, iterations=20)
    
    print("\n" + "=" * 60)
    print("✅ 所有测试完成！")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python benchmark.py <memory_dir>")
        sys.exit(1)
    
    memory_dir = Path(sys.argv[1])
    run_all_benchmarks(memory_dir)
