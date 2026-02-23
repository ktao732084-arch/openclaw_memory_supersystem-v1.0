#!/usr/bin/env python3
"""
Memory System v1.4.0 - 时序查询引擎
TemporalQueryEngine + FactEvolutionTracker + EvidenceTracker

对齐 LongMemEval 时序推理要求
"""

import json
import math
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ============================================================
# TemporalQueryEngine - 时序查询引擎
# ============================================================

# 时间表达式模式（中文）
TEMPORAL_PATTERNS = [
    # 相对时间
    (r"上次|上一次|最近一次", lambda now: (now - timedelta(days=7), now)),
    (r"昨天",                  lambda now: (now - timedelta(days=1), now - timedelta(days=1))),
    (r"前天",                  lambda now: (now - timedelta(days=2), now - timedelta(days=2))),
    (r"上周|上个星期",          lambda now: (now - timedelta(weeks=1), now - timedelta(days=1))),
    (r"上个月",                lambda now: (now - timedelta(days=30), now - timedelta(days=1))),
    (r"上个季度",              lambda now: (now - timedelta(days=90), now - timedelta(days=1))),
    (r"去年",                  lambda now: (now - timedelta(days=365), now - timedelta(days=1))),
    (r"今天|今日",             lambda now: (now.replace(hour=0, minute=0, second=0), now)),
    (r"本周|这周",             lambda now: (now - timedelta(days=now.weekday()), now)),
    (r"本月|这个月",           lambda now: (now.replace(day=1), now)),
    # 数字相对时间
    (r"(\d+)\s*天前",          lambda now, m: (now - timedelta(days=int(m.group(1))), now - timedelta(days=int(m.group(1))))),
    (r"(\d+)\s*周前",          lambda now, m: (now - timedelta(weeks=int(m.group(1))), now - timedelta(weeks=int(m.group(1))))),
    (r"(\d+)\s*个月前",        lambda now, m: (now - timedelta(days=30 * int(m.group(1))), now - timedelta(days=30 * int(m.group(1))))),
    (r"(\d+)\s*年前",          lambda now, m: (now - timedelta(days=365 * int(m.group(1))), now - timedelta(days=365 * int(m.group(1))))),
    # 最近 N
    (r"最近\s*(\d+)\s*天",     lambda now, m: (now - timedelta(days=int(m.group(1))), now)),
    (r"最近\s*(\d+)\s*周",     lambda now, m: (now - timedelta(weeks=int(m.group(1))), now)),
    (r"最近\s*(\d+)\s*个月",   lambda now, m: (now - timedelta(days=30 * int(m.group(1))), now)),
]


class TemporalQueryEngine:
    """时序查询引擎"""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def parse_temporal_expression(self, query: str, now: datetime = None) -> Optional[Tuple[datetime, datetime]]:
        """
        解析查询中的时间表达式，返回 (start, end) 时间范围
        没有时间表达式返回 None
        """
        now = now or datetime.utcnow()

        for pattern, time_func in TEMPORAL_PATTERNS:
            match = re.search(pattern, query)
            if match:
                try:
                    # 有捕获组的 pattern（数字相对时间）
                    if match.lastindex:
                        start, end = time_func(now, match)
                    else:
                        start, end = time_func(now)
                    return start, end
                except Exception:
                    continue

        return None

    def search_by_time_range(
        self,
        start: datetime,
        end: datetime,
        mem_type: str = None,
        limit: int = 20,
    ) -> List[Dict]:
        """按时间范围查询记忆"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            sql = """
                SELECT * FROM memories
                WHERE state = 0
                  AND timestamp >= ?
                  AND timestamp <= ?
            """
            params = [start.isoformat(), end.isoformat()]

            if mem_type:
                sql += " AND type = ?"
                params.append(mem_type)

            sql += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def apply_time_decay(self, memories: List[Dict], now: datetime = None, lambda_decay: float = 0.005) -> List[Dict]:
        """
        应用时间衰减评分
        γ = e^(-λΔt)，Δt 单位为天
        """
        now = now or datetime.utcnow()

        for m in memories:
            ts_str = m.get("timestamp") or m.get("created")
            if not ts_str:
                m["time_decayed_score"] = m.get("score", 0.5)
                continue
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00").replace("+00:00", ""))
                days_elapsed = max((now - ts).days, 0)
                decay = math.exp(-lambda_decay * days_elapsed)
                m["time_decayed_score"] = round(m.get("score", 0.5) * decay, 4)
            except Exception:
                m["time_decayed_score"] = m.get("score", 0.5)

        return memories

    def temporal_search(self, query: str, db_path: Path = None, limit: int = 20) -> Dict:
        """
        时序感知检索：自动解析时间表达式，返回时间范围内的记忆
        """
        db_path = db_path or self.db_path
        now = datetime.utcnow()

        time_range = self.parse_temporal_expression(query, now)

        if time_range:
            start, end = time_range
            # 扩展 end 到当天结束
            end = end.replace(hour=23, minute=59, second=59)
            results = self.search_by_time_range(start, end, limit=limit)
            results = self.apply_time_decay(results, now)
            return {
                "has_temporal": True,
                "time_range": {"start": start.isoformat(), "end": end.isoformat()},
                "results": results,
                "count": len(results),
            }
        else:
            return {
                "has_temporal": False,
                "time_range": None,
                "results": [],
                "count": 0,
            }


# ============================================================
# FactEvolutionTracker - 事实演变追踪
# ============================================================

class FactEvolutionTracker:
    """事实演变追踪器：追踪实体属性的历史变化"""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def get_evolution(self, entity: str, attribute_hint: str = None) -> List[Dict]:
        """
        获取实体相关记忆的演变历史（按时间排序）

        Args:
            entity: 实体名称（如 "Ktao"）
            attribute_hint: 属性关键词（如 "住在"、"学校"），None 则返回所有
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            sql = """
                SELECT m.* FROM memories m
                JOIN memory_entities e ON m.id = e.memory_id
                WHERE e.entity = ?
                  AND m.type = 'fact'
                ORDER BY m.timestamp ASC
            """
            cursor.execute(sql, [entity])
            rows = [dict(r) for r in cursor.fetchall()]

            if attribute_hint:
                rows = [r for r in rows if attribute_hint in r.get("content", "")]

            # 构建演变链
            evolution = []
            for i, row in enumerate(rows):
                entry = {
                    "memory_id": row["id"],
                    "content": row["content"],
                    "valid_from": row.get("timestamp") or row.get("created"),
                    "valid_to": rows[i + 1].get("timestamp") if i + 1 < len(rows) else None,
                    "superseded": bool(row.get("superseded")),
                    "confidence": row.get("confidence", 1.0),
                }
                evolution.append(entry)

            return evolution
        finally:
            conn.close()

    def get_current_value(self, entity: str, attribute_hint: str, at_time: datetime = None) -> Optional[Dict]:
        """
        获取指定时间点的属性值（默认当前时间）
        """
        at_time = at_time or datetime.utcnow()
        evolution = self.get_evolution(entity, attribute_hint)

        if not evolution:
            return None

        # 找到 at_time 时有效的记忆
        for item in reversed(evolution):
            valid_from_str = item.get("valid_from")
            if not valid_from_str:
                continue
            try:
                valid_from = datetime.fromisoformat(valid_from_str.replace("Z", ""))
                if valid_from <= at_time:
                    return item
            except Exception:
                continue

        return evolution[0] if evolution else None

    def summarize_evolution(self, entity: str, attribute_hint: str = None) -> str:
        """生成演变摘要文本"""
        evolution = self.get_evolution(entity, attribute_hint)
        if not evolution:
            return f"未找到 {entity} 的相关记忆"

        lines = [f"{entity} 的记忆演变（共 {len(evolution)} 条）："]
        for i, item in enumerate(evolution):
            valid_from = item["valid_from"] or "未知时间"
            valid_to = item["valid_to"] or "至今"
            lines.append(f"  {i+1}. [{valid_from[:10]} → {valid_to[:10] if item['valid_to'] else '至今'}] {item['content']}")

        return "\n".join(lines)


