#!/usr/bin/env python3
"""
Memory System v1.1 - 新增辅助函数
"""

import json
import math
import re
from datetime import datetime, timedelta

from v1_1_config import *


def now_iso():
    """当前时间 ISO 格式"""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================
# Phase 0: 清理过期记忆
# ============================================================


def phase0_expire_memories(memory_dir):
    """Phase 0: 清理过期记忆"""
    now = datetime.utcnow()
    expired_log_path = memory_dir / "layer2/expired_log.jsonl"

    total_expired = 0

    for mem_type in ["facts", "beliefs", "summaries"]:
        active_path = memory_dir / f"layer2/active/{mem_type}.jsonl"

        if not active_path.exists():
            continue

        memories = []
        with open(active_path, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    memories.append(json.loads(line))

        valid = []
        expired = []

        for mem in memories:
            expires_at = mem.get("expires_at")

            if expires_at:
                try:
                    expire_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                    if expire_time.replace(tzinfo=None) <= now:
                        expired.append(mem)
                        total_expired += 1
                    else:
                        valid.append(mem)
                except:
                    valid.append(mem)
            else:
                valid.append(mem)

        # 保存有效记忆
        with open(active_path, "w", encoding="utf-8") as f:
            for mem in valid:
                f.write(json.dumps(mem, ensure_ascii=False) + "\n")

        # 归档过期记忆
        if expired:
            with open(expired_log_path, "a", encoding="utf-8") as f:
                for mem in expired:
                    log_entry = {
                        "memory_id": mem["id"],
                        "content": mem.get("content", ""),
                        "created_at": mem.get("created", ""),
                        "expires_at": mem.get("expires_at", ""),
                        "expired_at": now_iso(),
                    }
                    f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    return total_expired


# ============================================================
# 第一级：强匹配池
# ============================================================


def check_tier1_patterns(content):
    """第一级：强匹配池（0 Token）"""
    patterns = FUNNEL_CONFIG["tier1_patterns"]

    # 检查永久记忆模式
    for pattern in patterns["permanent"]:
        if re.search(pattern, content):
            return {"type": "permanent", "expires_at": None, "is_permanent": True}

    # 检查立即任务
    for pattern in patterns["task_immediate"]:
        if re.search(pattern, content):
            expires_at = (datetime.utcnow() + timedelta(hours=12)).isoformat() + "Z"
            return {"type": "task", "expires_at": expires_at, "is_permanent": False}

    # 检查短期任务
    for pattern in patterns["task_short"]:
        if re.search(pattern, content):
            expires_at = (datetime.utcnow() + timedelta(days=2)).isoformat() + "Z"
            return {"type": "task", "expires_at": expires_at, "is_permanent": False}

    return None


# ============================================================
# 第二级：LLM 介入（模拟）
# ============================================================


def call_llm_time_sensor(content, importance):
    """
    第二级：LLM 介入（灰色地带）

    注意：这是简化版本，实际应调用 LLM API
    """
    # 简化版：基于关键词判断
    time_keywords = TIME_SENSITIVITY_CONFIG

    for category, config in time_keywords.items():
        if category == "specific_time":
            continue

        keywords = config.get("keywords", [])
        for kw in keywords:
            if kw in content:
                if "expires_hours" in config:
                    expires_at = (datetime.utcnow() + timedelta(hours=config["expires_hours"])).isoformat() + "Z"
                else:
                    expires_at = (datetime.utcnow() + timedelta(days=config["expires_days"])).isoformat() + "Z"

                return {"type": "task", "expires_at": expires_at, "is_permanent": False, "importance": importance}

    # 默认：永久记忆
    return {"type": "permanent", "expires_at": None, "is_permanent": True, "importance": importance}


# ============================================================
# 第三级：实体热度追踪
# ============================================================


def check_action_verbs(content):
    """检查内容是否包含动作词"""
    for verb in ACTION_VERBS:
        if verb in content:
            return True
    return False


def apply_tier3_entity_tracking(memories, active_entities=None):
    """
    第三级：实体热度追踪

    对于提到活跃实体但没有动作词的记忆，设置默认保质期
    """
    if active_entities is None:
        active_entities = set()

    for mem in memories:
        # 跳过已有过期时间的记忆
        if mem.get("expires_at") or mem.get("is_permanent"):
            continue

        entities = mem.get("entities", [])
        content = mem.get("content", "")

        # 检查是否提到活跃实体
        has_active_entity = any(e in active_entities for e in entities)
        has_action = check_action_verbs(content)

        if has_active_entity and not has_action:
            # 设置默认保质期
            ttl_days = FUNNEL_CONFIG["tier3_entity"]["default_ttl_days"]
            expires_at = (datetime.utcnow() + timedelta(days=ttl_days)).isoformat() + "Z"

            mem["expires_at"] = expires_at
            mem["is_permanent"] = False
            mem["tier3_tracked"] = True
            mem["reactivation_count"] = 0

    return memories


# ============================================================
# 访问日志系统
# ============================================================


def record_access(memory_id, access_type, memory_dir, query=None, context=None):
    """记录访问日志"""
    access_log_path = memory_dir / "layer2/access_log.jsonl"

    log_entry = {
        "memory_id": memory_id,
        "timestamp": now_iso(),
        "access_type": access_type,
        "query": query,
        "context": context,
    }

    with open(access_log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


def calculate_weighted_access_count(memory):
    """计算加权访问次数"""
    weights = ACCESS_BOOST_CONFIG["access_weights"]

    retrieval_count = memory.get("retrieval_count", 0)
    used_count = memory.get("used_in_response_count", 0)
    mentioned_count = memory.get("user_mentioned_count", 0)

    weighted = (
        retrieval_count * weights["retrieval"]
        + used_count * weights["used_in_response"]
        + mentioned_count * weights["user_mentioned"]
    )

    return weighted


def calculate_access_boost(memory):
    """
    计算访问频率加成

    v1.1.5 改进：使用"最近 N 天"替代"总天数"
    - 最近访问的记忆获得显著加成
    - 老记忆被重新激活后能快速"复活"
    """
    # 计算总加权访问次数
    total_weighted = calculate_weighted_access_count(memory)

    if total_weighted <= 0:
        return 0.0

    # v1.1.5: 使用最近 N 天逻辑
    recent_days = ACCESS_BOOST_CONFIG.get("recent_days", 7)

    # 检查最后访问时间
    last_accessed = memory.get("last_accessed")

    if not last_accessed:
        return 0.0

    try:
        last_access_time = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))
        days_since_access = max(0, (datetime.utcnow() - last_access_time.replace(tzinfo=None)).days)
    except:
        return 0.0

    # 核心逻辑：根据最后访问时间计算有效访问次数
    if days_since_access <= recent_days:
        # 最近访问过 → 给予高权重
        recency_factor = 1.0 - (days_since_access / recent_days) * 0.5  # 0.5 ~ 1.0
        effective_count = total_weighted * recency_factor

        # 额外加成：非常近期的访问（3天内）
        if days_since_access <= 3:
            effective_count *= 1.5
    else:
        # 很久没访问 → 大幅降低
        decay = 0.9 ** (days_since_access - recent_days)
        effective_count = total_weighted * decay * 0.1

    # 计算加成
    boost = math.log(effective_count + 1) * (effective_count / recent_days) * ACCESS_BOOST_CONFIG["coefficient"]

    # 限制最大加成
    boost = min(boost, ACCESS_BOOST_CONFIG["max_boost"])

    return boost


