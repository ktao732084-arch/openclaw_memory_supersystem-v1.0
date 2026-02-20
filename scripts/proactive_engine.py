#!/usr/bin/env python3
"""
Proactive Memory Engine v1.0 - 主动记忆引擎

功能:
- 持续意图监控：识别用户交互意图模式
- 上下文预测：预测下一步需要的上下文并预加载
- 主动建议生成：根据意图生成主动建议

参考: memU 主动记忆架构
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class Intent:
    """用户意图"""

    type: str
    topic: str
    confidence: float
    started_at: datetime
    last_active: datetime
    message_count: int = 0
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "topic": self.topic,
            "confidence": self.confidence,
            "started_at": self.started_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "message_count": self.message_count,
            "keywords": self.keywords,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Intent":
        return cls(
            type=data["type"],
            topic=data["topic"],
            confidence=data["confidence"],
            started_at=datetime.fromisoformat(data["started_at"]),
            last_active=datetime.fromisoformat(data["last_active"]),
            message_count=data.get("message_count", 0),
            keywords=data.get("keywords", []),
        )


@dataclass
class Suggestion:
    """主动建议"""

    type: str
    content: str
    priority: float
    triggered_by: str
    created_at: datetime
    intent_topic: str = ""

    def to_dict(self) -> Dict:
        return {
            "type": self.type,
            "content": self.content,
            "priority": self.priority,
            "triggered_by": self.triggered_by,
            "created_at": self.created_at.isoformat(),
            "intent_topic": self.intent_topic,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Suggestion":
        return cls(
            type=data["type"],
            content=data["content"],
            priority=data["priority"],
            triggered_by=data["triggered_by"],
            created_at=datetime.fromisoformat(data["created_at"]),
            intent_topic=data.get("intent_topic", ""),
        )


class ProactiveMemoryEngine:
    """主动记忆引擎"""

    INTENT_PATTERNS = {
        "research": {
            "keywords": ["研究", "论文", "分析", "调研", "文献", "实验", "数据", "探索", "调查", "学习"],
            "weight": 1.0,
        },
        "planning": {
            "keywords": ["计划", "安排", "日程", "会议", "截止", "deadline", "提醒", "明天", "下周", "任务"],
            "weight": 0.9,
        },
        "learning": {
            "keywords": ["学习", "教程", "课程", "理解", "怎么", "如何", "原理", "入门", "基础", "进阶"],
            "weight": 0.8,
        },
        "coding": {
            "keywords": ["代码", "开发", "实现", "bug", "功能", "API", "调试", "编程", "程序", "脚本"],
            "weight": 0.85,
        },
        "communication": {
            "keywords": ["发消息", "回复", "联系", "邮件", "通知", "沟通", "交流", "反馈"],
            "weight": 0.7,
        },
        "creative": {"keywords": ["设计", "创作", "写", "画", "构思", "创意", "想法", "灵感"], "weight": 0.75},
        "problem_solving": {
            "keywords": ["问题", "解决", "修复", "错误", "异常", "故障", "排查", "诊断"],
            "weight": 0.85,
        },
    }

    SUGGESTION_TEMPLATES = {
        "research": [
            "需要我帮你整理之前关于 {topic} 的研究笔记吗？",
            "我记得你之前提到过相关内容，要回顾一下吗？",
            "要不要我帮你搜索更多关于 {topic} 的资料？",
        ],
        "planning": [
            "你有一个任务即将到期：{topic}",
            "需要我帮你安排日程吗？",
            "记得 {topic} 快到了，需要提前准备吗？",
        ],
        "learning": [
            "关于 {topic}，我之前帮你总结过一些要点，要看吗？",
            "要不要我帮你生成一份 {topic} 的学习计划？",
        ],
        "coding": [
            "我记得你之前在 {topic} 中遇到过类似问题，要看解决方案吗？",
            "需要我帮你检查这段代码的潜在问题吗？",
        ],
        "communication": [
            "需要我帮你起草关于 {topic} 的消息吗？",
            "要不要回顾一下之前的沟通记录？",
        ],
        "creative": [
            "关于 {topic}，我有一些想法可以分享，想听吗？",
            "要不要我帮你头脑风暴一下？",
        ],
        "problem_solving": [
            "之前遇到过类似的 {topic} 问题，要看当时的解决方案吗？",
            "需要我帮你分析问题的可能原因吗？",
        ],
    }

    DEFAULT_CONFIG = {
        "enabled": True,
        "intent_window_size": 10,
        "intent_timeout_minutes": 30,
        "suggestion_interval_seconds": 60,
        "min_confidence_for_suggestion": 0.5,
        "max_suggestions_per_hour": 5,
        "cache_ttl_minutes": 5,
        "proactive_threshold_confidence": 0.7,
        "proactive_threshold_messages": 3,
    }

    def __init__(self, memory_dir: Optional[Path] = None, config: Optional[Dict] = None):
        self.memory_dir = memory_dir or Path("memory")
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

        self.active_intents: Dict[str, Intent] = {}
        self.intent_history: List[Intent] = []
        self.memory_cache: Dict[str, Tuple[datetime, List[Dict]]] = {}
        self.suggestion_queue: List[Suggestion] = []
        self.recent_messages: List[Dict] = []
        self.message_window_size = self.config["intent_window_size"]

        self._router_search = None
        self._add_to_pending = None
        self._load_memory_functions()

        self._stats = {
            "messages_processed": 0,
            "intents_detected": 0,
            "suggestions_generated": 0,
            "memories_preloaded": 0,
        }

    def _load_memory_functions(self):
        """动态加载记忆系统函数"""
        try:
            import sys

            scripts_dir = Path(__file__).parent
            if str(scripts_dir) not in sys.path:
                sys.path.insert(0, str(scripts_dir))

            from memory import add_to_pending, router_search

            self._router_search = router_search
            self._add_to_pending = add_to_pending
        except ImportError:
            pass

    def process_message(self, message: str, role: str = "user") -> Dict:
        """
        处理消息，返回分析结果

        Args:
            message: 消息内容
            role: 角色 (user/assistant)

        Returns:
            {
                "intent": Intent,
                "suggestions": List[Suggestion],
                "preloaded_memories": List[Dict]
            }
        """
        if not self.config["enabled"]:
            return {"intent": None, "suggestions": [], "preloaded_memories": []}

        self.recent_messages.append({"content": message, "role": role, "timestamp": datetime.now()})
        if len(self.recent_messages) > self.message_window_size:
            self.recent_messages.pop(0)

        intent = self._detect_intent(message)
        self._update_active_intent(intent)
        preloaded = self._preload_memories(intent)
        suggestions = self._generate_suggestions(intent)

        self._stats["messages_processed"] += 1
        if intent.type != "general":
            self._stats["intents_detected"] += 1
        self._stats["suggestions_generated"] += len(suggestions)
        self._stats["memories_preloaded"] += len(preloaded)

        return {
            "intent": intent,
            "suggestions": suggestions,
            "preloaded_memories": preloaded,
        }

    def _detect_intent(self, message: str) -> Intent:
        """检测消息意图"""
        message_lower = message.lower()
        scores = {}
        matched_keywords = {}

        for intent_type, config in self.INTENT_PATTERNS.items():
            score = 0
            keywords = []
            for kw in config["keywords"]:
                if kw in message_lower or kw in message:
                    score += config["weight"]
                    keywords.append(kw)

            scores[intent_type] = score
            matched_keywords[intent_type] = keywords

        best_type = max(scores, key=scores.get) if max(scores.values()) > 0 else "general"
        best_score = scores.get(best_type, 0)

        topic = self._extract_topic(message, matched_keywords.get(best_type, []))

        return Intent(
            type=best_type,
            topic=topic,
            confidence=min(best_score / 3.0, 1.0),
            started_at=datetime.now(),
            last_active=datetime.now(),
            message_count=1,
            keywords=matched_keywords.get(best_type, []),
        )

    def _extract_topic(self, message: str, keywords: List[str]) -> str:
        """提取主题"""
        if keywords:
            return keywords[0]

        words = re.findall(r"[\u4e00-\u9fa5]{2,}|[A-Za-z]{3,}", message)
        return words[0] if words else "未知主题"

    def _update_active_intent(self, new_intent: Intent):
        """更新活跃意图"""
        intent_key = f"{new_intent.type}:{new_intent.topic}"

        if intent_key in self.active_intents:
            existing = self.active_intents[intent_key]
            existing.last_active = datetime.now()
            existing.message_count += 1
            existing.confidence = min(existing.confidence + 0.1, 1.0)
            existing.keywords.extend(new_intent.keywords)
            existing.keywords = list(set(existing.keywords))
        else:
            self.active_intents[intent_key] = new_intent

        cutoff = datetime.now() - timedelta(minutes=self.config["intent_timeout_minutes"])
        expired = [k for k, v in self.active_intents.items() if v.last_active < cutoff]
        for k in expired:
            self.intent_history.append(self.active_intents[k])
            del self.active_intents[k]

    def _preload_memories(self, intent: Intent) -> List[Dict]:
        """预加载相关记忆"""
        if intent.type == "general":
            return []

        cache_key = f"{intent.type}:{intent.topic}"

        if cache_key in self.memory_cache:
            cached_at, memories = self.memory_cache[cache_key]
            if datetime.now() - cached_at < timedelta(minutes=self.config["cache_ttl_minutes"]):
                return memories

        if self._router_search:
            query = f"{intent.topic} {' '.join(intent.keywords[:3])}"
            result = self._router_search(query, self.memory_dir)
            memories = result.get("results", [])[:5]
        else:
            memories = self._fallback_search(intent)

        self.memory_cache[cache_key] = (datetime.now(), memories)
        return memories

    def _fallback_search(self, intent: Intent) -> List[Dict]:
        """回退搜索：基于文件的关键词搜索"""
        results = []
        try:
            for mem_type in ["facts", "beliefs", "summaries"]:
                path = self.memory_dir / f"layer2/active/{mem_type}.jsonl"
                if not path.exists():
                    continue

                with open(path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                            content = record.get("content", "").lower()
                            score = 0
                            for kw in intent.keywords:
                                if kw.lower() in content:
                                    score += 1
                            if intent.topic.lower() in content:
                                score += 2

                            if score > 0:
                                record["match_score"] = score
                                results.append(record)
                        except json.JSONDecodeError:
                            continue

            results.sort(key=lambda x: x.get("match_score", 0), reverse=True)
            return results[:5]
        except Exception:
            return []

    def _generate_suggestions(self, intent: Intent) -> List[Suggestion]:
        """生成主动建议"""
        suggestions = []

        if intent.confidence < self.config["min_confidence_for_suggestion"]:
            return suggestions

        templates = self.SUGGESTION_TEMPLATES.get(intent.type, [])

        for template in templates[:2]:
            content = template.format(
                topic=intent.topic,
                task=intent.topic,
                event=intent.topic,
                project=intent.topic,
            )

            suggestion = Suggestion(
                type="context",
                content=content,
                priority=intent.confidence,
                triggered_by=intent.type,
                created_at=datetime.now(),
                intent_topic=intent.topic,
            )
            suggestions.append(suggestion)

        self.suggestion_queue.extend(suggestions)
        return suggestions

    def get_next_suggestion(self) -> Optional[Suggestion]:
        """获取下一个待处理的建议"""
        if not self.suggestion_queue:
            return None

        self.suggestion_queue.sort(key=lambda x: x.priority, reverse=True)
        return self.suggestion_queue.pop(0)

    def get_active_context(self) -> Dict:
        """获取当前活跃上下文"""
        return {
            "active_intents": [
                i.to_dict()
                if hasattr(i, "to_dict")
                else {"type": i.type, "topic": i.topic, "confidence": i.confidence, "message_count": i.message_count}
                for i in sorted(self.active_intents.values(), key=lambda x: x.last_active, reverse=True)[:3]
            ],
            "recent_topics": [m["content"][:50] for m in self.recent_messages[-5:]],
            "pending_suggestions": len(self.suggestion_queue),
            "stats": self._stats.copy(),
        }

    def should_proactive_act(self) -> Tuple[bool, str]:
        """
        判断是否应该主动行动

        Returns:
            (should_act, reason)
        """
        for intent in self.active_intents.values():
            if (
                intent.confidence > self.config["proactive_threshold_confidence"]
                and intent.message_count >= self.config["proactive_threshold_messages"]
            ):
                return True, f"用户持续关注 {intent.topic}"

        for msg in self.recent_messages:
            if any(kw in msg["content"] for kw in ["明天", "下周", "截止", "到期", "deadline"]):
                return True, "检测到时间敏感内容"

        if self.suggestion_queue:
            return True, "有待处理的建议"

        return False, ""

    def clear_expired_suggestions(self):
        """清理过期建议（超过 30 分钟）"""
        cutoff = datetime.now() - timedelta(minutes=30)
        self.suggestion_queue = [s for s in self.suggestion_queue if s.created_at > cutoff]

    def reset(self):
        """重置引擎状态"""
        self.active_intents.clear()
        self.suggestion_queue.clear()
        self.recent_messages.clear()
        self.memory_cache.clear()
        self._stats = {
            "messages_processed": 0,
            "intents_detected": 0,
            "suggestions_generated": 0,
            "memories_preloaded": 0,
        }

    def save_state(self, path: Optional[Path] = None):
        """保存引擎状态到文件"""
        if path is None:
            path = self.memory_dir / "state" / "proactive_state.json"

        path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "active_intents": {k: v.to_dict() for k, v in self.active_intents.items()},
            "suggestion_queue": [s.to_dict() for s in self.suggestion_queue],
            "stats": self._stats,
            "config": self.config,
            "saved_at": datetime.now().isoformat(),
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

    def load_state(self, path: Optional[Path] = None):
        """从文件加载引擎状态"""
        if path is None:
            path = self.memory_dir / "state" / "proactive_state.json"

        if not path.exists():
            return False

        try:
            with open(path, encoding="utf-8") as f:
                state = json.load(f)

            self.active_intents = {k: Intent.from_dict(v) for k, v in state.get("active_intents", {}).items()}
            self.suggestion_queue = [Suggestion.from_dict(s) for s in state.get("suggestion_queue", [])]
            self._stats = state.get("stats", self._stats)
            return True
        except Exception:
            return False

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            **self._stats,
            "active_intents_count": len(self.active_intents),
            "pending_suggestions": len(self.suggestion_queue),
            "recent_messages": len(self.recent_messages),
        }


def create_engine(memory_dir: Optional[Path] = None, config: Optional[Dict] = None) -> ProactiveMemoryEngine:
    """工厂函数：创建主动记忆引擎实例"""
    return ProactiveMemoryEngine(memory_dir=memory_dir, config=config)
