#!/usr/bin/env python3
"""
Memory System v1.1 - 新增配置
"""

from datetime import datetime, timedelta
import re
import math

# ============================================================
# v1.1 新增配置
# ============================================================

# 三级漏斗配置
FUNNEL_CONFIG = {
    # 第一级：强匹配池（0 Token）
    "tier1_patterns": {
        "permanent": [
            r"我叫|我是|我的名字",
            r"过敏|疾病|健康问题",
            r"喜欢|讨厌|偏好",
            r"家人|父母|兄弟|姐妹"
        ],
        "task_immediate": [
            r"(今天|今晚|现在|马上|立刻).*(做|去|完成|提交)",
            r"\d{1,2}[点时].*(会议|开会|见面)"
        ],
        "task_short": [
            r"(明天|后天|一会儿|待会).*(做|去|完成|提交)"
        ]
    },
    
    # 第二级：LLM 介入阈值
    "tier2_threshold": {
        "lower": 0.35,
        "upper": 0.70
    },
    
    # 第三级：实体热度追踪
    "tier3_entity": {
        "default_ttl_days": 3,
        "reactivation_extend": 3,
        "max_ttl_days": 14
    }
}

# 访问日志加成配置
ACCESS_BOOST_CONFIG = {
    "coefficient": 0.2,
    "max_boost": 0.5,
    "log_base": "natural",
    "decay_factor": 0.95,
    "recent_days": 7,  # v1.1.5: 只计算最近 N 天的访问
    
    "access_weights": {
        "retrieval": 1.0,
        "used_in_response": 2.0,
        "user_mentioned": 3.0
    }
}

# 时间敏感配置
TIME_SENSITIVITY_CONFIG = {
    "immediate": {
        "keywords": ["今天", "今晚", "现在", "马上", "立刻"],
        "expires_hours": 12
    },
    "short_term": {
        "keywords": ["明天", "后天", "一会儿", "待会"],
        "expires_days": 2
    },
    "medium_term": {
        "keywords": ["这周", "下周", "最近"],
        "expires_days": 10
    },
    "long_term": {
        "keywords": ["这个月", "下个月"],
        "expires_days": 35
    },
    "specific_time": {
        "pattern": r"\d{1,2}[点时]",
        "action_keywords": ["会议", "开会", "见面", "约", "到"],
        "expires_after_hours": 2
    }
}

# 衰减与访问保护配置
DECAY_WITH_ACCESS_CONFIG = {
    "base_decay": {
        "fact": 0.008,
        "belief": 0.07,
        "summary": 0.025
    },
    
    "access_protection": {
        "within_3_days": 0.99,
        "within_7_days": 0.97,
        "within_14_days": 0.95,
        "beyond_14_days": 1.0
    }
}

# 动作词列表（用于第三级追踪）
ACTION_VERBS = [
    "做", "去", "完成", "提交", "开始", "结束", "处理", "解决",
    "写", "读", "看", "听", "说", "想", "买", "卖", "吃", "喝"
]
