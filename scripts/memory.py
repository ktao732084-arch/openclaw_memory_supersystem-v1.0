#!/usr/bin/env python3
"""
Memory System v1.1.7 - 三层记忆架构 CLI
支持 LLM 深度集成 + 访问日志追踪 + 时间敏感记忆 + 实体识别与隔离

v1.1.7 改进：
- LLM 深度集成：语义复杂度检测 + 智能触发 + 失败回退
- 扩大 LLM 触发区间：0.2~0.5（原 0.2~0.3）
- LLM 失败回退机制：失败时回退到规则结果，不丢弃
- API Key 多源获取：环境变量 → 配置文件 → 参数传入
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import re

# 导入 v1.1 新增模块
try:
    from v1_1_config import *
    from v1_1_helpers import *
    from v1_1_commands import *
    V1_1_ENABLED = True
except ImportError:
    V1_1_ENABLED = False
    print("⚠️ v1.1 模块未找到，部分功能不可用")

# 导入 v1.1.5 实体系统模块（用于实体隔离和学习实体清理）
try:
    from v1_1_5_entity_system import ENTITY_SYSTEM_CONFIG
    V1_1_5_ENABLED = True
except ImportError:
    V1_1_5_ENABLED = False
    # 静默失败，不打印警告（功能会优雅降级）

# 导入 v1.1.7 LLM 深度集成模块
try:
    from v1_1_7_llm_integration import (
        detect_semantic_complexity,
        should_use_llm_for_filtering,
        smart_filter_segment,
        smart_extract_entities,
        get_api_key,
        call_llm_with_fallback,
        LLMIntegrationStats,
        INTEGRATION_STATS,
        LLM_INTEGRATION_CONFIG,
    )
    V1_1_7_ENABLED = True
except ImportError:
    V1_1_7_ENABLED = False
    # 静默失败，功能会优雅降级

# ============================================================
# LLM 调用模块（v1.1.3 新增）
# ============================================================

def get_llm_config():
    """从环境变量获取 LLM 配置"""
    return {
        "api_key": os.environ.get("OPENAI_API_KEY"),
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "model": os.environ.get("MEMORY_LLM_MODEL", "gpt-3.5-turbo"),
        "enabled": os.environ.get("MEMORY_LLM_ENABLED", "true").lower() == "true"
    }

def call_llm(prompt, system_prompt=None, max_tokens=500):
    """
    调用 LLM（使用用户的 API Key）
    
    返回: (success: bool, result: str, error: str)
    """
    config = get_llm_config()
    
    # 检查是否启用 LLM
    if not config["enabled"]:
        return False, None, "LLM fallback disabled"
    
    # 检查 API Key
    if not config["api_key"]:
        return False, None, "OPENAI_API_KEY not found in environment"
    
    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": config["model"],
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3
        }
        
        response = requests.post(
            f"{config['base_url']}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # 统计 token 使用
            usage = result.get("usage", {})
            LLM_STATS["total_tokens"] += usage.get("total_tokens", 0)
            
            return True, content.strip(), None
        else:
            LLM_STATS["errors"] += 1
            return False, None, f"API error: {response.status_code}"
            
    except ImportError:
        LLM_STATS["errors"] += 1
        return False, None, "requests library not installed"
    except Exception as e:
        LLM_STATS["errors"] += 1
        return False, None, f"LLM call failed: {str(e)}"

# ============================================================
# 配置
# ============================================================

DEFAULT_CONFIG = {
    "version": "1.2.0",
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
    },
    "conflict_detection": {
        "enabled": True,
        "penalty": 0.2
    },
    "llm_fallback": {
        "enabled": True,
        "phase2_filter": True,
        "phase3_extract": True,
        "phase4b_verify": False,
        "min_confidence": 0.6
    },
    # v1.1.4 新增配置
    "funnel": {
        "tier2_threshold_lower": 0.35,
        "tier2_threshold_upper": 0.70,
        "tier3_default_ttl_days": 3,
        "tier3_reactivation_extend_days": 3,
        "tier3_max_ttl_days": 14
    },
    "access_tracking": {
        "enabled": True,
        "boost_coefficient": 0.2,
        "max_boost": 0.5,
        "weights": {
            "retrieval": 1.0,
            "used_in_response": 2.0,
            "user_mentioned": 3.0
        },
        "protection_days": {
            "strong": 3,
            "medium": 7,
            "weak": 14
        }
    },
    "time_sensitivity": {
        "enabled": True,
        "immediate_hours": 12,
        "short_term_days": 2,
        "medium_term_days": 10,
        "long_term_days": 35,
        "event_after_hours": 2
    }
}

# ============================================================
# v1.2.0 废话前置过滤器（规则强化）
# ============================================================

NOISE_PATTERNS = {
    # 纯语气词/感叹词（直接跳过，不进入 LLM）
    "pure_interjection": [
        r"^[哈嘿呵嗯啊哦噢呃唉嘛吧啦呀咯嘞哇喔]+[~～。！!？?]*$",  # 哈哈哈、嗯嗯、啊啊啊
        r"^[oO]+[kK]+[~～。！!？?]*$",  # ok, OK, okok
        r"^[yY]e+[sS]*[~～。！!？?]*$",  # yes, yeees
        r"^[nN]o+[~～。！!？?]*$",  # no, nooo
        r"^[lL][oO]+[lL]+[~～。！!？?]*$",  # lol, looool
    ],
    # 简单确认/应答（直接跳过）
    "simple_ack": [
        r"^(好的?|行|可以|没问题|收到|了解|明白|懂了?|知道了?|OK|ok|嗯|对|是的?)[~～。！!？?]*$",
        r"^(谢谢|感谢|thanks?|thx)[~～。！!？?]*$",
        r"^(不用|不必|算了|没事|无所谓)[~～。！!？?]*$",
    ],
    # 纯表情/符号
    "emoji_only": [
        r"^[\U0001F300-\U0001F9FF\U0001FA00-\U0001FAFF\u2600-\u26FF\u2700-\u27BF\s~～。！!？?]+$",  # emoji
        r"^[.。,，!！?？~～\s]+$",  # 纯标点
    ],
    # 过短内容（<3字符，排除数字和特殊标记）
    "too_short": [
        r"^.{0,2}$",  # 0-2个字符
    ],
}

def is_noise(content: str) -> tuple[bool, str]:
    """
    前置废话检测，返回 (是否废话, 匹配的类别)
    在 calculate_importance 之前调用，直接跳过明显废话
    """
    content = content.strip()
    
    for category, patterns in NOISE_PATTERNS.items():
        for pattern in patterns:
            if re.match(pattern, content):
                return True, category
    
    return False, ""

# ============================================================
# 重要性规则配置
# ============================================================

IMPORTANCE_RULES = {
    # 身份/健康/安全 → 1.0
    "identity_health_safety": {
        "keywords": ["过敏", "疾病", "病", "健康", "安全", "紧急", "危险", 
                     "我叫", "我是", "我的名字", "身份证", "电话", "地址",
                     "密码", "账号", "银行", "死", "生命"],
        "score": 1.0
    },
    # 偏好/关系/状态变更 → 0.8
    "preference_relation_status": {
        "keywords": ["喜欢", "讨厌", "爱", "恨", "偏好", "习惯",
                     "朋友", "家人", "父母", "妈妈", "爸爸", "兄弟", "姐妹",
                     "换工作", "搬家", "毕业", "结婚", "离婚", "分手",
                     "开始", "结束", "改变"],
        "score": 0.8
    },
    # 项目/任务/目标 → 0.7
    "project_task_goal": {
        "keywords": ["项目", "任务", "目标", "计划", "deadline", "截止",
                     "开发", "设计", "实现", "完成", "进度"],
        "score": 0.7
    },
    # 一般事实 → 0.5
    "general_fact": {
        "keywords": [],  # 默认
        "score": 0.5
    },
    # 临时信息 → 0.2
    "temporary": {
        "keywords": ["今天", "明天", "刚才", "一会儿", "待会", "马上",
                     "顺便", "随便", "无所谓"],
        "score": 0.2
    }
}

# 显式信号加成
EXPLICIT_SIGNALS = {
    "boost_high": {
        "keywords": ["记住", "永远记住", "一定要记住", "以后都", "永远都"],
        "boost": 0.5
    },
    "boost_medium": {
        "keywords": ["重要", "关键", "必须", "一定"],
        "boost": 0.3
    },
    "boost_low": {
        "keywords": ["注意", "别忘了"],
        "boost": 0.2
    },
    "reduce": {
        "keywords": ["顺便说一下", "随便问问", "不重要", "无所谓"],
        "boost": -0.2
    }
}

# 实体识别模式（v1.1.2 改进：支持正则模式）
ENTITY_PATTERNS = {
    "person": {
        "fixed": ["我", "你", "他", "她", "用户", "Ktao", "Tkao"],
        "patterns": [
            r"[A-Z][a-z]+",  # 英文人名：John, Mary（移除\b）
        ]
    },
    "project": {
        "fixed": ["项目", "系统", "工具", "应用", "App"],
        "patterns": [
            r"项目_\d+",  # 项目_1, 项目_25
            r"[A-Z][a-zA-Z0-9-]+",  # OpenClaw, Memory-System（移除\b）
        ]
    },
    "location": {
        "fixed": ["北京", "上海", "深圳", "广州", "杭州", "河南", "郑州"],
        "patterns": [
            r"城市_\d+",  # 城市_1, 城市_50
            r"地点_\d+",  # 地点_1, 地点_50
        ]
    },
    "organization": {
        "fixed": ["公司", "学校", "大学", "医院", "团队"],
        "patterns": [
            r"组织_\d+",  # 组织_1, 组织_50
            r"团队_\d+",  # 团队_1, 团队_50
        ]
    }
}

# v1.1.6 新增：引号实体模式（优先级高于通用词）
# 支持中英文引号：「」『』""''《》
QUOTED_ENTITY_PATTERNS = [
    # 中文单引号「」
    "\u300c([^\u300d]+)\u300d",
    # 中文双引号『』
    "\u300e([^\u300f]+)\u300f",
    # 中文弯引号""
    "\u201c([^\u201d]+)\u201d",
    # 中文弯引号''
    "\u2018([^\u2019]+)\u2019",
    # 书名号《》
    "\u300a([^\u300b]+)\u300b",
    # 英文单引号
    r"'([^']+)'",
    # 英文双引号
    r'"([^"]+)"',
]

# 冲突覆盖信号（v1.1.1 新增，v1.1.6 扩展）
# Tier 1: 高置信度修正信号 → 直接触发冲突覆盖
OVERRIDE_SIGNALS_TIER1 = [
    "不再", "改成", "换成", "搬到", "现在是", "已经是",
    "不是", "而是", "从", "到", "修正", "更正", "变成",
    "其实是", "实际上", "事实上", "准确说"
]

# Tier 2: 中置信度修正信号 → 标记为"可能冲突"，降权但不自动覆盖
OVERRIDE_SIGNALS_TIER2 = [
    "逗你的", "开玩笑", "骗你的", "瞎说的", "胡说",
    "刚才说错了", "说反了", "搞错了", "弄错了"
]

# 合并（向后兼容）
OVERRIDE_SIGNALS = OVERRIDE_SIGNALS_TIER1 + OVERRIDE_SIGNALS_TIER2

# 冲突降权系数
CONFLICT_PENALTY = 0.2

# LLM 调用统计（v1.1.3 新增）
LLM_STATS = {
    "phase2_calls": 0,
    "phase3_calls": 0,
    "total_tokens": 0,
    "errors": 0
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

def append_jsonl(path, record):
    """追加单条记录到 JSONL 文件"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')

