#!/usr/bin/env python3
"""
Memory System v1.1.5 - 实体识别与隔离系统

核心功能：
1. 三层实体识别（硬编码 → 学习 → LLM）
2. 动态实体学习与模式归纳
3. 竞争性抑制（实体隔离）
4. 学习实体清理

设计原则：
- 类型保护：只归纳同类型后缀
- 断崖降权：相似但不同的实体 × 0.1
- 按需触发：只在必要时启用隔离
"""

import json
import re
import math
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
# 配置
# ============================================================

ENTITY_SYSTEM_CONFIG = {
    # 内置实体模式（硬编码）
    "builtin_patterns": [
        r"机器人[_\-]?\d+",
        r"项目[_\-]?[A-Z]",
        r"城市[_\-]?\d+",
        r"用户[_\-]?\d+",
        r"Agent[_\-]?\d+",
        r"协议[_\-]?[A-Z]",
    ],
    
    # 学习配置
    "learning": {
        "min_similar_for_pattern": 3,  # 至少 3 个相似实体才归纳模式
        "max_learned_entities": 1000,  # 最大学习实体数
        "max_learned_patterns": 100,   # 最大学习模式数
        "ttl_days": 365,               # 未使用实体的保留天数
    },
    
    # 隔离配置
    "isolation": {
        "inhibition_factor": 0.1,      # 抑制系数（断崖降权）
        "similarity_threshold": 0.5,   # 相似度阈值
        "min_common_prefix_ratio": 0.5,  # 最小共同前缀比例
    },
    
    # 访问加成配置（修复版）
    "access_boost": {
        "recent_days": 7,              # 只计算最近 N 天的访问
        "coefficient": 0.2,
        "max_boost": 0.5,
        "weights": {
            "retrieval": 1.0,
            "used_in_response": 2.0,
            "user_mentioned": 3.0
        }
    }
}

# ============================================================
# 学习实体存储
# ============================================================

def get_learned_entities_path(memory_dir):
    """获取学习实体文件路径"""
    return Path(memory_dir) / 'layer2' / 'learned_entities.json'

def load_learned_entities(memory_dir):
    """加载学习过的实体"""
    path = get_learned_entities_path(memory_dir)
    
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {
        "exact": [],           # 精确实体列表
        "patterns": [],        # 归纳的模式
        "access_stats": {},    # 实体访问统计
        "last_updated": None,
        "last_cleanup": None
    }

