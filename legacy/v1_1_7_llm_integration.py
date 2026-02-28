#!/usr/bin/env python3
"""
Memory System v1.1.7 - LLM 深度集成模块

核心改进：
1. 语义复杂度检测 - 识别需要 LLM 处理的复杂内容
2. 扩大 LLM 触发区间 - 不确定区间从 0.2~0.3 扩大到 0.2~0.5
3. LLM 失败回退机制 - 失败时回退到规则结果，不丢弃
4. API Key 多源获取 - 环境变量 → 配置文件 → 参数传入
5. 智能调用策略 - 根据内容复杂度决定是否调用 LLM
"""

import os
import re
import json
from typing import Optional, Dict, Any, Tuple, List

# ============================================================
# 配置
# ============================================================

LLM_INTEGRATION_CONFIG = {
    # LLM 触发策略
    "trigger": {
        "high_confidence_threshold": 0.5,   # 高于此值，规则直接接受（除非语义复杂）
        "low_confidence_threshold": 0.2,    # 低于此值，检查语义复杂度
        "uncertain_range": (0.2, 0.5),      # 不确定区间，交给 LLM
        "force_llm_on_complex": True,       # 复杂内容强制 LLM
    },
    
    # 语义复杂度检测
    "complexity": {
        "min_length_for_check": 10,         # 最小长度才检测复杂度
        "entity_count_threshold": 3,        # 实体数量阈值
        "relation_indicators": [            # 关系指示词
            "认为", "觉得", "怀疑", "可能", "也许", "大概",
            "据说", "听说", "似乎", "好像", "应该", "或许",
            "如果", "假如", "除非", "尽管", "虽然", "但是",
            "因为", "所以", "导致", "造成", "影响", "关系",
        ],
        "negation_indicators": [            # 否定/反转指示词
            "不是", "没有", "并非", "其实", "实际上", "事实上",
            "相反", "反而", "却", "倒是", "恰恰",
        ],
        "metaphor_indicators": [            # 隐喻/比喻指示词
            "像", "如同", "仿佛", "好比", "就像", "犹如",
            "简直", "堪比", "不亚于", "胜过",
        ],
        "temporal_complexity": [            # 时间复杂性
            "之前", "之后", "同时", "期间", "直到", "自从",
            "曾经", "一直", "最近", "将来", "过去",
        ],
    },
    
    # 回退策略
    "fallback": {
        "on_llm_failure": "rule",           # LLM 失败时：rule（回退规则）/ discard（丢弃）
        "on_parse_failure": "rule",         # 解析失败时
        "retry_count": 1,                   # 重试次数
        "timeout_seconds": 30,              # 超时时间
    },
    
    # API 配置
    "api": {
        "env_key": "OPENAI_API_KEY",        # 环境变量名
        "config_key": "llm_api_key",        # 配置文件键名
        "default_model": "gpt-4o-mini",     # 默认模型（便宜且快）
        "default_base_url": "https://api.openai.com/v1",
    },
}

# ============================================================
# 语义复杂度检测
# ============================================================

def detect_semantic_complexity(content: str) -> Dict[str, Any]:
    """
    检测内容的语义复杂度
    
    返回:
        {
            "is_complex": bool,          # 是否复杂
            "complexity_score": float,   # 复杂度分数 (0-1)
            "reasons": list,             # 复杂原因
            "should_use_llm": bool,      # 是否应该使用 LLM
        }
    """
    config = LLM_INTEGRATION_CONFIG["complexity"]
    reasons = []
    score = 0.0
    
    # 1. 长度检查
    if len(content) < config["min_length_for_check"]:
        return {
            "is_complex": False,
            "complexity_score": 0.0,
            "reasons": ["内容太短"],
            "should_use_llm": False,
        }
    
    # 2. 关系指示词检测
    relation_count = sum(1 for word in config["relation_indicators"] if word in content)
    if relation_count >= 1:  # 降低阈值：1个关系词就加分
        score += 0.2 + (relation_count - 1) * 0.1  # 第一个 0.2，之后每个 +0.1
        reasons.append(f"包含 {relation_count} 个关系指示词")
    
    # 3. 否定/反转检测
    negation_count = sum(1 for word in config["negation_indicators"] if word in content)
    if negation_count >= 1:
        score += 0.25  # 提高否定/反转的权重
        reasons.append(f"包含 {negation_count} 个否定/反转词")
    
    # 4. 隐喻/比喻检测
    metaphor_count = sum(1 for word in config["metaphor_indicators"] if word in content)
    if metaphor_count >= 1:
        score += 0.25
        reasons.append(f"包含 {metaphor_count} 个隐喻/比喻词")
    
    # 5. 时间复杂性检测
    temporal_count = sum(1 for word in config["temporal_complexity"] if word in content)
    if temporal_count >= 2:
        score += 0.15
        reasons.append(f"包含 {temporal_count} 个时间复杂词")
    
    # 6. 多实体检测（简单版：检测人名模式）
    # 中文人名：2-4个汉字
    # 英文人名：首字母大写
    chinese_names = re.findall(r'[\u4e00-\u9fff]{2,4}(?:先生|女士|同学|老师|医生|教授)?', content)
    english_names = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?', content)
    entity_count = len(set(chinese_names)) + len(set(english_names))
    
    if entity_count >= config["entity_count_threshold"]:
        score += 0.25  # 提高多实体的权重
        reasons.append(f"包含 {entity_count} 个可能的实体")
    
    # 7. 句子结构复杂度（简单版：检测标点符号密度）
    punctuation_count = len(re.findall(r'[，。！？；：、]', content))
    if len(content) > 0:
        punct_density = punctuation_count / len(content)
        if punct_density > 0.1:  # 标点密度高
            score += 0.1
            reasons.append("句子结构复杂")
    
    # 8. 问句检测
    if '?' in content or '？' in content or content.endswith('吗') or content.endswith('呢'):
        score += 0.1
        reasons.append("包含疑问")
    
    # 归一化分数
    score = min(score, 1.0)
    
    # 判断是否复杂
    is_complex = score >= 0.4
    
    # 判断是否应该使用 LLM
    should_use_llm = score >= 0.3  # 稍微宽松一点
    
    return {
        "is_complex": is_complex,
        "complexity_score": round(score, 2),
        "reasons": reasons,
        "should_use_llm": should_use_llm,
    }