# ============================================================
# Phase 2: 重要性筛选 - rule_filter()
# ============================================================

def calculate_importance(content):
    """
    基于规则计算内容的重要性分数
    返回: (importance_score, matched_category)
    """
    content_lower = content.lower()
    
    # 1. 检查内在重要性（从高到低）
    for category in ["identity_health_safety", "preference_relation_status", 
                     "project_task_goal", "temporary"]:
        rule = IMPORTANCE_RULES[category]
        for keyword in rule["keywords"]:
            if keyword in content or keyword in content_lower:
                base_score = rule["score"]
                break
        else:
            continue
        break
    else:
        # 默认为一般事实
        base_score = IMPORTANCE_RULES["general_fact"]["score"]
        category = "general_fact"
    
    # 2. 检查显式信号加成
    boost = 0
    for signal_type, signal_config in EXPLICIT_SIGNALS.items():
        for keyword in signal_config["keywords"]:
            if keyword in content:
                boost = max(boost, signal_config["boost"]) if signal_config["boost"] > 0 else min(boost, signal_config["boost"])
                break
    
    # 3. 计算最终分数
    final_score = min(1.0, max(0.0, base_score + boost))
    
    return final_score, category

def rule_filter(segments, threshold=0.3, use_llm_fallback=True):
    """
    Phase 2: 重要性筛选（v1.1.7：智能 LLM 集成）
    
    v1.1.7 改进：
    - 语义复杂度检测：识别需要 LLM 处理的复杂内容
    - 扩大 LLM 触发区间：0.2~0.5（原 0.2~0.3）
    - LLM 失败回退：失败时回退到规则结果，不丢弃
    
    输入: 语义片段列表
    输出: 筛选后的重要片段列表（带 importance 标注）
    """
    config = get_config()
    llm_enabled = config.get("llm_fallback", {}).get("enabled", True) and use_llm_fallback
    phase2_llm = config.get("llm_fallback", {}).get("phase2_filter", True)
    
    filtered = []
    noise_skipped = 0  # v1.2.0 统计
    
    for segment in segments:
        content = segment.get("content", "") if isinstance(segment, dict) else segment
        source = segment.get("source", "unknown") if isinstance(segment, dict) else "unknown"
        
        # v1.2.0: 前置废话过滤（跳过明显废话，不进入 LLM）
        is_noise_content, noise_category = is_noise(content)
        if is_noise_content:
            noise_skipped += 1
            continue
        
        # 1. 规则判断
        rule_importance, rule_category = calculate_importance(content)
        
        # 2. v1.1.7: 智能 LLM 集成
        if V1_1_7_ENABLED and llm_enabled and phase2_llm:
            # 使用智能筛选（自动决定是否调用 LLM）
            smart_result = smart_filter_segment(
                content=content,
                rule_importance=rule_importance,
                rule_category=rule_category,
                config_dict=config,
            )
            
            importance = smart_result["importance"]
            category = smart_result["category"]
            method = smart_result["method"]
            
            # 记录统计
            if smart_result.get("llm_stats"):
                INTEGRATION_STATS.record_phase2(smart_result["llm_stats"])
            if smart_result.get("complexity", {}).get("is_complex"):
                INTEGRATION_STATS.record_complexity_trigger()
            
            # 判断是否保留
            if importance >= threshold:
                result = {
                    "content": content,
                    "importance": importance,
                    "category": category,
                    "source": source,
                    "method": method,
                    "complexity": smart_result.get("complexity", {}),
                }
                filtered.append(result)
        else:
            # 回退到原有逻辑（v1.1.6 及之前）
            if rule_importance >= threshold:
                result = {
                    "content": content,
                    "importance": rule_importance,
                    "category": rule_category,
                    "source": source,
                    "method": "rule"
                }
                filtered.append(result)
            elif rule_importance >= threshold - 0.1:
                # 不确定区间，尝试 LLM
                if llm_enabled and phase2_llm:
                    llm_result = llm_filter_segment(content)
                    if llm_result:
                        importance = llm_result.get("importance", rule_importance)
                        if importance >= threshold:
                            result = {
                                "content": content,
                                "importance": importance,
                                "category": llm_result.get("category", rule_category),
                                "source": source,
                                "method": "llm"
                            }
                            filtered.append(result)
    
    return filtered
    
    return filtered

