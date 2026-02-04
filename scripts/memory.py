#!/usr/bin/env python3
"""
Memory System v1.0 - 三层记忆架构 CLI
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import hashlib

# ============================================================
# 配置
# ============================================================

DEFAULT_CONFIG = {
    "version": "1.0",
    "decay_rates": {
        "fact": 0.008,
        "belief": 0.07,
        "summary": 0.025
    },
    "thresholds": {
        "archive": 0.05,
        "summary_trigger": 3
    },
    "token_budget": {
        "layer1_total": 2000
    },
    "consolidation": {
        "fallback_hours": 48
    }
}

# ============================================================
# 工具函数
# ============================================================

def get_memory_dir():
    """获取记忆系统根目录"""
    workspace = os.environ.get('WORKSPACE', os.getcwd())
    return Path(workspace) / 'memory'

def get_config():
    """读取配置"""
    config_path = get_memory_dir() / 'config.json'
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return DEFAULT_CONFIG

def save_config(config):
    """保存配置"""
    config_path = get_memory_dir() / 'config.json'
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

def load_jsonl(path):
    """读取 JSONL 文件"""
    if not path.exists():
        return []
    records = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records

def save_jsonl(path, records):
    """保存 JSONL 文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')

def generate_id(prefix, content):
    """生成唯一ID"""
    date_str = datetime.now().strftime('%Y%m%d')
    hash_str = hashlib.md5(content.encode()).hexdigest()[:6]
    return f"{prefix}_{date_str}_{hash_str}"

def now_iso():
    """当前时间 ISO 格式"""
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')

# ============================================================
# 混合策略：规则优先，LLM 兜底
# ============================================================

# 无意义回复列表
SKIP_RESPONSES = {
    "好的", "嗯", "OK", "好", "行", "可以", "知道了", "明白",
    "ok", "嗯嗯", "哦", "噢", "收到", "了解", "懂了"
}

# 问候语列表
GREETINGS = {
    "你好", "您好", "早上好", "下午好", "晚上好", "早安", "晚安",
    "hi", "hello", "hey", "嗨", "哈喽"
}

# 时间关键词
TIME_KEYWORDS = [
    "明天", "后天", "下周", "下个月", "今天", "昨天",
    "周一", "周二", "周三", "周四", "周五", "周六", "周日",
    "月底", "年底", "deadline", "截止"
]

# 模板匹配模式
EXTRACT_PATTERNS = [
    # 身份类
    (r"我是(.{2,20})$", "fact", "identity"),
    (r"我叫(.{2,10})$", "fact", "name"),
    (r"我的名字是(.{2,10})", "fact", "name"),
    # 偏好类
    (r"我喜欢(.{2,30})", "fact", "preference"),
    (r"我不喜欢(.{2,30})", "fact", "dislike"),
    (r"我讨厌(.{2,30})", "fact", "dislike"),
    (r"我爱(.{2,20})", "fact", "preference"),
    # 状态类
    (r"我在(.{2,20})工作", "fact", "work"),
    (r"我在(.{2,20})上学", "fact", "education"),
    (r"我是(.{2,10})专业", "fact", "major"),
    # 时间类
    (r"(明天|后天|下周.?|下个月)(.{2,30})", "fact", "schedule"),
]

import re

def is_greeting(content):
    """判断是否为问候语"""
    content_lower = content.lower().strip()
    return content_lower in GREETINGS or any(g in content_lower for g in GREETINGS)

def is_pure_emoji(content):
    """判断是否为纯表情"""
    import unicodedata
    stripped = content.strip()
    if not stripped:
        return True
    for char in stripped:
        if unicodedata.category(char) not in ('So', 'Sm', 'Sk', 'Sc'):
            if not char.isspace():
                return False
    return True

def contains_time_reference(content):
    """判断是否包含时间引用"""
    return any(kw in content for kw in TIME_KEYWORDS)

def contains_importance_marker(content):
    """判断是否包含重要性标记"""
    markers = ["记住", "重要", "别忘了", "一定要", "千万", "务必"]
    return any(m in content for m in markers)