# ============================================================
# API Key 获取
# ============================================================

def get_api_key(config_dict: Optional[Dict] = None, param_key: Optional[str] = None) -> Optional[str]:
    """
    多源获取 API Key
    
    优先级：参数传入 > 环境变量 > 配置文件
    
    参数:
        config_dict: 配置字典（可选）
        param_key: 直接传入的 API Key（可选）
    
    返回:
        API Key 或 None
    """
    api_config = LLM_INTEGRATION_CONFIG["api"]
    
    # 1. 参数传入（最高优先级）
    if param_key:
        return param_key
    
    # 2. 环境变量
    env_key = os.environ.get(api_config["env_key"])
    if env_key:
        return env_key
    
    # 3. 配置文件
    if config_dict and api_config["config_key"] in config_dict:
        return config_dict[api_config["config_key"]]
    
    return None


# ============================================================
# LLM 调用封装
# ============================================================

def call_llm_with_fallback(
    prompt: str,
    system_prompt: str,
    fallback_result: Any,
    api_key: Optional[str] = None,
    config_dict: Optional[Dict] = None,
    max_tokens: int = 150,
) -> Tuple[Any, str, Dict]:
    """
    带回退机制的 LLM 调用
    
    参数:
        prompt: 用户提示
        system_prompt: 系统提示
        fallback_result: 失败时的回退结果
        api_key: API Key（可选）
        config_dict: 配置字典（可选）
        max_tokens: 最大 token 数
    
    返回:
        (result, method, stats)
        - result: 结果（LLM 结果或回退结果）
        - method: 方法（"llm" 或 "rule_fallback"）
        - stats: 统计信息
    """
    stats = {
        "llm_called": False,
        "llm_success": False,
        "llm_error": None,
        "tokens_used": 0,
        "fallback_used": False,
    }
    
    # 获取 API Key
    key = get_api_key(config_dict, api_key)
    if not key:
        stats["llm_error"] = "API Key not found"
        stats["fallback_used"] = True
        return fallback_result, "rule_fallback", stats
    
    # 获取配置
    api_config = LLM_INTEGRATION_CONFIG["api"]
    base_url = os.environ.get("OPENAI_BASE_URL", api_config["default_base_url"])
    model = os.environ.get("MEMORY_LLM_MODEL", api_config["default_model"])
    timeout = LLM_INTEGRATION_CONFIG["fallback"]["timeout_seconds"]
    
    stats["llm_called"] = True
    
    try:
        import requests
        
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        data = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        
        response = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=data,
            timeout=timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})
            
            stats["llm_success"] = True
            stats["tokens_used"] = usage.get("total_tokens", 0)
            
            return content.strip(), "llm", stats
        else:
            stats["llm_error"] = f"HTTP {response.status_code}: {response.text[:100]}"
            
    except requests.exceptions.Timeout:
        stats["llm_error"] = "Request timeout"
    except requests.exceptions.RequestException as e:
        stats["llm_error"] = f"Request error: {str(e)}"
    except Exception as e:
        stats["llm_error"] = f"Unexpected error: {str(e)}"
    
    # 回退
    stats["fallback_used"] = True
    return fallback_result, "rule_fallback", stats


