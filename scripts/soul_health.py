#!/usr/bin/env python3
"""
Soul Health Monitor v1.0
基于 BMAM (Li et al. 2026) Soul Erosion 理论的记忆健康监控

S(M) = α·T(M) + β·C(M) + γ·I(M)
- T: Temporal Coherence  时序一致性
- C: Semantic Consistency 语义一致性
- I: Identity Preservation 身份保持
"""

import json
import os
from datetime import datetime
from pathlib import Path


def get_memory_dir():
    workspace = os.environ.get("WORKSPACE", "/root/.openclaw/workspace")
    return Path(workspace) / "memory"


def load_jsonl(path):
    if not Path(path).exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    pass
    return records


def compute_temporal_coherence(facts):
    """
    T: 时序一致性
    衡量 facts 中 timestamp/created 字段完整率 + 时序引擎覆盖率
    """
    if not facts:
        return 0.5
    has_timestamp = sum(1 for f in facts if f.get("timestamp") or f.get("created"))
    return has_timestamp / len(facts)


def compute_semantic_consistency(facts):
    """
    C: 语义一致性
    衡量冲突降权比例（越低越好）
    """
    if not facts:
        return 1.0
    conflict_count = sum(1 for f in facts if f.get("conflict_downgraded"))
    superseded_count = sum(1 for f in facts if f.get("superseded"))
    bad = conflict_count + superseded_count
    return 1.0 - (bad / len(facts))


def compute_identity_preservation(facts):
    """
    I: 身份保持
    衡量 identity facts 的存活质量
    - identity facts 数量是否足够
    - identity facts 的平均 importance/score 是否健康
    """
    identity_facts = [f for f in facts if f.get("is_identity")]

    if not identity_facts:
        # 没有 identity 标签，检查是否有高 importance 的 facts 作为替代
        high_imp = [f for f in facts if f.get("importance", 0) >= 0.8]
        if not high_imp:
            return 0.3  # 没有任何身份信息，风险高
        avg_score = sum(f.get("score", f.get("importance", 0.5)) for f in high_imp) / len(high_imp)
        return min(0.7, avg_score)  # 没有明确标签，最高 0.7

    avg_importance = sum(f.get("importance", 0.5) for f in identity_facts) / len(identity_facts)
    avg_score = sum(f.get("score", f.get("importance", 0.5)) for f in identity_facts) / len(identity_facts)

    # 综合：importance 权重 0.4，score 权重 0.6
    return 0.4 * avg_importance + 0.6 * avg_score


def compute_soul_score(memory_dir=None):
    """
    计算完整 Soul Score
    返回详细报告 dict
    """
    if memory_dir is None:
        memory_dir = get_memory_dir()
    memory_dir = Path(memory_dir)

    facts = load_jsonl(memory_dir / "layer2/active/facts.jsonl")
    beliefs = load_jsonl(memory_dir / "layer2/active/beliefs.jsonl")
    summaries = load_jsonl(memory_dir / "layer2/active/summaries.jsonl")
    all_memories = facts + beliefs + summaries

    # 三维评分
    t_score = compute_temporal_coherence(facts)
    c_score = compute_semantic_consistency(facts)
    i_score = compute_identity_preservation(facts)

    # 加权：identity 最重要（BMAM 建议根据场景调整）
    alpha, beta, gamma = 0.25, 0.35, 0.40
    soul_score = alpha * t_score + beta * c_score + gamma * i_score

    # 风险等级
    if soul_score >= 0.80:
        risk = "LOW"
        risk_emoji = "🟢"
    elif soul_score >= 0.60:
        risk = "MEDIUM"
        risk_emoji = "🟡"
    else:
        risk = "HIGH"
        risk_emoji = "🔴"

    # 统计
    identity_count = sum(1 for f in facts if f.get("is_identity"))
    conflict_count = sum(1 for f in facts if f.get("conflict_downgraded"))

    return {
        "soul_score": round(soul_score, 3),
        "temporal_coherence": round(t_score, 3),
        "semantic_consistency": round(c_score, 3),
        "identity_preservation": round(i_score, 3),
        "risk": risk,
        "risk_emoji": risk_emoji,
        "stats": {
            "total_facts": len(facts),
            "total_beliefs": len(beliefs),
            "total_summaries": len(summaries),
            "identity_facts": identity_count,
            "conflict_facts": conflict_count,
        },
        "computed_at": datetime.utcnow().isoformat() + "Z",
    }


def print_soul_report(report):
    print(f"\n{'='*40}")
    print(f"🧠 Soul Health Report")
    print(f"{'='*40}")
    print(f"  总分:  {report['soul_score']:.3f}  {report['risk_emoji']} {report['risk']}")
    print(f"  T (时序一致性):   {report['temporal_coherence']:.3f}")
    print(f"  C (语义一致性):   {report['semantic_consistency']:.3f}")
    print(f"  I (身份保持):     {report['identity_preservation']:.3f}")
    print(f"  ---")
    s = report["stats"]
    print(f"  Facts: {s['total_facts']} (identity: {s['identity_facts']}, conflict: {s['conflict_facts']})")
    print(f"  Beliefs: {s['total_beliefs']}  Summaries: {s['total_summaries']}")
    print(f"{'='*40}\n")


if __name__ == "__main__":
    report = compute_soul_score()
    print_soul_report(report)