def llm_filter_segment(content):
    """
    使用 LLM 判断片段重要性
    
    返回: {"importance": float, "category": str} 或 None
    """
    LLM_STATS["phase2_calls"] += 1
    
    system_prompt = """你是一个记忆重要性评估专家。
评估用户输入的重要性（0-1），并分类。

分类标准：
- identity_health_safety (1.0): 身份、健康、安全相关
- preference_relation_status (0.8): 偏好、关系、状态变更
- project_task_goal (0.7): 项目、任务、目标
- general_fact (0.5): 一般事实
- temporary (0.2): 临时信息

返回 JSON 格式：
{"importance": 0.8, "category": "preference_relation_status", "reason": "简短理由"}"""

    prompt = f"""评估以下内容的重要性：

内容：{content}

返回 JSON："""

    success, result, error = call_llm(prompt, system_prompt, max_tokens=100)
    
    if success:
        try:
            # 尝试解析 JSON
            import re
            json_match = re.search(r'\{[^}]+\}', result)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "importance": float(data.get("importance", 0.5)),
                    "category": data.get("category", "general_fact")
                }
        except:
            pass
    
    return None

# ============================================================
# Phase 3: 深度提取 - template_extract()
# ============================================================

def extract_entities(content, memory_dir=None, use_llm_fallback=True):
    """
    从内容中提取实体
    
    v1.1.6 改进：四层识别架构
    - Layer 0: 引号实体（优先级最高，v1.1.6 新增）
    - Layer 1: 硬编码模式（ENTITY_PATTERNS）
    - Layer 2: 学习过的实体（learned_entities.json）
    - Layer 3: LLM 提取 + 自动学习
    
    参数:
        content: 要提取的内容
        memory_dir: 记忆目录（用于加载学习实体，可选）
        use_llm_fallback: 是否启用 LLM 兜底
    
    返回:
        list: 提取的实体列表
    """
    import re
    entities = []
    matched_positions = set()
    
    # ===== Layer 0: 引号实体（v1.1.6 新增，优先级最高）=====
    # 引号内的内容通常是专有名词，优先提取
    for pattern in QUOTED_ENTITY_PATTERNS:
        for match in re.finditer(pattern, content):
            # 提取引号内的内容（group(1) 是括号捕获的部分）
            quoted_text = match.group(1) if match.lastindex else match.group()
            if quoted_text and len(quoted_text) > 1 and quoted_text not in entities:
                entities.append(quoted_text)
                # 标记位置，避免后续重复匹配
                start, end = match.span()
                for i in range(start, end):
                    matched_positions.add(i)
    
    # ===== Layer 1: 硬编码模式（原有逻辑）=====
    for entity_type, config in ENTITY_PATTERNS.items():
        # 1. 固定词匹配
        if "fixed" in config:
            for word in config["fixed"]:
                if word in content:
                    entities.append(word)
        
        # 2. 正则模式匹配
        if "patterns" in config:
            for pattern in config["patterns"]:
                for match in re.finditer(pattern, content):
                    matched_text = match.group()
                    start, end = match.span()
                    
                    if not any(start < pos < end or pos == start for pos in matched_positions):
                        entities.append(matched_text)
                        for i in range(start, end):
                            matched_positions.add(i)
    
    # ===== Layer 2: 学习过的实体（v1.1.5 新增）=====
    if V1_1_5_ENABLED and memory_dir:
        from v1_1_5_entity_system import load_learned_entities
        learned = load_learned_entities(memory_dir)
        
        # 精确匹配
        for exact in learned.get("exact", []):
            if exact in content and exact not in entities:
                entities.append(exact)
        
        # 学习的模式匹配
        for pattern in learned.get("patterns", []):
            try:
                for match in re.finditer(pattern, content):
                    matched_text = match.group()
                    if matched_text not in entities:
                        entities.append(matched_text)
            except re.error:
                continue
    
    # ===== Layer 3: LLM 兜底（v1.1.5 新增）=====
    if not entities and V1_1_5_ENABLED and use_llm_fallback:
        config = get_config()
        llm_enabled = config.get("llm_fallback", {}).get("enabled", True)
        
        if llm_enabled:
            llm_result = llm_extract_entities(content)
            if llm_result:
                entities = llm_result.get("entities", [])
                
                # 学习新实体
                if entities and memory_dir:
                    from v1_1_5_entity_system import learn_new_entities
                    learn_new_entities(entities, memory_dir)
    
    # ===== 去重和过滤（原有逻辑）=====
    entities = [e for e in set(entities) if e and len(e) > 1]
    
    # 过滤：如果短实体是长实体的子串，移除短实体
    final_entities = []
    sorted_entities = sorted(entities, key=len, reverse=True)
    
    for entity in sorted_entities:
        is_substring = False
        for other in final_entities:
            if entity in other and entity != other:
                is_substring = True
                break
        if not is_substring:
            final_entities.append(entity)
    
    return final_entities

def classify_memory_type(content, importance):
    """
    判断记忆类型: fact / belief / summary
    """
    content_lower = content.lower()
    
    # 推断性词汇 → belief
    belief_indicators = ["可能", "也许", "大概", "应该", "似乎", "看起来", 
                         "我觉得", "我认为", "我猜", "估计", "probably", "maybe"]
    for indicator in belief_indicators:
        if indicator in content_lower:
            return "belief"
    
    # 聚合性词汇 → summary
    summary_indicators = ["总结", "综上", "总的来说", "概括", "整体上"]
    for indicator in summary_indicators:
        if indicator in content_lower:
            return "summary"
    
    # 默认 → fact
    return "fact"

def template_extract(filtered_segments, use_llm_fallback=True, memory_dir=None):
    """
    Phase 3: 深度提取（v1.1.5：三层实体识别 + LLM 兜底）
    将筛选后的片段转为结构化 facts/beliefs
    
    模板匹配优先，LLM 兜底
    """
    config = get_config()
    llm_enabled = config.get("llm_fallback", {}).get("enabled", True) and use_llm_fallback
    phase3_llm = config.get("llm_fallback", {}).get("phase3_extract", True)
    
    # 获取 memory_dir
    if memory_dir is None:
        memory_dir = get_memory_dir()
    
    extracted = {
        "facts": [],
        "beliefs": [],
        "summaries": []
    }
    
    for segment in filtered_segments:
        content = segment["content"]
        importance = segment["importance"]
        source = segment.get("source", "unknown")
        method = segment.get("method", "rule")
        
        # 1. v1.1.5: 三层实体识别（传入 memory_dir）
        entities = extract_entities(content, memory_dir=memory_dir, use_llm_fallback=llm_enabled and phase3_llm)
        mem_type = classify_memory_type(content, importance)
        
        # 2. 构建记录
        record = {
            "id": generate_id(mem_type[0], content),
            "content": content,
            "importance": importance,
            "score": importance,
            "entities": entities,
            "created": now_iso(),
            "source": source,
            "extract_method": method,
            # v1.1.4 新增字段
            "expires_at": None,
            "is_permanent": True,
            "access_count": 0,
            "retrieval_count": 0,
            "used_in_response_count": 0,
            "user_mentioned_count": 0,
            "last_accessed": None,
            "access_boost": 0.0,
            "tier3_tracked": False,
            "reactivation_count": 0,
            "final_score": importance
        }
        
        # v1.1.4: 时间敏感检测
        if V1_1_ENABLED:
            # 第一级强匹配
            tier1_result = check_tier1_patterns(content)
            if tier1_result:
                record['expires_at'] = tier1_result.get('expires_at')
                record['is_permanent'] = tier1_result.get('is_permanent', True)
            # 第二级 LLM 介入（灰色地带）
            elif 0.35 <= importance <= 0.70:
                llm_result = call_llm_time_sensor(content, importance)
                record['expires_at'] = llm_result.get('expires_at')
                record['is_permanent'] = llm_result.get('is_permanent', True)
        
        # belief 需要额外字段
        if mem_type == "belief":
            record["confidence"] = 0.6
            record["basis"] = f"从对话推断: {content[:50]}..."
        
        # 分类存储
        extracted[f"{mem_type}s"].append(record)
    
    return extracted