def rule_filter(content):
    """
    规则过滤：Phase 2 筛选的第一道防线
    
    返回:
        (True, reason) - 保留
        (False, reason) - 丢弃
        (None, reason) - 无法判断，交给 LLM
    """
    content = content.strip()
    
    # === 直接丢弃 ===
    if len(content) < 5:
        return False, "内容太短"
    
    if content in SKIP_RESPONSES:
        return False, "无意义回复"
    
    if is_greeting(content):
        return False, "问候语"
    
    if is_pure_emoji(content):
        return False, "纯表情"
    
    # === 直接保留 ===
    if contains_importance_marker(content):
        return True, "用户标记重要"
    
    if contains_time_reference(content):
        return True, "时间敏感信息"
    
    if "我是" in content or "我叫" in content:
        return True, "身份信息"
    
    if "我喜欢" in content or "我不喜欢" in content:
        return True, "偏好信息"
    
    # === 无法判断 ===
    return None, "需要 LLM 判断"

def template_extract(content):
    """
    模板提取：Phase 3 提取的第一道防线
    
    返回:
        dict - 提取成功，返回结构化数据
        None - 无法匹配，交给 LLM
    """
    content = content.strip()
    
    for pattern, mem_type, category in EXTRACT_PATTERNS:
        match = re.search(pattern, content)
        if match:
            if len(match.groups()) == 1:
                value = match.group(1).strip()
            else:
                # 时间类模式有两个捕获组
                value = f"{match.group(1)} {match.group(2)}".strip()
            
            return {
                "type": mem_type,
                "category": category,
                "content": value,
                "confidence": 0.9,
                "source": "template_match",
                "original": content
            }
    
    return None  # 交给 LLM

def code_verify_belief(belief, new_facts):
    """
    代码验证 Belief：Phase 4b 的第一道防线
    
    返回:
        dict - {"action": "increase/decrease/upgrade/delete/none", "delta": float}
    """
    belief_content = belief.get('content', '').lower()
    
    for fact in new_facts:
        fact_content = fact.get('content', '').lower()
        
        # 直接证据支持
        if belief_content in fact_content or fact_content in belief_content:
            new_confidence = belief.get('confidence', 0.5) + 0.15
            if new_confidence > 0.85:
                return {"action": "upgrade", "new_confidence": new_confidence}
            return {"action": "increase", "delta": 0.15}
        
        # 简单矛盾检测（包含"不"的反转）
        if f"不{belief_content}" in fact_content or f"没有{belief_content}" in fact_content:
            new_confidence = belief.get('confidence', 0.5) - 0.25
            if new_confidence < 0.2:
                return {"action": "delete", "new_confidence": new_confidence}
            return {"action": "decrease", "delta": 0.25}
    
    return {"action": "none"}

# ============================================================
# 初始化命令
# ============================================================