def save_learned_entities(memory_dir, learned):
    """保存学习实体"""
    path = get_learned_entities_path(memory_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    learned["last_updated"] = datetime.utcnow().isoformat() + 'Z'
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(learned, f, ensure_ascii=False, indent=2)

# ============================================================
# 三层实体识别
# ============================================================

def extract_entities_layer1(content):
    """Layer 1: 硬编码模式识别（0 Token）"""
    entities = []
    
    for pattern in ENTITY_SYSTEM_CONFIG["builtin_patterns"]:
        matches = re.findall(pattern, content, re.IGNORECASE)
        entities.extend(matches)
    
    return list(set(entities))

def extract_entities_layer2(content, memory_dir):
    """Layer 2: 学习过的实体识别（0 Token）"""
    entities = []
    learned = load_learned_entities(memory_dir)
    
    # 精确匹配
    for exact in learned.get("exact", []):
        if exact in content:
            entities.append(exact)
    
    # 模式匹配
    for pattern in learned.get("patterns", []):
        try:
            matches = re.findall(pattern, content, re.IGNORECASE)
            entities.extend(matches)
        except re.error:
            continue
    
    return list(set(entities))

def extract_entities_layer3_llm(content, llm_caller=None):
    """
    Layer 3: LLM 提取实体（有成本）
    
    Args:
        content: 要提取的内容
        llm_caller: LLM 调用函数，签名为 (prompt) -> (success, result, error)
    
    Returns:
        list: 提取的实体列表
    """
    if not llm_caller:
        return []
    
    prompt = f"""请从以下内容中提取所有命名实体（人名、地名、项目名、产品名、编号等）。

内容："{content}"

要求：
1. 只提取明确的实体名称
2. 保留完整的实体名（如"机器人_50"而不是"机器人"和"50"）
3. 返回 JSON 格式

输出格式：
{{"entities": ["实体1", "实体2", ...]}}"""

    success, result, error = llm_caller(prompt)
    
    if not success:
        return []
    
    try:
        # 尝试解析 JSON
        data = json.loads(result)
        return data.get("entities", [])
    except json.JSONDecodeError:
        # 尝试从文本中提取
        match = re.search(r'\[([^\]]+)\]', result)
        if match:
            items = match.group(1).split(',')
            return [item.strip().strip('"\'') for item in items if item.strip()]
        return []

def extract_entities(content, memory_dir=None, llm_caller=None, use_llm_fallback=True):
    """
    三层实体识别（主入口）
    
    Args:
        content: 要提取的内容
        memory_dir: 记忆目录（用于加载学习实体）
        llm_caller: LLM 调用函数
        use_llm_fallback: 是否启用 LLM 兜底
    
    Returns:
        tuple: (entities, source) - 实体列表和来源
    """
    # Layer 1: 硬编码模式
    entities = extract_entities_layer1(content)
    if entities:
        return entities, "builtin"
    
    # Layer 2: 学习过的实体
    if memory_dir:
        entities = extract_entities_layer2(content, memory_dir)
        if entities:
            return entities, "learned"
    
    # Layer 3: LLM 兜底
    if use_llm_fallback and llm_caller:
        entities = extract_entities_layer3_llm(content, llm_caller)
        if entities and memory_dir:
            # 学习新实体
            learn_new_entities(entities, memory_dir)
        return entities, "llm"
    
    return [], "none"

# ============================================================
# 动态实体学习
# ============================================================

def find_common_prefix(strings):
    """找出字符串列表的共同前缀"""
    if not strings:
        return ""
    
    prefix = strings[0]
    for s in strings[1:]:
        while not s.startswith(prefix) and prefix:
            prefix = prefix[:-1]
    
    return prefix

def get_suffix_type(suffix):
    """判断后缀类型"""
    if not suffix:
        return "empty"
    
    if suffix.isdigit():
        return "digit"
    
    if re.match(r'^[A-Z]$', suffix):
        return "single_upper"
    
    if re.match(r'^[A-Z]{2,3}$', suffix):
        return "multi_upper"
    
    if re.match(r'^[a-z]+$', suffix):
        return "lower"
    
    return "mixed"

def try_generalize_pattern(new_entity, existing_entities):
    """
    尝试从相似实体归纳模式
    
    类型保护：只有后缀类型一致才归纳
    """
    config = ENTITY_SYSTEM_CONFIG["learning"]
    
    # 找相似实体（共同前缀）
    similar = []
    for e in existing_entities:
        prefix = find_common_prefix([new_entity, e])
        # 共同前缀至少占一半
        if prefix and len(prefix) >= len(new_entity) * 0.5:
            similar.append(e)
    
    # 加上新实体
    all_similar = similar + [new_entity]
    
    # 至少需要 N 个相似实体才归纳
    if len(all_similar) < config["min_similar_for_pattern"]:
        return None
    
    # 找共同前缀
    prefix = find_common_prefix(all_similar)
    if not prefix:
        return None
    
    # 提取后缀
    suffixes = [e[len(prefix):] for e in all_similar]
    
    # 类型保护：检查后缀类型是否一致
    suffix_types = [get_suffix_type(s) for s in suffixes]
    
    if len(set(suffix_types)) != 1:
        # 后缀类型不一致，不归纳
        return None
    
    suffix_type = suffix_types[0]
    
    # 根据后缀类型生成模式
    escaped_prefix = re.escape(prefix)
    
    if suffix_type == "digit":
        return f"{escaped_prefix}\\d+"
    elif suffix_type == "single_upper":
        return f"{escaped_prefix}[A-Z]"
    elif suffix_type == "multi_upper":
        # 检测长度
        lengths = set(len(s) for s in suffixes)
        if len(lengths) == 1:
            length = list(lengths)[0]
            return f"{escaped_prefix}[A-Z]{{{length}}}"
        else:
            min_len = min(lengths)
            max_len = max(lengths)
            return f"{escaped_prefix}[A-Z]{{{min_len},{max_len}}}"
    elif suffix_type == "lower":
        return f"{escaped_prefix}[a-z]+"
    
    # 其他类型不归纳
    return None

def learn_new_entities(new_entities, memory_dir):
    """
    学习新实体
    
    1. 添加到精确匹配列表
    2. 尝试归纳模式
    """
    config = ENTITY_SYSTEM_CONFIG["learning"]
    learned = load_learned_entities(memory_dir)
    
    for entity in new_entities:
        # 避免重复
        if entity in learned["exact"]:
            continue
        
        # 检查是否超过上限
        if len(learned["exact"]) >= config["max_learned_entities"]:
            break
        
        # 添加到精确列表
        learned["exact"].append(entity)
        
        # 初始化访问统计
        learned["access_stats"][entity] = {
            "first_seen": datetime.utcnow().isoformat() + 'Z',
            "last_used": datetime.utcnow().isoformat() + 'Z',
            "use_count": 1
        }
        
        # 尝试归纳模式
        if len(learned["patterns"]) < config["max_learned_patterns"]:
            pattern = try_generalize_pattern(entity, learned["exact"])
            if pattern and pattern not in learned["patterns"]:
                learned["patterns"].append(pattern)
    
    save_learned_entities(memory_dir, learned)

def update_entity_access(entity, memory_dir):
    """更新实体访问统计"""
    learned = load_learned_entities(memory_dir)
    
    if entity in learned["access_stats"]:
        learned["access_stats"][entity]["last_used"] = datetime.utcnow().isoformat() + 'Z'
        learned["access_stats"][entity]["use_count"] = learned["access_stats"][entity].get("use_count", 0) + 1
    else:
        learned["access_stats"][entity] = {
            "first_seen": datetime.utcnow().isoformat() + 'Z',
            "last_used": datetime.utcnow().isoformat() + 'Z',
            "use_count": 1
        }
    
    save_learned_entities(memory_dir, learned)

# ============================================================
# 实体隔离（竞争性抑制）
# ============================================================

def calculate_entity_similarity(e1, e2):
    """
    计算两个实体的相似度
    
    Returns:
        float: 0-1 之间的相似度
    """
    if e1 == e2:
        return 1.0
    
    # 方法1：共同前缀比例
    prefix = find_common_prefix([e1, e2])
    if prefix:
        prefix_ratio = len(prefix) / max(len(e1), len(e2))
        if prefix_ratio >= 0.5:
            return prefix_ratio
    
    # 方法2：一个包含另一个
    if e1 in e2 or e2 in e1:
        shorter = min(len(e1), len(e2))
        longer = max(len(e1), len(e2))
        return shorter / longer
    
    # 方法3：编辑距离
    distance = levenshtein_distance(e1, e2)
    max_len = max(len(e1), len(e2))
    if max_len > 0:
        similarity = 1 - (distance / max_len)
        return max(0, similarity)
    
    return 0.0

def levenshtein_distance(s1, s2):
    """计算编辑距离"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]

def is_similar_entity(e1, e2, threshold=None):
    """判断两个实体是否相似（易混淆）"""
    if threshold is None:
        threshold = ENTITY_SYSTEM_CONFIG["isolation"]["similarity_threshold"]
    
    return calculate_entity_similarity(e1, e2) >= threshold

def find_similar_entity_groups(query_entities, all_entities):
    """
    找出相似实体组
    
    Returns:
        list of sets: 每个 set 包含一组相似的实体
    """
    groups = []
    
    for qe in query_entities:
        similar = {qe}
        for e in all_entities:
            if e != qe and is_similar_entity(qe, e):
                similar.add(e)
        
        if len(similar) > 1:
            groups.append(similar)
    
    return groups

def should_apply_entity_isolation(query_entities, candidates):
    """
    判断是否需要应用实体隔离
    
    按需触发：只在存在相似实体时才启用
    """
    if not query_entities:
        return False
    
    # 收集所有候选记忆中的实体
    all_candidate_entities = set()
    for mem in candidates:
        all_candidate_entities.update(mem.get('entities', []))
    
    # 检查是否存在相似实体
    for qe in query_entities:
        for ce in all_candidate_entities:
            if qe != ce and is_similar_entity(qe, ce):
                return True
    
    return False

def apply_entity_isolation(query, candidates, memory_dir=None, llm_caller=None):
    """
    应用实体隔离（竞争性抑制）
    
    Args:
        query: 查询字符串
        candidates: 候选记忆列表
        memory_dir: 记忆目录
        llm_caller: LLM 调用函数
    
    Returns:
        list: 处理后的候选记忆列表
    """
    config = ENTITY_SYSTEM_CONFIG["isolation"]
    
    # 1. 从查询中提取实体
    query_entities, source = extract_entities(
        query, 
        memory_dir=memory_dir, 
        llm_caller=llm_caller,
        use_llm_fallback=True
    )
    
    if not query_entities:
        return candidates  # 没有明确实体，跳过隔离
    
    # 2. 检查是否需要隔离
    if not should_apply_entity_isolation(query_entities, candidates):
        return candidates  # 没有相似实体，跳过隔离
    
    # 3. 收集所有候选实体
    all_candidate_entities = set()
    for mem in candidates:
        all_candidate_entities.update(mem.get('entities', []))
    
    # 4. 找出相似实体组
    similar_groups = find_similar_entity_groups(
        query_entities, 
        list(all_candidate_entities)
    )
    
    if not similar_groups:
        return candidates
    
    # 5. 应用竞争性抑制
    inhibition_factor = config["inhibition_factor"]
    
    for mem in candidates:
        mem_entities = set(mem.get('entities', []))
        
        # 精确匹配查询实体 → 保持权重
        if mem_entities & set(query_entities):
            continue
        
        # 检查是否包含相似但不同的实体
        for group in similar_groups:
            # 记忆包含这个组中的实体，但不是查询的目标实体
            if mem_entities & group and not (mem_entities & set(query_entities)):
                # 应用断崖降权
                original_score = mem.get('score', mem.get('final_score', 1.0))
                mem['score'] = original_score * inhibition_factor
                mem['isolation_applied'] = True
                mem['isolation_reason'] = f"竞争性抑制: 查询[{query_entities}] vs 记忆[{mem_entities & group}]"
                break
    
    return candidates

# ============================================================
# 访问加成修复（最近 N 天）
# ============================================================

def calculate_access_boost_v1_1_5(memory, access_log=None):
    """
    计算访问加成（v1.1.5 修复版）
    
    核心改进：
    1. 使用最近 N 天的访问次数，而非总天数
    2. 最近访问的记忆获得显著加成
    3. 老记忆被重新激活后能快速"复活"
    """
    config = ENTITY_SYSTEM_CONFIG["access_boost"]
    recent_days = config["recent_days"]
    weights = config["weights"]
    
    # 计算总加权访问次数
    total_weighted = (
        memory.get('retrieval_count', 0) * weights['retrieval'] +
        memory.get('used_in_response_count', 0) * weights['used_in_response'] +
        memory.get('user_mentioned_count', 0) * weights['user_mentioned']
    )
    
    if total_weighted <= 0:
        return 0.0
    
    # 检查最后访问时间
    last_accessed = memory.get('last_accessed')
    
    if not last_accessed:
        # 没有访问记录，返回最小加成
        return 0.0
    
    try:
        last_access_time = datetime.fromisoformat(last_accessed.replace('Z', '+00:00'))
        days_since_access = max(0, (datetime.utcnow() - last_access_time.replace(tzinfo=None)).days)
    except:
        return 0.0
    
    # 核心逻辑：根据最后访问时间计算有效访问次数
    if days_since_access <= recent_days:
        # 最近访问过 → 给予高权重
        # 越近访问，权重越高
        recency_factor = 1.0 - (days_since_access / recent_days) * 0.5  # 0.5 ~ 1.0
        effective_count = total_weighted * recency_factor
        
        # 额外加成：非常近期的访问（3天内）
        if days_since_access <= 3:
            effective_count *= 1.5
    else:
        # 很久没访问 → 大幅降低
        # 衰减因子：每超过 recent_days 一天，衰减 10%
        decay = 0.9 ** (days_since_access - recent_days)
        effective_count = total_weighted * decay * 0.1
    
    # 计算加成
    # 公式：ln(count + 1) * (count / recent_days) * coefficient
    boost = math.log(effective_count + 1) * (effective_count / recent_days) * config["coefficient"]
    
    # 限制最大加成
    boost = min(boost, config["max_boost"])
    
    return boost

# ============================================================
# 学习实体清理
# ============================================================

def cleanup_learned_entities(memory_dir, force=False):
    """
    清理废弃的学习实体
    
    在 Phase 5 执行，清理一年未使用的实体
    """
    config = ENTITY_SYSTEM_CONFIG["learning"]
    ttl_days = config["ttl_days"]
    
    learned = load_learned_entities(memory_dir)
    cutoff = datetime.utcnow() - timedelta(days=ttl_days)
    
    # 统计
    original_exact_count = len(learned.get("exact", []))
    original_pattern_count = len(learned.get("patterns", []))
    
    # 清理精确实体
    valid_exact = []
    for entity in learned.get("exact", []):
        stats = learned.get("access_stats", {}).get(entity, {})
        last_used = stats.get("last_used")
        
        if last_used:
            try:
                last_used_time = datetime.fromisoformat(last_used.replace('Z', '+00:00'))
                if last_used_time.replace(tzinfo=None) > cutoff:
                    valid_exact.append(entity)
                    continue
            except:
                pass
        
        # 没有访问记录或已过期，但如果是最近添加的保留
        first_seen = stats.get("first_seen")
        if first_seen:
            try:
                first_seen_time = datetime.fromisoformat(first_seen.replace('Z', '+00:00'))
                if first_seen_time.replace(tzinfo=None) > cutoff:
                    valid_exact.append(entity)
                    continue
            except:
                pass
    
    learned["exact"] = valid_exact
    
    # 清理模式（更保守：只清理完全没命中过的）
    valid_patterns = []
    for pattern in learned.get("patterns", []):
        stats = learned.get("access_stats", {}).get(pattern, {})
        hit_count = stats.get("use_count", 0)
        
        if hit_count > 0:
            valid_patterns.append(pattern)
    
    learned["patterns"] = valid_patterns
    
    # 清理访问统计中的孤儿记录
    valid_entities = set(learned["exact"] + learned["patterns"])
    learned["access_stats"] = {
        k: v for k, v in learned.get("access_stats", {}).items()
        if k in valid_entities
    }
    
    learned["last_cleanup"] = datetime.utcnow().isoformat() + 'Z'
    
    save_learned_entities(memory_dir, learned)
    
    # 返回清理统计
    return {
        "exact_removed": original_exact_count - len(learned["exact"]),
        "patterns_removed": original_pattern_count - len(learned["patterns"]),
        "exact_remaining": len(learned["exact"]),
        "patterns_remaining": len(learned["patterns"])
    }

# ============================================================
# 导出函数
# ============================================================

__all__ = [
    # 实体识别
    'extract_entities',
    'extract_entities_layer1',
    'extract_entities_layer2',
    'extract_entities_layer3_llm',
    
    # 实体学习
    'learn_new_entities',
    'update_entity_access',
    'try_generalize_pattern',
    
    # 实体隔离
    'apply_entity_isolation',
    'should_apply_entity_isolation',
    'find_similar_entity_groups',
    'is_similar_entity',
    'calculate_entity_similarity',
    
    # 访问加成
    'calculate_access_boost_v1_1_5',
    
    # 清理
    'cleanup_learned_entities',
    
    # 存储
    'load_learned_entities',
    'save_learned_entities',
    
    # 配置
    'ENTITY_SYSTEM_CONFIG',
]