def llm_extract_entities(content):
    """
    使用 LLM 提取实体和记忆类型
    
    返回: {"entities": [...], "type": "fact/belief"} 或 None
    """
    LLM_STATS["phase3_calls"] += 1
    
    system_prompt = """你是一个实体提取专家。
从用户输入中提取关键实体（人物、地点、项目、组织等）。

返回 JSON 格式：
{"entities": ["实体1", "实体2"], "type": "fact", "reason": "简短理由"}

type 可选值：
- fact: 确定的事实
- belief: 推断或不确定的信息"""

    prompt = f"""从以下内容中提取实体：

内容：{content}

返回 JSON："""

    success, result, error = call_llm(prompt, system_prompt, max_tokens=150)
    
    if success:
        try:
            import re
            json_match = re.search(r'\{[^}]+\}', result)
            if json_match:
                data = json.loads(json_match.group())
                return {
                    "entities": data.get("entities", []),
                    "type": data.get("type", "fact")
                }
        except:
            pass
    
    return None

# ============================================================
# Phase 4a: Facts 去重合并
# ============================================================

# v1.1.6: 去重配置
DEDUP_CONFIG = {
    "min_overlap_ratio": 0.3,  # 最小重叠比例（30%）
    "tier1_penalty": 0.1,      # Tier 1 信号：强降权（保留 10%）
    "tier2_penalty": 0.4,      # Tier 2 信号：弱降权（保留 40%）
}

def tokenize_chinese(text):
    """
    简单的中文分词（字符级 + 英文单词）
    对于中文，使用 2-gram；对于英文，使用空格分词
    """
    import re
    tokens = set()
    
    # 提取英文单词
    english_words = re.findall(r'[a-zA-Z]+', text)
    tokens.update(english_words)
    
    # 提取中文字符的 2-gram
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    for i in range(len(chinese_chars) - 1):
        tokens.add(chinese_chars[i] + chinese_chars[i + 1])
    
    # 单个中文字符也加入（用于短文本）
    tokens.update(chinese_chars)
    
    return tokens

def deduplicate_facts(new_facts, existing_facts):
    """
    Phase 4a: Facts 去重合并 + 冲突检测（v1.1.6 改进）
    
    v1.1.6 改进：
    - 使用相对比例（30%）替代绝对数量（3）判断相似度
    - 分层冲突信号：Tier 1 强降权，Tier 2 弱降权
    
    返回: (merged_facts, duplicate_count, downgraded_count)
    """
    merged = []
    duplicate_count = 0
    downgraded_count = 0
    
    # 建立现有 facts 的索引（按实体分组）
    existing_by_entity = {}
    for fact in existing_facts:
        for entity in fact.get("entities", []):
            if entity not in existing_by_entity:
                existing_by_entity[entity] = []
            existing_by_entity[entity].append(fact)
    
    for new_fact in new_facts:
        is_duplicate = False
        new_content = new_fact["content"].lower()
        new_entities = new_fact.get("entities", [])
        
        # v1.1.6: 分层检测覆盖信号
        has_tier1_override = any(signal in new_fact["content"] for signal in OVERRIDE_SIGNALS_TIER1)
        has_tier2_override = any(signal in new_fact["content"] for signal in OVERRIDE_SIGNALS_TIER2)
        has_override = has_tier1_override or has_tier2_override
        
        # 检查是否与现有 fact 重复或冲突
        for entity in new_entities:
            if entity in existing_by_entity:
                for existing in existing_by_entity[entity]:
                    existing_content = existing["content"].lower()
                    
                    # 计算内容重叠度（v1.1.6: 使用中文分词）
                    new_tokens = tokenize_chinese(new_content)
                    existing_tokens = tokenize_chinese(existing_content)
                    overlap = len(new_tokens & existing_tokens)
                    
                    # v1.1.6: 使用相对比例替代绝对数量
                    min_len = min(len(new_tokens), len(existing_tokens))
                    overlap_ratio = overlap / max(min_len, 1)
                    
                    # v1.1.6: 相似度检查改用比例阈值
                    is_similar = (
                        new_content in existing_content or 
                        existing_content in new_content or
                        overlap_ratio >= DEDUP_CONFIG["min_overlap_ratio"]
                    )
                    
                    if is_similar:
                        # 如果新记忆包含覆盖信号，执行冲突降权
                        if has_override and overlap_ratio >= DEDUP_CONFIG["min_overlap_ratio"]:
                            # v1.1.6: 分层降权
                            old_score = existing.get("score", existing.get("importance", 0.5))
                            if has_tier1_override:
                                # Tier 1: 强降权（几乎废弃旧记忆）
                                penalty = DEDUP_CONFIG["tier1_penalty"]
                                existing["override_tier"] = 1
                            else:
                                # Tier 2: 弱降权（标记为可能冲突）
                                penalty = DEDUP_CONFIG["tier2_penalty"]
                                existing["override_tier"] = 2
                            
                            existing["score"] = old_score * penalty
                            existing["conflict_downgraded"] = True
                            existing["downgrade_reason"] = new_fact["id"]
                            existing["downgrade_at"] = now_iso()
                            downgraded_count += 1
                            # 不标记为重复，允许新记忆加入
                        else:
                            # 正常去重：更新现有记录（保留更高 importance）
                            if new_fact["importance"] > existing.get("importance", 0):
                                existing["content"] = new_fact["content"]
                                existing["importance"] = new_fact["importance"]
                                existing["score"] = max(existing.get("score", 0), new_fact["score"])
                            is_duplicate = True
                            duplicate_count += 1
                        break
            if is_duplicate:
                break
        
        if not is_duplicate:
            merged.append(new_fact)
    
    return merged, duplicate_count, downgraded_count

# ============================================================
# Phase 4b: Beliefs 验证 - code_verify_belief()
# ============================================================

def code_verify_belief(belief, facts):
    """
    Phase 4b: Beliefs 验证
    检查 belief 是否被 facts 证实
    
    返回: ("confirmed" | "contradicted" | "unchanged", updated_belief)
    """
    belief_content = belief["content"].lower()
    belief_entities = belief.get("entities", [])
    
    for fact in facts:
        fact_content = fact["content"].lower()
        fact_entities = fact.get("entities", [])
        
        # 检查实体重叠
        entity_overlap = set(belief_entities) & set(fact_entities)
        if not entity_overlap:
            continue
        
        # 检查内容关系
        # 1. 证实：fact 包含 belief 的核心内容
        belief_words = set(belief_content.split())
        fact_words = set(fact_content.split())
        overlap_ratio = len(belief_words & fact_words) / max(len(belief_words), 1)
        
        if overlap_ratio > 0.5:
            # 被证实 → 升级为 fact
            upgraded = belief.copy()
            upgraded["id"] = generate_id("f", belief["content"])
            upgraded["confidence"] = 1.0  # 升级为确定
            upgraded["verified_by"] = fact["id"]
            upgraded["verified_at"] = now_iso()
            return "confirmed", upgraded
        
        # 2. 矛盾检测（简单版：否定词）
        negation_words = ["不", "没", "无", "非", "否", "别", "不是", "没有"]
        belief_has_neg = any(neg in belief_content for neg in negation_words)
        fact_has_neg = any(neg in fact_content for neg in negation_words)
        
        if belief_has_neg != fact_has_neg and overlap_ratio > 0.3:
            # 可能矛盾 → 降低置信度
            updated = belief.copy()
            updated["confidence"] = max(0.1, belief.get("confidence", 0.6) - 0.3)
            updated["contradiction_hint"] = fact["id"]
            return "contradicted", updated
    
    return "unchanged", belief