# ============================================================
# 智能筛选决策
# ============================================================

def should_use_llm_for_filtering(
    content: str,
    rule_importance: float,
    rule_category: str,
) -> Tuple[bool, str]:
    """
    决定是否应该使用 LLM 进行筛选
    
    参数:
        content: 内容
        rule_importance: 规则计算的重要性
        rule_category: 规则计算的分类
    
    返回:
        (should_use_llm, reason)
    """
    config = LLM_INTEGRATION_CONFIG["trigger"]
    
    # 1. 检测语义复杂度
    complexity = detect_semantic_complexity(content)
    
    # 2. 高置信度 + 简单内容 → 信任规则
    if rule_importance >= config["high_confidence_threshold"]:
        if not complexity["is_complex"]:
            return False, "high_confidence_simple"
        elif config["force_llm_on_complex"]:
            return True, f"high_confidence_but_complex: {complexity['reasons']}"
        else:
            return False, "high_confidence_complex_but_not_forced"
    
    # 3. 低置信度 → 检查复杂度
    if rule_importance < config["low_confidence_threshold"]:
        if complexity["should_use_llm"]:
            return True, f"low_confidence_but_complex: {complexity['reasons']}"
        else:
            return False, "low_confidence_simple"
    
    # 4. 不确定区间 → 使用 LLM
    low, high = config["uncertain_range"]
    if low <= rule_importance < high:
        return True, "uncertain_range"
    
    return False, "default_rule"


# ============================================================
# Phase 2 增强：智能重要性筛选
# ============================================================