def update_memory_access_stats(memory, access_type):
    """更新记忆的访问统计"""
    # 更新总访问次数
    memory["access_count"] = memory.get("access_count", 0) + 1

    # 更新分类访问次数
    if access_type == "retrieval":
        memory["retrieval_count"] = memory.get("retrieval_count", 0) + 1
    elif access_type == "used_in_response":
        memory["used_in_response_count"] = memory.get("used_in_response_count", 0) + 1
    elif access_type == "user_mentioned":
        memory["user_mentioned_count"] = memory.get("user_mentioned_count", 0) + 1

    # 更新最后访问时间
    memory["last_accessed"] = now_iso()

    # 计算访问加成
    memory["access_boost"] = calculate_access_boost(memory)

    return memory


# ============================================================
# Phase 5: 排名（含访问加成）
# ============================================================


def phase5_rank_with_access_boost(memories):
    """Phase 5: 排名（含访问加成）"""
    for mem in memories:
        base_score = (
            mem.get("importance", 0.5) * mem.get("confidence", 1.0)
            if "confidence" in mem
            else mem.get("importance", 0.5)
        )
        access_boost = mem.get("access_boost", 0.0)

        final_score = base_score * (1 + access_boost)
        mem["final_score"] = final_score

    # 按 final_score 排序
    memories.sort(key=lambda x: x.get("final_score", 0), reverse=True)

    return memories


# ============================================================
# Phase 6: 衰减（含访问保护）
# ============================================================


def phase6_decay_with_access_protection(memories, config):
    """Phase 6: 衰减（含访问保护）"""
    now = datetime.utcnow()
    decay_rates = config["decay_rates"]
    protection = DECAY_WITH_ACCESS_CONFIG["access_protection"]

    for mem in memories:
        mem_type = "fact" if mem["id"].startswith("f_") else ("belief" if mem["id"].startswith("b_") else "summary")
        base_decay = decay_rates.get(mem_type, 0.01)

        # 检查最后访问时间
        last_accessed = mem.get("last_accessed")
        if last_accessed:
            try:
                last_access_time = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))
                days_since_access = (now - last_access_time.replace(tzinfo=None)).days
            except:
                days_since_access = 999
        else:
            days_since_access = 999

        # 应用访问保护
        if days_since_access <= 3:
            decay_factor = protection["within_3_days"]
        elif days_since_access <= 7:
            decay_factor = protection["within_7_days"]
        elif days_since_access <= 14:
            decay_factor = protection["within_14_days"]
        else:
            decay_factor = protection["beyond_14_days"]

        # 计算实际衰减
        importance = mem.get("importance", 0.5)
        actual_decay = base_decay * (1 - importance * 0.5) * decay_factor

        # 更新 score
        current_score = mem.get("final_score", mem.get("score", importance))
        mem["score"] = current_score * (1 - actual_decay)

    return memories