# ============================================================
# Phase 4c: Summaries 生成
# ============================================================

def generate_summaries(facts, existing_summaries, trigger_count=3):
    """
    Phase 4c: Summaries 生成
    当同一实体有 >= trigger_count 个 facts 时，生成摘要
    
    返回: 新生成的 summaries 列表
    """
    new_summaries = []
    
    # 按实体分组 facts
    facts_by_entity = {}
    for fact in facts:
        for entity in fact.get("entities", []):
            if entity not in facts_by_entity:
                facts_by_entity[entity] = []
            facts_by_entity[entity].append(fact)
    
    # 检查已有摘要覆盖的实体
    summarized_entities = set()
    for summary in existing_summaries:
        summarized_entities.update(summary.get("entities", []))
    
    # 为符合条件的实体生成摘要
    for entity, entity_facts in facts_by_entity.items():
        if len(entity_facts) >= trigger_count and entity not in summarized_entities:
            # 按重要性排序，取 top facts
            sorted_facts = sorted(entity_facts, key=lambda x: x.get("importance", 0), reverse=True)
            top_facts = sorted_facts[:5]
            
            # 生成摘要内容（简单拼接）
            summary_content = f"关于{entity}的信息: " + "; ".join([f["content"][:30] for f in top_facts])
            
            # 计算摘要重要性（取平均）
            avg_importance = sum(f.get("importance", 0.5) for f in top_facts) / len(top_facts)
            
            summary = {
                "id": generate_id("s", summary_content),
                "content": summary_content,
                "importance": avg_importance,
                "score": avg_importance,
                "entities": [entity],
                "source_facts": [f["id"] for f in top_facts],
                "created": now_iso()
            }
            new_summaries.append(summary)
    
    return new_summaries

# ============================================================
# Phase 4d: Entities 更新
# ============================================================

def update_entities(facts, beliefs, summaries, memory_dir):
    """
    Phase 4d: Entities 更新
    维护实体档案
    """
    entities_dir = memory_dir / 'layer2/entities'
    index_path = entities_dir / '_index.json'
    
    # 加载现有索引
    if index_path.exists():
        with open(index_path, 'r', encoding='utf-8') as f:
            index = json.load(f)
    else:
        index = {"entities": []}
    
    # 收集所有实体
    all_entities = set()
    entity_facts = {}
    entity_beliefs = {}
    entity_summaries = {}
    
    for fact in facts:
        for entity in fact.get("entities", []):
            all_entities.add(entity)
            if entity not in entity_facts:
                entity_facts[entity] = []
            entity_facts[entity].append(fact["id"])
    
    for belief in beliefs:
        for entity in belief.get("entities", []):
            all_entities.add(entity)
            if entity not in entity_beliefs:
                entity_beliefs[entity] = []
            entity_beliefs[entity].append(belief["id"])
    
    for summary in summaries:
        for entity in summary.get("entities", []):
            all_entities.add(entity)
            if entity not in entity_summaries:
                entity_summaries[entity] = []
            entity_summaries[entity].append(summary["id"])
    
    # 更新每个实体的档案
    updated_count = 0
    for entity in all_entities:
        entity_id = hashlib.md5(entity.encode()).hexdigest()[:8]
        entity_path = entities_dir / f'{entity_id}.json'
        
        entity_data = {
            "id": entity_id,
            "name": entity,
            "facts": entity_facts.get(entity, []),
            "beliefs": entity_beliefs.get(entity, []),
            "summaries": entity_summaries.get(entity, []),
            "updated": now_iso()
        }
        
        with open(entity_path, 'w', encoding='utf-8') as f:
            json.dump(entity_data, f, indent=2, ensure_ascii=False)
        
        # 更新索引
        if entity not in [e["name"] for e in index["entities"]]:
            index["entities"].append({
                "id": entity_id,
                "name": entity,
                "count": len(entity_facts.get(entity, [])) + len(entity_beliefs.get(entity, []))
            })
        
        updated_count += 1
    
    # 保存索引
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index, f, indent=2, ensure_ascii=False)
    
    return updated_count

# ============================================================
# Router 逻辑 - 智能检索系统
# ============================================================

# 触发条件关键词
TRIGGER_KEYWORDS = {
    "layer0_explicit": ["你还记得", "帮我回忆", "之前说过", "上次提到", "我告诉过你"],
    "layer0_time": ["之前", "以前", "上次", "昨天", "前几天", "那时候", "当时"],
    "layer1_preference": ["我喜欢", "我讨厌", "我偏好", "我习惯", "我爱", "我恨"],
    "layer1_identity": ["我是", "我叫", "我的名字", "关于我"],
    "layer1_relation": ["朋友", "家人", "同事", "父母", "兄弟", "姐妹"],
    "layer1_project": ["项目", "任务", "计划", "目标", "进度"],
}

# 查询类型配置
QUERY_CONFIG = {
    "precise": {
        "initial": 15,
        "rerank": 10,
        "final": 8
    },
    "topic": {
        "initial": 25,
        "rerank": 16,
        "final": 13
    },
    "broad": {
        "initial": 35,
        "rerank": 25,
        "final": 18
    }
}

# 会话缓存
_session_cache = {}
_cache_ttl = 1800  # 30分钟

def get_cache_key(query):
    """生成缓存键"""
    return hashlib.md5(query.encode()).hexdigest()[:12]

def get_cached_result(query):
    """获取缓存结果"""
    key = get_cache_key(query)
    if key in _session_cache:
        entry = _session_cache[key]
        if datetime.utcnow().timestamp() - entry["time"] < _cache_ttl:
            return entry["result"]
        else:
            del _session_cache[key]
    return None

def set_cached_result(query, result):
    """设置缓存结果"""
    key = get_cache_key(query)
    _session_cache[key] = {
        "time": datetime.utcnow().timestamp(),
        "result": result
    }

def detect_trigger_layer(query):
    """
    检测查询触发的层级
    返回: (layer, trigger_type, matched_keywords)
    """
    query_lower = query.lower()
    
    # Layer 0: 显式请求或时间引用
    for trigger_type in ["layer0_explicit", "layer0_time"]:
        keywords = TRIGGER_KEYWORDS[trigger_type]
        matched = [kw for kw in keywords if kw in query_lower]
        if matched:
            return 0, trigger_type, matched
    
    # Layer 1: 偏好/身份/关系/项目
    for trigger_type in ["layer1_preference", "layer1_identity", "layer1_relation", "layer1_project"]:
        keywords = TRIGGER_KEYWORDS[trigger_type]
        matched = [kw for kw in keywords if kw in query_lower]
        if matched:
            return 1, trigger_type, matched
    
    # Layer 2: 默认（任务类型映射）
    return 2, "default", []

def classify_query_type(query, trigger_layer):
    """
    分类查询类型: precise / topic / broad
    """
    query_lower = query.lower()
    
    # 精准查询：具体问题、特定实体
    precise_indicators = ["是什么", "是谁", "在哪", "什么时候", "多少", "具体"]
    if any(ind in query_lower for ind in precise_indicators) or trigger_layer == 0:
        return "precise"
    
    # 广度查询：总结、概览、所有
    broad_indicators = ["所有", "全部", "总结", "概括", "列出", "有哪些"]
    if any(ind in query_lower for ind in broad_indicators):
        return "broad"
    
    # 默认：主题查询
    return "topic"