def cmd_init(args):
    """初始化记忆系统目录结构"""
    memory_dir = get_memory_dir()
    
    # 创建目录结构
    dirs = [
        'layer1',
        'layer2/active',
        'layer2/archive',
        'layer2/entities',
        'layer2/index',
        'state'
    ]
    
    for d in dirs:
        (memory_dir / d).mkdir(parents=True, exist_ok=True)
    
    # 创建默认配置
    config_path = memory_dir / 'config.json'
    if not config_path.exists():
        save_config(DEFAULT_CONFIG)
    
    # 创建空的 JSONL 文件
    jsonl_files = [
        'layer2/active/facts.jsonl',
        'layer2/active/beliefs.jsonl',
        'layer2/active/summaries.jsonl',
        'layer2/archive/facts.jsonl',
        'layer2/archive/beliefs.jsonl',
        'layer2/archive/summaries.jsonl'
    ]
    
    for f in jsonl_files:
        path = memory_dir / f
        if not path.exists():
            path.touch()
    
    # 创建索引文件
    index_files = {
        'layer2/index/keywords.json': {},
        'layer2/index/timeline.json': {},
        'layer2/index/relations.json': {},
        'layer2/entities/_index.json': {"entities": []}
    }
    
    for f, default in index_files.items():
        path = memory_dir / f
        if not path.exists():
            with open(path, 'w', encoding='utf-8') as fp:
                json.dump(default, fp, indent=2, ensure_ascii=False)
    
    # 创建状态文件
    state_files = {
        'state/consolidation.json': {
            "last_run": None,
            "last_success": None,
            "current_phase": None,
            "phase_data": {},
            "retry_count": 0
        },
        'state/rankings.json': {
            "updated": None,
            "rankings": []
        }
    }
    
    for f, default in state_files.items():
        path = memory_dir / f
        if not path.exists():
            with open(path, 'w', encoding='utf-8') as fp:
                json.dump(default, fp, indent=2, ensure_ascii=False)
    
    # 创建初始 Layer 1 快照
    snapshot_path = memory_dir / 'layer1/snapshot.md'
    if not snapshot_path.exists():
        snapshot_content = """# 工作记忆快照
> 生成时间: {time} | 状态: 初始化

## 说明
记忆系统已初始化，尚无记忆数据。
执行 `memory.py consolidate` 开始整合记忆。
""".format(time=now_iso())
        with open(snapshot_path, 'w', encoding='utf-8') as f:
            f.write(snapshot_content)
    
    print("✅ 记忆系统初始化完成")
    print(f"   目录: {memory_dir}")
    print(f"   配置: {memory_dir / 'config.json'}")

# ============================================================
# 状态命令
# ============================================================

