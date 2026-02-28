#!/usr/bin/env python3
"""
Memory System v1.1 - 访问日志管理命令
"""

import json
from pathlib import Path
from datetime import datetime
from v1_1_helpers import record_access, update_memory_access_stats

def cmd_record_access(args, memory_dir):
    """记录访问日志"""
    memory_id = args.id
    access_type = args.type
    query = args.query
    context = args.context
    
    # 记录访问日志
    record_access(memory_id, access_type, memory_dir, query, context)
    
    # 更新记忆的访问统计
    for mem_type in ['facts', 'beliefs', 'summaries']:
        active_path = memory_dir / f'layer2/active/{mem_type}.jsonl'
        
        if not active_path.exists():
            continue
        
        memories = []
        with open(active_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    memories.append(json.loads(line))
        
        updated = False
        for mem in memories:
            if mem.get('id') == memory_id:
                update_memory_access_stats(mem, access_type)
                updated = True
                break
        
        if updated:
            with open(active_path, 'w', encoding='utf-8') as f:
                for mem in memories:
                    f.write(json.dumps(mem, ensure_ascii=False) + '\n')
            print(f"✅ 访问记录已更新: {memory_id}")
            print(f"   类型: {access_type}")
            print(f"   访问次数: {mem.get('access_count', 0)}")
            print(f"   访问加成: {mem.get('access_boost', 0):.2f}")
            return
    
    print(f"❌ 未找到记忆: {memory_id}")

def cmd_view_access_log(args, memory_dir):
    """查看访问日志"""
    access_log_path = memory_dir / 'layer2/access_log.jsonl'
    
    if not access_log_path.exists():
        print("📋 访问日志为空")
        return
    
    logs = []
    with open(access_log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                logs.append(json.loads(line))
    
    # 按时间倒序
    logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    limit = args.limit if hasattr(args, 'limit') else 20
    
    print(f"📋 访问日志 (最近 {limit} 条)")
    print("=" * 60)
    
    for i, log in enumerate(logs[:limit]):
        timestamp = log.get('timestamp', '')
        memory_id = log.get('memory_id', '')
        access_type = log.get('access_type', '')
        query = log.get('query', '')
        
        print(f"{i+1}. [{timestamp}] {memory_id}")
        print(f"   类型: {access_type}")
        if query:
            print(f"   查询: {query[:50]}...")
        print()

def cmd_view_expired_log(args, memory_dir):
    """查看过期记忆日志"""
    expired_log_path = memory_dir / 'layer2/expired_log.jsonl'
    
    if not expired_log_path.exists():
        print("📋 过期日志为空")
        return
    
    logs = []
    with open(expired_log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                logs.append(json.loads(line))
    
    # 按过期时间倒序
    logs.sort(key=lambda x: x.get('expired_at', ''), reverse=True)
    
    limit = args.limit if hasattr(args, 'limit') else 20
    
    print(f"📋 过期记忆日志 (最近 {limit} 条)")
    print("=" * 60)
    
    for i, log in enumerate(logs[:limit]):
        expired_at = log.get('expired_at', '')
        memory_id = log.get('memory_id', '')
        content = log.get('content', '')
        
        print(f"{i+1}. [{expired_at}] {memory_id}")
        print(f"   内容: {content[:50]}...")
        print()