def keyword_search(query, memory_dir, limit=20):
    """
    基于关键词的检索
    返回: [(memory_id, score, content), ...]
    """
    import re
    
    # 加载关键词索引
    keywords_path = memory_dir / 'layer2/index/keywords.json'
    if not keywords_path.exists():
        return []
    
    with open(keywords_path, 'r', encoding='utf-8') as f:
        keywords_index = json.load(f)
    
    # 提取查询关键词（改进版）
    query_words = set()
    segments = re.split(r'[，。！？、；：""''（）\[\]【】\s]+', query)
    for seg in segments:
        seg = seg.strip()
        if len(seg) >= 2:
            query_words.add(seg)
        # 提取2-4字子串
        for i in range(len(seg)):
            for length in [2, 3, 4]:
                if i + length <= len(seg):
                    sub = seg[i:i+length]
                    if len(sub) >= 2:
                        query_words.add(sub)
    
    # 计算每个记忆的匹配分数
    memory_scores = {}
    for word in query_words:
        if word in keywords_index:
            for mem_id in keywords_index[word]:
                if mem_id not in memory_scores:
                    memory_scores[mem_id] = 0
                memory_scores[mem_id] += 1
    
    # 加载记忆内容
    results = []
    all_memories = {}
    for mem_type in ['facts', 'beliefs', 'summaries']:
        records = load_jsonl(memory_dir / f'layer2/active/{mem_type}.jsonl')
        for r in records:
            all_memories[r['id']] = r
    
    # 排序并返回
    sorted_ids = sorted(memory_scores.keys(), key=lambda x: memory_scores[x], reverse=True)
    for mem_id in sorted_ids[:limit]:
        if mem_id in all_memories:
            mem = all_memories[mem_id]
            results.append({
                "id": mem_id,
                "score": memory_scores[mem_id],
                "content": mem.get("content", ""),
                "importance": mem.get("importance", 0.5),
                "memory_score": mem.get("score", 0.5),
                "type": "fact" if mem_id.startswith("f_") else ("belief" if mem_id.startswith("b_") else "summary")
            })
    
    return results

def entity_search(query, memory_dir, limit=20):
    """
    基于实体的检索
    返回: [(memory_id, score, content), ...]
    """
    # 加载实体索引
    relations_path = memory_dir / 'layer2/index/relations.json'
    if not relations_path.exists():
        return []
    
    with open(relations_path, 'r', encoding='utf-8') as f:
        relations_index = json.load(f)
    
    # 检查查询中是否包含已知实体
    matched_entities = []
    for entity in relations_index.keys():
        if entity in query:
            matched_entities.append(entity)
    
    if not matched_entities:
        return []
    
    # 收集相关记忆
    memory_ids = set()
    for entity in matched_entities:
        entity_data = relations_index[entity]
        for mem_type in ['facts', 'beliefs', 'summaries']:
            memory_ids.update(entity_data.get(mem_type, []))
    
    # 加载记忆内容
    results = []
    all_memories = {}
    for mem_type in ['facts', 'beliefs', 'summaries']:
        records = load_jsonl(memory_dir / f'layer2/active/{mem_type}.jsonl')
        for r in records:
            all_memories[r['id']] = r
    
    for mem_id in list(memory_ids)[:limit]:
        if mem_id in all_memories:
            mem = all_memories[mem_id]
            results.append({
                "id": mem_id,
                "score": len([e for e in matched_entities if e in mem.get("entities", [])]),
                "content": mem.get("content", ""),
                "importance": mem.get("importance", 0.5),
                "memory_score": mem.get("score", 0.5),
                "type": "fact" if mem_id.startswith("f_") else ("belief" if mem_id.startswith("b_") else "summary")
            })
    
    return results

def rerank_results(results, query, limit, memory_dir=None):
    """
    重排序检索结果
    
    v1.1.5 改进：集成实体隔离（竞争性抑制）
    
    综合考虑: 匹配分数 + 记忆重要性 + 记忆score + 实体隔离
    """
    # 1. 计算基础综合分数
    for r in results:
        r["final_score"] = (
            r.get("score", 0) * 0.4 +
            r.get("importance", 0.5) * 0.3 +
            r.get("memory_score", 0.5) * 0.3
        )
    
    # 2. v1.1.5: 实体隔离（竞争性抑制）
    if V1_1_5_ENABLED and results:
        from v1_1_5_entity_system import (
            extract_entities as extract_entities_v1_1_5,
            should_apply_entity_isolation,
            find_similar_entity_groups,
            is_similar_entity,
            ENTITY_SYSTEM_CONFIG
        )
        
        if memory_dir is None:
            memory_dir = get_memory_dir()
        
        # 从查询中提取实体
        query_entities = extract_entities(query, memory_dir=memory_dir, use_llm_fallback=False)
        
        if query_entities:
            # 收集所有候选实体
            all_candidate_entities = set()
            for r in results:
                all_candidate_entities.update(r.get('entities', []))
            
            # 找出相似实体组
            similar_groups = find_similar_entity_groups(query_entities, list(all_candidate_entities))
            
            if similar_groups:
                inhibition_factor = ENTITY_SYSTEM_CONFIG["isolation"]["inhibition_factor"]
                
                for r in results:
                    mem_entities = set(r.get('entities', []))
                    
                    # 精确匹配查询实体 → 保持权重
                    if mem_entities & set(query_entities):
                        continue
                    
                    # 包含相似但不同的实体 → 抑制
                    for group in similar_groups:
                        if mem_entities & group and not (mem_entities & set(query_entities)):
                            r['final_score'] *= inhibition_factor
                            r['isolation_applied'] = True
                            r['isolation_reason'] = f"竞争性抑制: {mem_entities & group}"
                            break
    
    # 3. 按综合分数排序
    results.sort(key=lambda x: x["final_score"], reverse=True)
    return results[:limit]

def format_injection(results, confidence_threshold_high=0.8, confidence_threshold_low=0.5):
    """
    格式化注入结果
    - 高置信度(>0.8): 直接注入，无标记
    - 中置信度(0.5-0.8): 注入 + 来源标记
    - 低置信度(<0.5): 仅提供引用路径
    """
    output = {
        "direct": [],      # 直接注入
        "marked": [],      # 带标记注入
        "reference": []    # 仅引用
    }
    
    for r in results:
        confidence = r.get("memory_score", 0.5)
        
        if confidence >= confidence_threshold_high:
            output["direct"].append({
                "content": r["content"],
                "type": r["type"]
            })
        elif confidence >= confidence_threshold_low:
            output["marked"].append({
                "content": r["content"],
                "type": r["type"],
                "source": r["id"]
            })
        else:
            output["reference"].append({
                "id": r["id"],
                "preview": r["content"][:50] + "..."
            })
    
    return output

def router_search(query, memory_dir=None):
    """
    Router 主入口：智能检索记忆
    
    参数:
        query: 用户查询
        memory_dir: 记忆目录（可选）
    
    返回:
        {
            "trigger_layer": 0/1/2,
            "trigger_type": str,
            "query_type": "precise"/"topic"/"broad",
            "results": [...],
            "injection": {...},
            "cached": bool
        }
    """
    if memory_dir is None:
        memory_dir = get_memory_dir()
    
    # 检查缓存
    cached = get_cached_result(query)
    if cached:
        cached["cached"] = True
        return cached
    
    # 1. 检测触发层级
    trigger_layer, trigger_type, matched_keywords = detect_trigger_layer(query)
    
    # 2. 分类查询类型
    query_type = classify_query_type(query, trigger_layer)
    config = QUERY_CONFIG[query_type]
    
    # 3. 多路检索
    keyword_results = keyword_search(query, memory_dir, limit=config["initial"])
    entity_results = entity_search(query, memory_dir, limit=config["initial"])
    
    # 4. 合并去重
    seen_ids = set()
    merged_results = []
    for r in keyword_results + entity_results:
        if r["id"] not in seen_ids:
            seen_ids.add(r["id"])
            merged_results.append(r)
    
    # 5. 重排序（v1.1.5: 内部集成实体隔离）
    reranked = rerank_results(merged_results, query, config["rerank"], memory_dir=memory_dir)
    
    # 6. 最终筛选
    final_results = reranked[:config["final"]]
    
    # 7. 格式化注入
    injection = format_injection(final_results)
    
    # 构建结果
    result = {
        "trigger_layer": trigger_layer,
        "trigger_type": trigger_type,
        "matched_keywords": matched_keywords,
        "query_type": query_type,
        "results": final_results,
        "injection": injection,
        "stats": {
            "keyword_hits": len(keyword_results),
            "entity_hits": len(entity_results),
            "merged": len(merged_results),
            "final": len(final_results)
        },
        "cached": False
    }
    
    # 缓存结果
    set_cached_result(query, result)
    
    return result