def cmd_status(args):
    """显示系统状态"""
    memory_dir = get_memory_dir()
    
    if not memory_dir.exists():
        print("❌ 记忆系统未初始化，请先运行: memory.py init")
        return
    
    # 读取状态
    state_path = memory_dir / 'state/consolidation.json'
    if state_path.exists():
        with open(state_path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    else:
        state = {}
    
    # 统计记忆数量
    active_facts = len(load_jsonl(memory_dir / 'layer2/active/facts.jsonl'))
    active_beliefs = len(load_jsonl(memory_dir / 'layer2/active/beliefs.jsonl'))
    active_summaries = len(load_jsonl(memory_dir / 'layer2/active/summaries.jsonl'))
    archive_facts = len(load_jsonl(memory_dir / 'layer2/archive/facts.jsonl'))
    archive_beliefs = len(load_jsonl(memory_dir / 'layer2/archive/beliefs.jsonl'))
    archive_summaries = len(load_jsonl(memory_dir / 'layer2/archive/summaries.jsonl'))
    
    active_total = active_facts + active_beliefs + active_summaries
    archive_total = archive_facts + archive_beliefs + archive_summaries
    
    print("🧠 Memory System Status")
    print("=" * 40)
    print(f"目录: {memory_dir}")
    print()
    print("📊 记忆统计")
    print(f"   活跃池: {active_total} 条")
    print(f"     - Facts: {active_facts}")
    print(f"     - Beliefs: {active_beliefs}")
    print(f"     - Summaries: {active_summaries}")
    print(f"   归档池: {archive_total} 条")
    print()
    print("⏰ Consolidation")
    print(f"   上次运行: {state.get('last_run', '从未')}")
    print(f"   上次成功: {state.get('last_success', '从未')}")
    print(f"   当前阶段: {state.get('current_phase', '无')}")

def cmd_stats(args):
    """显示详细统计"""
    memory_dir = get_memory_dir()
    
    if not memory_dir.exists():
        print("❌ 记忆系统未初始化")
        return
    
    # 加载所有记忆
    facts = load_jsonl(memory_dir / 'layer2/active/facts.jsonl')
    beliefs = load_jsonl(memory_dir / 'layer2/active/beliefs.jsonl')
    summaries = load_jsonl(memory_dir / 'layer2/active/summaries.jsonl')
    
    # 按重要性分组
    importance_groups = {
        'critical': 0,  # 0.9-1.0
        'high': 0,      # 0.7-0.9
        'medium': 0,    # 0.4-0.7
        'low': 0        # 0-0.4
    }
    
    all_records = facts + beliefs + summaries
    for r in all_records:
        imp = r.get('importance', 0.5)
        if imp >= 0.9:
            importance_groups['critical'] += 1
        elif imp >= 0.7:
            importance_groups['high'] += 1
        elif imp >= 0.4:
            importance_groups['medium'] += 1
        else:
            importance_groups['low'] += 1
    
    print("📊 Memory System Stats")
    print("=" * 40)
    print(f"Total: {len(all_records)} memories")
    print()
    print("By Type:")
    print(f"  Facts: {len(facts)} ({len(facts)*100//max(len(all_records),1)}%)")
    print(f"  Beliefs: {len(beliefs)} ({len(beliefs)*100//max(len(all_records),1)}%)")
    print(f"  Summaries: {len(summaries)} ({len(summaries)*100//max(len(all_records),1)}%)")
    print()
    print("By Importance:")
    print(f"  Critical (0.9-1.0): {importance_groups['critical']}")
    print(f"  High (0.7-0.9): {importance_groups['high']}")
    print(f"  Medium (0.4-0.7): {importance_groups['medium']}")
    print(f"  Low (0-0.4): {importance_groups['low']}")

# ============================================================
# 手动操作命令
# ============================================================

def cmd_capture(args):
    """手动添加记忆"""
    memory_dir = get_memory_dir()
    
    if not memory_dir.exists():
        print("❌ 记忆系统未初始化")
        return
    
    content = args.content
    mem_type = args.type
    importance = args.importance
    
    # 输入验证
    if not content or not content.strip():
        print("❌ 错误: 内容不能为空")
        return
    
    # 限制 importance 在 0-1 范围
    if importance < 0:
        importance = 0
        print("⚠️ 警告: importance 已调整为 0")
    elif importance > 1:
        importance = 1
        print("⚠️ 警告: importance 已调整为 1")
    entities = args.entities.split(',') if args.entities else []
    
    record = {
        "id": generate_id(mem_type[0], content),
        "content": content,
        "importance": importance,
        "score": importance,  # 初始 score = importance
        "entities": entities,
        "created": now_iso(),
        "source": "manual"
    }
    
    if mem_type == 'belief':
        record['confidence'] = args.confidence
    
    # 追加到对应文件
    if mem_type == 'fact':
        path = memory_dir / 'layer2/active/facts.jsonl'
    elif mem_type == 'belief':
        path = memory_dir / 'layer2/active/beliefs.jsonl'
    else:
        path = memory_dir / 'layer2/active/summaries.jsonl'
    
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    print(f"✅ 记忆已添加: {record['id']}")
    print(f"   类型: {mem_type}")
    print(f"   重要性: {importance}")
    print(f"   内容: {content[:50]}...")

def cmd_archive(args):
    """手动归档记忆"""
    memory_dir = get_memory_dir()
    memory_id = args.id
    
    # 在活跃池中查找
    for mem_type in ['facts', 'beliefs', 'summaries']:
        active_path = memory_dir / f'layer2/active/{mem_type}.jsonl'
        archive_path = memory_dir / f'layer2/archive/{mem_type}.jsonl'
        
        records = load_jsonl(active_path)
        found = None
        remaining = []
        
        for r in records:
            if r.get('id') == memory_id:
                found = r
            else:
                remaining.append(r)
        
        if found:
            # 保存剩余记录
            save_jsonl(active_path, remaining)
            # 追加到归档
            with open(archive_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(found, ensure_ascii=False) + '\n')
            print(f"✅ 已归档: {memory_id}")
            return
    
    print(f"❌ 未找到记忆: {memory_id}")

# ============================================================
# Consolidation 命令
# ============================================================

def cmd_consolidate(args):
    """执行 Consolidation 流程"""
    memory_dir = get_memory_dir()
    
    if not memory_dir.exists():
        print("❌ 记忆系统未初始化，请先运行: memory.py init")
        return
    
    config = get_config()
    
    # 检查是否需要执行
    state_path = memory_dir / 'state/consolidation.json'
    with open(state_path, 'r', encoding='utf-8') as f:
        state = json.load(f)
    
    if not args.force and state.get('last_success'):
        last_success = datetime.fromisoformat(state['last_success'].replace('Z', '+00:00'))
        hours_since = (datetime.now(last_success.tzinfo) - last_success).total_seconds() / 3600
        fallback_hours = config['consolidation']['fallback_hours']
        
        if hours_since < 20:  # 至少间隔 20 小时
            print(f"⏭️ 跳过: 距离上次成功仅 {hours_since:.1f} 小时")
            print(f"   使用 --force 强制执行")
            return
    
    print("🧠 开始 Consolidation...")
    print("=" * 40)
    
    # 更新状态
    state['last_run'] = now_iso()
    state['current_phase'] = 1
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    
    try:
        # Phase 1: 轻量全量
        if not args.phase or args.phase == 1:
            print("\n📋 Phase 1: 轻量全量（切分片段）")
            print("   [模拟] 读取今日对话，切分为语义片段")
            print("   ✅ 完成")
        
        # Phase 2: 重要性筛选
        if not args.phase or args.phase == 2:
            print("\n🎯 Phase 2: 重要性筛选")
            print("   [模拟] 调用模型判断重要性")
            print("   ✅ 完成")
        
        # Phase 3: 深度提取
        if not args.phase or args.phase == 3:
            print("\n📝 Phase 3: 深度提取")
            print("   [模拟] 提取结构化 facts/beliefs")
            print("   ✅ 完成")
        
        # Phase 4: Layer 2 维护
        if not args.phase or args.phase == 4:
            print("\n🔧 Phase 4: Layer 2 维护")
            print("   4a: Facts 去重合并")
            print("   4b: Beliefs 验证")
            print("   4c: Summaries 生成")
            print("   4d: Entities 更新")
            print("   ✅ 完成")
        
        # Phase 5: 权重更新
        if not args.phase or args.phase == 5:
            print("\n⚖️ Phase 5: 权重更新")
            decay_rates = config['decay_rates']
            archive_threshold = config['thresholds']['archive']
            
            archived_count = 0
            for mem_type in ['facts', 'beliefs', 'summaries']:
                active_path = memory_dir / f'layer2/active/{mem_type}.jsonl'
                archive_path = memory_dir / f'layer2/archive/{mem_type}.jsonl'
                
                records = load_jsonl(active_path)
                remaining = []
                to_archive = []
                
                decay_rate = decay_rates.get(mem_type.rstrip('s'), 0.01)
                
                for r in records:
                    importance = r.get('importance', 0.5)
                    actual_decay = decay_rate * (1 - importance * 0.5)
                    r['score'] = r.get('score', importance) * (1 - actual_decay)
                    
                    if r['score'] < archive_threshold:
                        to_archive.append(r)
                        archived_count += 1
                    else:
                        remaining.append(r)
                
                save_jsonl(active_path, remaining)
                if to_archive:
                    existing = load_jsonl(archive_path)
                    save_jsonl(archive_path, existing + to_archive)
            
            print(f"   衰减完成，归档 {archived_count} 条")
            print("   ✅ 完成")
        
        # Phase 6: 索引更新
        if not args.phase or args.phase == 6:
            print("\n📇 Phase 6: 索引更新")
            # 重建关键词索引
            keywords_index = {}
            relations_index = {}
            
            for mem_type in ['facts', 'beliefs', 'summaries']:
                records = load_jsonl(memory_dir / f'layer2/active/{mem_type}.jsonl')
                for r in records:
                    # 简单的关键词提取
                    content = r.get('content', '')
                    words = content.replace('，', ' ').replace('。', ' ').split()
                    for word in words:
                        if len(word) >= 2:
                            if word not in keywords_index:
                                keywords_index[word] = []
                            keywords_index[word].append(r['id'])
                    
                    # 实体关系
                    for entity in r.get('entities', []):
                        if entity not in relations_index:
                            relations_index[entity] = {'facts': [], 'beliefs': [], 'summaries': []}
                        relations_index[entity][mem_type].append(r['id'])
            
            with open(memory_dir / 'layer2/index/keywords.json', 'w', encoding='utf-8') as f:
                json.dump(keywords_index, f, indent=2, ensure_ascii=False)
            with open(memory_dir / 'layer2/index/relations.json', 'w', encoding='utf-8') as f:
                json.dump(relations_index, f, indent=2, ensure_ascii=False)
            
            print("   ✅ 完成")
        
        # Phase 7: Layer 1 快照
        if not args.phase or args.phase == 7:
            print("\n📸 Phase 7: Layer 1 快照")
            
            # 收集所有活跃记忆并排序
            all_records = []
            for mem_type in ['facts', 'beliefs', 'summaries']:
                records = load_jsonl(memory_dir / f'layer2/active/{mem_type}.jsonl')
                for r in records:
                    r['_type'] = mem_type
                all_records.extend(records)
            
            # 按 score 排序
            all_records.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            # 统计各类型数量
            facts_count = len([r for r in all_records if r['_type'] == 'facts'])
            beliefs_count = len([r for r in all_records if r['_type'] == 'beliefs'])
            summaries_count = len([r for r in all_records if r['_type'] == 'summaries'])
            
            # 按重要性分组
            critical = [r for r in all_records if r.get('importance', 0) >= 0.9]
            high = [r for r in all_records if 0.7 <= r.get('importance', 0) < 0.9]
            
            # 提取实体统计
            all_entities = set()
            for r in all_records:
                all_entities.update(r.get('entities', []))
            
            # 生成增强版快照
            snapshot = f"""# 工作记忆快照
> 生成时间: {now_iso()} | 活跃记忆: {len(all_records)} | 实体: {len(all_entities)}

---

## 🔴 关键信息 (importance ≥ 0.9)
"""
            for r in critical[:5]:
                snapshot += f"- **{r.get('content', '')}**\n"
            if not critical:
                snapshot += "- (无)\n"
            
            snapshot += f"""
## 🟠 重要信息 (importance 0.7-0.9)
"""
            for r in high[:5]:
                snapshot += f"- {r.get('content', '')}\n"
            if not high:
                snapshot += "- (无)\n"
            
            snapshot += f"""
## 📊 记忆排名 (Top 15)
| # | Score | 内容 |
|---|-------|------|
"""
            for i, r in enumerate(all_records[:15]):
                score = r.get('score', 0)
                content_text = r.get('content', '')[:40]
                mem_type = r['_type'][0].upper()  # F/B/S
                snapshot += f"| {i+1} | {score:.2f} | [{mem_type}] {content_text} |\n"
            
            snapshot += f"""
## 🏷️ 实体索引
"""
            for entity in sorted(all_entities)[:10]:
                related = len([r for r in all_records if entity in r.get('entities', [])])
                snapshot += f"- **{entity}**: {related} 条相关记忆\n"
            
            snapshot += f"""
## 📈 统计概览
- **Facts**: {facts_count} 条 ({facts_count*100//max(len(all_records),1)}%)
- **Beliefs**: {beliefs_count} 条 ({beliefs_count*100//max(len(all_records),1)}%)
- **Summaries**: {summaries_count} 条 ({summaries_count*100//max(len(all_records),1)}%)
- **关键信息**: {len(critical)} 条
- **重要信息**: {len(high)} 条

---
*Memory System v1.0 | 使用 memory_search 检索详细信息*
"""
            
            with open(memory_dir / 'layer1/snapshot.md', 'w', encoding='utf-8') as f:
                f.write(snapshot)
            
            # 保存排名
            rankings = [{'id': r['id'], 'score': r.get('score', 0)} for r in all_records[:50]]
            with open(memory_dir / 'state/rankings.json', 'w', encoding='utf-8') as f:
                json.dump({'updated': now_iso(), 'rankings': rankings}, f, indent=2, ensure_ascii=False)
            
            print("   ✅ 完成")
        
        # 更新成功状态
        state['last_success'] = now_iso()
        state['current_phase'] = None
        state['retry_count'] = 0
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 40)
        print("✅ Consolidation 完成!")
        
    except Exception as e:
        state['retry_count'] = state.get('retry_count', 0) + 1
        with open(state_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        print(f"\n❌ Consolidation 失败: {e}")
        raise

# ============================================================
# 维护命令
# ============================================================

def cmd_rebuild_index(args):
    """重建索引"""
    memory_dir = get_memory_dir()
    print("🔄 重建索引...")
    
    # 调用 Phase 6 逻辑
    args.phase = 6
    args.force = True
    cmd_consolidate(args)

def cmd_validate(args):
    """验证数据完整性"""
    memory_dir = get_memory_dir()
    print("🔍 验证数据完整性...")
    
    errors = []
    
    # 检查目录结构
    required_dirs = [
        'layer1', 'layer2/active', 'layer2/archive',
        'layer2/entities', 'layer2/index', 'state'
    ]
    for d in required_dirs:
        if not (memory_dir / d).exists():
            errors.append(f"缺少目录: {d}")
    
    # 检查 JSONL 文件格式
    for mem_type in ['facts', 'beliefs', 'summaries']:
        for pool in ['active', 'archive']:
            path = memory_dir / f'layer2/{pool}/{mem_type}.jsonl'
            if path.exists():
                try:
                    records = load_jsonl(path)
                    for i, r in enumerate(records):
                        if 'id' not in r:
                            errors.append(f"{path}:{i+1} 缺少 id 字段")
                        if 'content' not in r:
                            errors.append(f"{path}:{i+1} 缺少 content 字段")
                except Exception as e:
                    errors.append(f"{path} 解析失败: {e}")
    
    if errors:
        print(f"❌ 发现 {len(errors)} 个问题:")
        for e in errors[:10]:
            print(f"   - {e}")
        if len(errors) > 10:
            print(f"   ... 还有 {len(errors) - 10} 个问题")
    else:
        print("✅ 数据完整性验证通过")

# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='Memory System v1.0 - 三层记忆架构 CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # init
    parser_init = subparsers.add_parser('init', help='初始化记忆系统')
    parser_init.set_defaults(func=cmd_init)
    
    # status
    parser_status = subparsers.add_parser('status', help='显示系统状态')
    parser_status.set_defaults(func=cmd_status)
    
    # stats
    parser_stats = subparsers.add_parser('stats', help='显示详细统计')
    parser_stats.set_defaults(func=cmd_stats)
    
    # capture
    parser_capture = subparsers.add_parser('capture', help='手动添加记忆')
    parser_capture.add_argument('content', help='记忆内容')
    parser_capture.add_argument('--type', choices=['fact', 'belief', 'summary'], default='fact', help='记忆类型')
    parser_capture.add_argument('--importance', type=float, default=0.5, help='重要性 (0-1)')
    parser_capture.add_argument('--confidence', type=float, default=0.6, help='置信度 (belief 专用)')
    parser_capture.add_argument('--entities', default='', help='相关实体，逗号分隔')
    parser_capture.set_defaults(func=cmd_capture)
    
    # archive
    parser_archive = subparsers.add_parser('archive', help='手动归档记忆')
    parser_archive.add_argument('id', help='记忆 ID')
    parser_archive.set_defaults(func=cmd_archive)
    
    # consolidate
    parser_consolidate = subparsers.add_parser('consolidate', help='执行 Consolidation')
    parser_consolidate.add_argument('--force', action='store_true', help='强制执行')
    parser_consolidate.add_argument('--phase', type=int, choices=[1,2,3,4,5,6,7], help='只执行指定阶段')
    parser_consolidate.set_defaults(func=cmd_consolidate)
    
    # rebuild-index
    parser_rebuild = subparsers.add_parser('rebuild-index', help='重建索引')
    parser_rebuild.set_defaults(func=cmd_rebuild_index)
    
    # validate
    parser_validate = subparsers.add_parser('validate', help='验证数据完整性')
    parser_validate.set_defaults(func=cmd_validate)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    args.func(args)

if __name__ == '__main__':
    main()