# ============================================================
# EvidenceTracker - 证据追踪
# ============================================================

class EvidenceTracker:
    """证据追踪器：追踪记忆的来源证据，支持 LoCoMo 格式输出"""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def get_evidence(self, memory_id: str) -> Optional[Dict]:
        """获取单条记忆的证据"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT * FROM memories WHERE id = ?", [memory_id])
            row = cursor.fetchone()
            if not row:
                return None

            row = dict(row)
            return {
                "memory_id": row["id"],
                "content": row["content"],
                "session_id": row.get("session_id"),
                "source_turn": row.get("source_turn"),
                "source_quote": row.get("source_quote"),
                "timestamp": row.get("timestamp") or row.get("created"),
                "ownership": row.get("ownership", "user"),
                "confidence": row.get("confidence", 1.0),
            }
        finally:
            conn.close()

    def get_evidence_chain(self, memory_id: str) -> List[Dict]:
        """
        获取完整证据链（包括被取代的旧记忆）
        """
        chain = []
        visited = set()

        def _traverse(mid):
            if mid in visited:
                return
            visited.add(mid)

            evidence = self.get_evidence(mid)
            if not evidence:
                return
            chain.append(evidence)

            # 追溯 supersedes 链
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT supersedes FROM memories WHERE id = ?", [mid])
                row = cursor.fetchone()
                if row and row[0]:
                    try:
                        old_ids = json.loads(row[0])
                        for old_id in old_ids:
                            _traverse(old_id)
                    except Exception:
                        pass
            finally:
                conn.close()

        _traverse(memory_id)
        return chain

    def format_locomo(self, memory_id: str) -> Dict:
        """
        格式化为 LoCoMo 评测集要求的输出格式
        {answer, evidence_ids, confidence}
        """
        chain = self.get_evidence_chain(memory_id)
        if not chain:
            return {"answer": "", "evidence_ids": [], "confidence": 0.0}

        primary = chain[0]
        evidence_ids = [
            e["source_turn"] for e in chain
            if e.get("source_turn") is not None
        ]

        return {
            "answer": primary["content"],
            "evidence_ids": evidence_ids,
            "confidence": primary["confidence"],
            "source_quote": primary.get("source_quote"),
        }


# ============================================================
# 工厂函数
# ============================================================

def create_temporal_engine(memory_dir: Path) -> TemporalQueryEngine:
    db_path = memory_dir / "layer2" / "memories.db"
    return TemporalQueryEngine(db_path)

def create_evolution_tracker(memory_dir: Path) -> FactEvolutionTracker:
    db_path = memory_dir / "layer2" / "memories.db"
    return FactEvolutionTracker(db_path)

def create_evidence_tracker(memory_dir: Path) -> EvidenceTracker:
    db_path = memory_dir / "layer2" / "memories.db"
    return EvidenceTracker(db_path)