def cmd_search(args):
    """执行记忆检索"""
    memory_dir = get_memory_dir()
    
    if not memory_dir.exists():
        print("❌ 记忆系统未初始化")
        return
    
    query = args.query
    result = router_search(query, memory_dir)
    
    print(f"🔍 检索: {query}")
    print("=" * 50)
    print(f"触发层级: Layer {result['trigger_layer']} ({result['trigger_type']})")
    print(f"查询类型: {result['query_type']}")
    print(f"匹配关键词: {result['matched_keywords']}")
    print(f"缓存命中: {'是' if result['cached'] else '否'}")
    print()
    print(f"📊 检索统计:")
    print(f"   关键词命中: {result['stats']['keyword_hits']}")
    print(f"   实体命中: {result['stats']['entity_hits']}")
    print(f"   合并后: {result['stats']['merged']}")
    print(f"   最终结果: {result['stats']['final']}")
    print()
    
    if result['results']:
        print("📋 检索结果:")
        for i, r in enumerate(result['results'][:10]):
            print(f"   {i+1}. [{r['type'][0].upper()}] {r['content'][:50]}...")
            print(f"      score={r['final_score']:.2f}, importance={r['importance']:.1f}")
    else:
        print("📋 无匹配结果")
    
    print()
    print("💉 注入建议:")
    inj = result['injection']
    print(f"   直接注入: {len(inj['direct'])} 条")
    print(f"   带标记注入: {len(inj['marked'])} 条")
    print(f"   仅引用: {len(inj['reference'])} 条")
    
    if args.json:
        print()
        print("📄 JSON 输出:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

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
    state['current_phase'] = 0
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    
    try:
        # 用于存储中间结果
        phase_data = state.get('phase_data', {})
        
        # Phase 0: 清理过期记忆（v1.1.4 新增）
        if V1_1_ENABLED and (not args.phase or args.phase == 0):
            print("\n🗑️ Phase 0: 清理过期记忆")
            expired_count = phase0_expire_memories(memory_dir)
            print(f"   归档 {expired_count} 条过期记忆")
            print("   ✅ 完成")
        
        # Phase 1: 轻量全量（模拟 - 需要接入 OpenClaw session）
        if not args.phase or args.phase == 1:
            print("\n📋 Phase 1: 轻量全量（切分片段）")
            # TODO: 接入 OpenClaw session 数据
            # 目前使用模拟数据或从 stdin 读取
            if args.input:
                with open(args.input, 'r', encoding='utf-8') as f:
                    raw_text = f.read()
                # 简单按句子切分
                segments = []
                for line in raw_text.split('\n'):
                    line = line.strip()
                    if line and len(line) > 5:
                        segments.append({"content": line, "source": args.input})
                phase_data['segments'] = segments
                print(f"   从文件读取 {len(segments)} 个片段")
            else:
                print("   [跳过] 无输入数据，使用 --input 指定输入文件")
                phase_data['segments'] = []
            print("   ✅ 完成")
        
        # Phase 2: 重要性筛选
        if not args.phase or args.phase == 2:
            print("\n🎯 Phase 2: 重要性筛选")
            segments = phase_data.get('segments', [])
            if segments:
                filtered = rule_filter(segments, threshold=0.3)
                phase_data['filtered'] = filtered
                print(f"   输入: {len(segments)} 片段")
                print(f"   筛选后: {len(filtered)} 片段 (threshold=0.3)")
                for f in filtered[:3]:
                    print(f"     - [{f['importance']:.1f}] {f['content'][:40]}...")
            else:
                phase_data['filtered'] = []
                print("   [跳过] 无输入片段")
            print("   ✅ 完成")
        
        # Phase 3: 深度提取
        if not args.phase or args.phase == 3:
            print("\n📝 Phase 3: 深度提取")
            filtered = phase_data.get('filtered', [])
            if filtered:
                extracted = template_extract(filtered)
                phase_data['extracted'] = extracted
                print(f"   提取结果:")
                print(f"     - Facts: {len(extracted['facts'])}")
                print(f"     - Beliefs: {len(extracted['beliefs'])}")
                print(f"     - Summaries: {len(extracted['summaries'])}")
            else:
                phase_data['extracted'] = {'facts': [], 'beliefs': [], 'summaries': []}
                print("   [跳过] 无筛选片段")
            print("   ✅ 完成")
        
        # Phase 4: Layer 2 维护
        if not args.phase or args.phase == 4:
            print("\n🔧 Phase 4: Layer 2 维护")
            extracted = phase_data.get('extracted', {'facts': [], 'beliefs': [], 'summaries': []})
            
            # 加载现有记忆
            existing_facts = load_jsonl(memory_dir / 'layer2/active/facts.jsonl')
            existing_beliefs = load_jsonl(memory_dir / 'layer2/active/beliefs.jsonl')
            existing_summaries = load_jsonl(memory_dir / 'layer2/active/summaries.jsonl')
            
            # 4a: Facts 去重合并
            print("   4a: Facts 去重合并 + 冲突检测")
            new_facts = extracted.get('facts', [])
            if new_facts:
                merged_facts, dup_count, downgrade_count = deduplicate_facts(new_facts, existing_facts)
                print(f"       新增: {len(merged_facts)}, 去重: {dup_count}, 降权: {downgrade_count}")
                # 追加新 facts
                for fact in merged_facts:
                    append_jsonl(memory_dir / 'layer2/active/facts.jsonl', fact)
                # 如果有降权，需要重写 existing_facts
                if downgrade_count > 0:
                    save_jsonl(memory_dir / 'layer2/active/facts.jsonl', existing_facts)
            else:
                print("       [跳过] 无新 facts")
            
            # 4b: Beliefs 验证
            print("   4b: Beliefs 验证")
            new_beliefs = extracted.get('beliefs', [])
            all_facts = existing_facts + extracted.get('facts', [])
            confirmed_count = 0
            contradicted_count = 0
            
            for belief in new_beliefs:
                status, updated = code_verify_belief(belief, all_facts)
                if status == "confirmed":
                    # 升级为 fact
                    append_jsonl(memory_dir / 'layer2/active/facts.jsonl', updated)
                    confirmed_count += 1
                elif status == "contradicted":
                    # 降低置信度后保存
                    append_jsonl(memory_dir / 'layer2/active/beliefs.jsonl', updated)
                    contradicted_count += 1
                else:
                    # 保持不变
                    append_jsonl(memory_dir / 'layer2/active/beliefs.jsonl', belief)
            
            print(f"       证实→升级: {confirmed_count}, 矛盾→降权: {contradicted_count}")
            
            # 4c: Summaries 生成
            print("   4c: Summaries 生成")
            all_facts_now = load_jsonl(memory_dir / 'layer2/active/facts.jsonl')
            trigger_count = config['thresholds'].get('summary_trigger', 3)
            new_summaries = generate_summaries(all_facts_now, existing_summaries, trigger_count)
            if new_summaries:
                for summary in new_summaries:
                    append_jsonl(memory_dir / 'layer2/active/summaries.jsonl', summary)
                print(f"       生成: {len(new_summaries)} 条新摘要")
            else:
                print("       [跳过] 无需生成摘要")
            
            # 4d: Entities 更新
            print("   4d: Entities 更新")
            all_facts_final = load_jsonl(memory_dir / 'layer2/active/facts.jsonl')
            all_beliefs_final = load_jsonl(memory_dir / 'layer2/active/beliefs.jsonl')
            all_summaries_final = load_jsonl(memory_dir / 'layer2/active/summaries.jsonl')
            entity_count = update_entities(all_facts_final, all_beliefs_final, all_summaries_final, memory_dir)
            print(f"       更新: {entity_count} 个实体档案")
            
            print("   ✅ 完成")
        
        # Phase 5: 权重更新
        if not args.phase or args.phase == 5:
            print("\n⚖️ Phase 5: 权重更新")
            decay_rates = config['decay_rates']
            archive_threshold = config['thresholds']['archive']
            
            # 5a: 应用访问加成（v1.1.5 已在 v1_1_helpers.calculate_access_boost 中修复）
            if V1_1_ENABLED:
                print("   5a: 应用访问加成")
                for mem_type in ['facts', 'beliefs', 'summaries']:
                    active_path = memory_dir / f'layer2/active/{mem_type}.jsonl'
                    records = load_jsonl(active_path)
                    records = phase5_rank_with_access_boost(records)
                    save_jsonl(active_path, records)
                print("   ✅ 访问加成完成")
            
            # 5b: v1.1.5 清理废弃的学习实体
            if V1_1_5_ENABLED:
                print("   5b: 清理废弃学习实体")
                from v1_1_5_entity_system import cleanup_learned_entities
                cleanup_stats = cleanup_learned_entities(memory_dir)
                print(f"       清理: {cleanup_stats['exact_removed']} 实体, {cleanup_stats['patterns_removed']} 模式")
                print(f"       保留: {cleanup_stats['exact_remaining']} 实体, {cleanup_stats['patterns_remaining']} 模式")
            
            # 5c: 衰减（含访问保护）
            print("   5c: 衰减更新")
            archived_count = 0
            for mem_type in ['facts', 'beliefs', 'summaries']:
                active_path = memory_dir / f'layer2/active/{mem_type}.jsonl'
                archive_path = memory_dir / f'layer2/archive/{mem_type}.jsonl'
                
                records = load_jsonl(active_path)
                
                # v1.1.4: 应用访问保护衰减
                if V1_1_ENABLED:
                    records = phase6_decay_with_access_protection(records, config)
                else:
                    # v1.1.3 原始衰减逻辑
                    decay_rate = decay_rates.get(mem_type.rstrip('s'), 0.01)
                    for r in records:
                        importance = r.get('importance', 0.5)
                        actual_decay = decay_rate * (1 - importance * 0.5)
                        r['score'] = r.get('score', importance) * (1 - actual_decay)
                
                remaining = []
                to_archive = []
                
                for r in records:
                    if r.get('score', 0) < archive_threshold:
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
            
            # 中文分词辅助函数
            def extract_keywords(text):
                """提取关键词（改进版：保留连字符词）"""
                import re
                keywords = set()
                
                # 1. 优先提取连字符词（memory-system, v1.1, API-key等）
                hyphen_words = re.findall(r'[a-zA-Z0-9][-a-zA-Z0-9.]+', text)
                for word in hyphen_words:
                    if len(word) > 1:
                        keywords.add(word.lower())
                
                # 2. 提取中文词组（2字以上）
                chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,}', text)
                for word in chinese_words:
                    keywords.add(word)
                
                # 3. 提取纯英文单词（不含连字符的）
                english_words = re.findall(r'\b[a-zA-Z]{2,}\b', text)
                for word in english_words:
                    keywords.add(word.lower())
                
                return keywords
            
            for mem_type in ['facts', 'beliefs', 'summaries']:
                records = load_jsonl(memory_dir / f'layer2/active/{mem_type}.jsonl')
                for r in records:
                    # 改进的关键词提取
                    content = r.get('content', '')
                    keywords = extract_keywords(content)
                    for word in keywords:
                        if word not in keywords_index:
                            keywords_index[word] = []
                        if r['id'] not in keywords_index[word]:
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
            downgraded = [r for r in all_records if r.get('conflict_downgraded', False)]
            
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
            
            # 新增：降权记忆标注
            if downgraded:
                snapshot += f"""
## 📉 已降权记忆 (冲突覆盖)
"""
                for r in downgraded[:5]:
                    content = r.get('content', '')[:40]
                    old_score = r.get('importance', 0.5)
                    new_score = r.get('score', 0)
                    snapshot += f"- ~~{content}~~ (Score: {old_score:.2f} → {new_score:.2f})\n"
            
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
        
        # v1.1.7: 显示智能 LLM 集成统计
        if V1_1_7_ENABLED:
            summary = INTEGRATION_STATS.summary()
            total_calls = summary["phase2"]["calls"] + summary["phase3"]["calls"]
            if total_calls > 0:
                INTEGRATION_STATS.print_summary()
            else:
                print("\n💰 Token 节省: 100% (纯规则处理，无 LLM 调用)")
        # 回退到原有统计（v1.1.6 及之前）
        elif LLM_STATS["phase2_calls"] > 0 or LLM_STATS["phase3_calls"] > 0:
            print("\n📊 LLM 调用统计:")
            print(f"   Phase 2 (筛选): {LLM_STATS['phase2_calls']} 次")
            print(f"   Phase 3 (提取): {LLM_STATS['phase3_calls']} 次")
            print(f"   总 Token: {LLM_STATS['total_tokens']}")
            if LLM_STATS["errors"] > 0:
                print(f"   ⚠️  错误: {LLM_STATS['errors']} 次")
        else:
            print("\n💰 Token 节省: 100% (纯规则处理，无 LLM 调用)")
        
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
    parser_consolidate.add_argument('--phase', type=int, choices=[0,1,2,3,4,5,6,7], help='只执行指定阶段')
    parser_consolidate.add_argument('--input', help='输入文件路径（Phase 1 数据源）')
    parser_consolidate.set_defaults(func=cmd_consolidate)
    
    # rebuild-index
    parser_rebuild = subparsers.add_parser('rebuild-index', help='重建索引')
    parser_rebuild.set_defaults(func=cmd_rebuild_index)
    
    # validate
    parser_validate = subparsers.add_parser('validate', help='验证数据完整性')
    parser_validate.set_defaults(func=cmd_validate)
    
    # search
    parser_search = subparsers.add_parser('search', help='智能检索记忆')
    parser_search.add_argument('query', help='检索查询')
    parser_search.add_argument('--json', action='store_true', help='输出 JSON 格式')
    parser_search.set_defaults(func=cmd_search)
    
    # v1.1.4 新增命令
    if V1_1_ENABLED:
        # record-access
        parser_access = subparsers.add_parser('record-access', help='记录访问日志')
        parser_access.add_argument('id', help='记忆 ID')
        parser_access.add_argument('--type', choices=['retrieval', 'used_in_response', 'user_mentioned'], 
                                   default='retrieval', help='访问类型')
        parser_access.add_argument('--query', help='查询内容')
        parser_access.add_argument('--context', help='上下文')
        parser_access.set_defaults(func=lambda args: cmd_record_access(args, get_memory_dir()))
        
        # view-access-log
        parser_view_access = subparsers.add_parser('view-access-log', help='查看访问日志')
        parser_view_access.add_argument('--limit', type=int, default=20, help='显示条数')
        parser_view_access.set_defaults(func=lambda args: cmd_view_access_log(args, get_memory_dir()))
        
        # view-expired-log
        parser_view_expired = subparsers.add_parser('view-expired-log', help='查看过期记忆日志')
        parser_view_expired.add_argument('--limit', type=int, default=20, help='显示条数')
        parser_view_expired.set_defaults(func=lambda args: cmd_view_expired_log(args, get_memory_dir()))
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        return
    
    args.func(args)

if __name__ == '__main__':
    main()