def smart_filter_segment(
    content: str,
    rule_importance: float,
    rule_category: str,
    api_key: Optional[str] = None,
    config_dict: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    智能筛选单个片段
    
    结合规则和 LLM，返回最终的重要性判断
    
    返回:
        {
            "importance": float,
            "category": str,
            "method": str,           # "rule" / "llm" / "rule_fallback"
            "complexity": dict,      # 复杂度分析
            "llm_stats": dict,       # LLM 调用统计
        }
    """
    # 1. 决定是否使用 LLM
    should_use, reason = should_use_llm_for_filtering(content, rule_importance, rule_category)
    
    result = {
        "importance": rule_importance,
        "category": rule_category,
        "method": "rule",
        "complexity": detect_semantic_complexity(content),
        "llm_stats": None,
        "decision_reason": reason,
    }
    
    if not should_use:
        return result
    
    # 2. 构建 LLM 提示
    system_prompt = """你是一个记忆重要性评估专家。评估用户输入的重要性（0-1），并分类。

分类标准：
- identity_health_safety (0.9-1.0): 身份、健康、安全、过敏、密码、密钥
- preference_relation (0.7-0.9): 偏好、关系、态度、观点
- project_task (0.5-0.7): 项目、任务、目标、计划
- general_fact (0.3-0.5): 一般事实、描述
- temporary (0.1-0.3): 临时信息、闲聊

注意：
1. 如果内容包含健康风险（如过敏），必须给高分
2. 如果内容包含安全信息（如密码），必须给高分
3. 如果内容包含人际关系变化，给中高分
4. 如果内容是简单闲聊，给低分

返回 JSON：{"importance": 0.8, "category": "preference_relation", "reason": "简短理由"}"""

    prompt = f"评估以下内容的重要性：\n\n{content}\n\n返回 JSON："
    
    # 3. 调用 LLM（带回退）
    fallback_result = json.dumps({
        "importance": rule_importance,
        "category": rule_category,
        "reason": "LLM fallback to rule"
    })
    
    llm_response, method, stats = call_llm_with_fallback(
        prompt=prompt,
        system_prompt=system_prompt,
        fallback_result=fallback_result,
        api_key=api_key,
        config_dict=config_dict,
        max_tokens=100,
    )
    
    result["llm_stats"] = stats
    result["method"] = method
    
    # 4. 解析 LLM 结果
    if method == "llm":
        try:
            # 尝试提取 JSON
            json_match = re.search(r'\{[^}]+\}', llm_response)
            if json_match:
                data = json.loads(json_match.group())
                result["importance"] = float(data.get("importance", rule_importance))
                result["category"] = data.get("category", rule_category)
                result["llm_reason"] = data.get("reason", "")
        except (json.JSONDecodeError, ValueError) as e:
            # 解析失败，回退到规则
            result["method"] = "rule_fallback"
            result["parse_error"] = str(e)
    
    return result


# ============================================================
# Phase 3 增强：智能实体提取
# ============================================================

def smart_extract_entities(
    content: str,
    rule_entities: List[str],
    api_key: Optional[str] = None,
    config_dict: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    智能提取实体
    
    如果规则提取的实体为空或内容复杂，使用 LLM 补充
    
    返回:
        {
            "entities": list,
            "method": str,
            "llm_stats": dict,
        }
    """
    complexity = detect_semantic_complexity(content)
    
    result = {
        "entities": rule_entities,
        "method": "rule",
        "complexity": complexity,
        "llm_stats": None,
    }
    
    # 决定是否需要 LLM
    need_llm = False
    reason = ""
    
    if not rule_entities:
        need_llm = True
        reason = "no_rule_entities"
    elif complexity["is_complex"] and len(rule_entities) < 2:
        need_llm = True
        reason = "complex_content_few_entities"
    
    if not need_llm:
        return result
    
    # 构建 LLM 提示
    system_prompt = """你是一个实体提取专家。从文本中提取关键实体。

实体类型：
- 人名（中文/英文）
- 项目名/产品名
- 组织名/公司名
- 地点名
- 专有名词

返回 JSON：{"entities": ["实体1", "实体2"], "types": {"实体1": "person", "实体2": "project"}}"""

    prompt = f"提取以下内容中的实体：\n\n{content}\n\n返回 JSON："
    
    fallback_result = json.dumps({"entities": rule_entities, "types": {}})
    
    llm_response, method, stats = call_llm_with_fallback(
        prompt=prompt,
        system_prompt=system_prompt,
        fallback_result=fallback_result,
        api_key=api_key,
        config_dict=config_dict,
        max_tokens=150,
    )
    
    result["llm_stats"] = stats
    result["method"] = method
    result["decision_reason"] = reason
    
    if method == "llm":
        try:
            json_match = re.search(r'\{[^}]+\}', llm_response)
            if json_match:
                data = json.loads(json_match.group())
                llm_entities = data.get("entities", [])
                # 合并规则和 LLM 的实体
                all_entities = list(set(rule_entities + llm_entities))
                result["entities"] = all_entities
                result["entity_types"] = data.get("types", {})
        except (json.JSONDecodeError, ValueError) as e:
            result["method"] = "rule_fallback"
            result["parse_error"] = str(e)
    
    return result


# ============================================================
# 统计汇总
# ============================================================

class LLMIntegrationStats:
    """LLM 集成统计"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.phase2_calls = 0
        self.phase2_successes = 0
        self.phase2_fallbacks = 0
        self.phase3_calls = 0
        self.phase3_successes = 0
        self.phase3_fallbacks = 0
        self.total_tokens = 0
        self.errors = []
        self.complexity_triggers = 0
    
    def record_phase2(self, stats: Dict):
        if stats and stats.get("llm_called"):
            self.phase2_calls += 1
            if stats.get("llm_success"):
                self.phase2_successes += 1
            if stats.get("fallback_used"):
                self.phase2_fallbacks += 1
            self.total_tokens += stats.get("tokens_used", 0)
            if stats.get("llm_error"):
                self.errors.append(f"Phase2: {stats['llm_error']}")
    
    def record_phase3(self, stats: Dict):
        if stats and stats.get("llm_called"):
            self.phase3_calls += 1
            if stats.get("llm_success"):
                self.phase3_successes += 1
            if stats.get("fallback_used"):
                self.phase3_fallbacks += 1
            self.total_tokens += stats.get("tokens_used", 0)
            if stats.get("llm_error"):
                self.errors.append(f"Phase3: {stats['llm_error']}")
    
    def record_complexity_trigger(self):
        self.complexity_triggers += 1
    
    def summary(self) -> Dict:
        return {
            "phase2": {
                "calls": self.phase2_calls,
                "successes": self.phase2_successes,
                "fallbacks": self.phase2_fallbacks,
            },
            "phase3": {
                "calls": self.phase3_calls,
                "successes": self.phase3_successes,
                "fallbacks": self.phase3_fallbacks,
            },
            "total_tokens": self.total_tokens,
            "complexity_triggers": self.complexity_triggers,
            "errors": self.errors[:5],  # 只保留前 5 个错误
        }
    
    def print_summary(self):
        print("\n📊 LLM 集成统计:")
        print(f"   Phase 2 (筛选): {self.phase2_calls} 调用, {self.phase2_successes} 成功, {self.phase2_fallbacks} 回退")
        print(f"   Phase 3 (提取): {self.phase3_calls} 调用, {self.phase3_successes} 成功, {self.phase3_fallbacks} 回退")
        print(f"   总 Token: {self.total_tokens}")
        print(f"   复杂度触发: {self.complexity_triggers} 次")
        if self.errors:
            print(f"   ⚠️  错误: {len(self.errors)} 个")
            for err in self.errors[:3]:
                print(f"      - {err}")


# 全局统计实例
INTEGRATION_STATS = LLMIntegrationStats()
