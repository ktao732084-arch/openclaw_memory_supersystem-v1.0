#!/usr/bin/env python3
"""
Memory System v1.5.2 - TF-IDF 向量引擎 + RRF 混合检索

设计原则：
- 零依赖外部 API，完全离线
- char-level TF-IDF，天然支持中文
- 增量更新索引（只重建有变化时）
- RRF (Reciprocal Rank Fusion) 合并多路检索结果
"""

from __future__ import annotations

import hashlib
import json
import pickle
import re
from pathlib import Path
from typing import Optional


def _get_index_path(memory_dir: Path) -> Path:
    return memory_dir / "layer2/index/tfidf_index.pkl"


def _get_checksum_path(memory_dir: Path) -> Path:
    return memory_dir / "layer2/index/tfidf_checksum.txt"


def _compute_facts_checksum(memory_dir: Path) -> str:
    """计算 facts/beliefs/summaries 的内容 checksum，用于判断是否需要重建索引"""
    h = hashlib.md5()
    for mem_type in ["facts", "beliefs", "summaries"]:
        path = memory_dir / f"layer2/active/{mem_type}.jsonl"
        if path.exists():
            h.update(path.read_bytes())
    return h.hexdigest()


def _load_all_records(memory_dir: Path) -> list[dict]:
    records = []
    for mem_type in ["facts", "beliefs", "summaries"]:
        path = memory_dir / f"layer2/active/{mem_type}.jsonl"
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                if "type" not in r:
                    r["type"] = mem_type.rstrip("s")
                records.append(r)
            except Exception:
                pass
    return records


def build_tfidf_index(memory_dir: Path, force: bool = False) -> Optional[dict]:
    """
    构建或加载 TF-IDF 索引

    返回 {"vectorizer": ..., "matrix": ..., "ids": [...], "records": [...]}
    """
    from sklearn.feature_extraction.text import TfidfVectorizer

    index_path = _get_index_path(memory_dir)
    checksum_path = _get_checksum_path(memory_dir)
    current_checksum = _compute_facts_checksum(memory_dir)

    # 检查是否可以复用缓存
    if not force and index_path.exists() and checksum_path.exists():
        if checksum_path.read_text().strip() == current_checksum:
            try:
                with open(index_path, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass

    # 重建索引
    records = _load_all_records(memory_dir)
    if not records:
        return None

    texts = [r.get("content", "") for r in records]
    ids = [r["id"] for r in records]

    # char-level analyzer，支持中文，analyzer="char_wb" 效果更好
    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(2, 4),
        max_features=20000,
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(texts)

    index = {
        "vectorizer": vectorizer,
        "matrix": matrix,
        "ids": ids,
        "records": records,
    }

    # 保存
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "wb") as f:
        pickle.dump(index, f)
    checksum_path.write_text(current_checksum)

    return index


def tfidf_search(query: str, memory_dir: Path, top_k: int = 20) -> list[dict]:
    """
    TF-IDF 语义检索

    返回格式与 keyword_search / entity_search 一致
    """
    import numpy as np

    index = build_tfidf_index(memory_dir)
    if index is None:
        return []

    try:
        vectorizer = index["vectorizer"]
        matrix = index["matrix"]
        ids = index["ids"]
        records = index["records"]

        query_vec = vectorizer.transform([query])
        # 余弦相似度
        scores = (matrix @ query_vec.T).toarray().flatten()

        top_indices = scores.argsort()[::-1][:top_k * 2]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < 0.01:
                break
            r = records[idx]
            results.append({
                "id": ids[idx],
                "content": r.get("content", ""),
                "score": score,
                "importance": r.get("importance", 0.5),
                "memory_score": r.get("score", r.get("importance", 0.5)),
                "type": r.get("type", "fact"),
                "entities": r.get("entities", []),
                "last_accessed": r.get("last_accessed"),
                "is_identity": r.get("is_identity", False),
                "match_source": "tfidf",
            })

        return results[:top_k]

    except Exception as e:
        print(f"⚠️  TF-IDF 检索失败: {e}")
        return []


def rrf_merge(result_lists: list[list[dict]], k: int = 60, top_n: int = 20) -> list[dict]:
    """
    Reciprocal Rank Fusion

    result_lists: 多路检索结果列表，每路已按相关性排序
    k: RRF 平滑参数（默认 60，论文推荐值）
    top_n: 返回 top N 结果

    RRF score = Σ 1/(k + rank_i)
    """
    rrf_scores: dict[str, float] = {}
    record_map: dict[str, dict] = {}

    for result_list in result_lists:
        for rank, record in enumerate(result_list, start=1):
            rid = record["id"]
            rrf_scores[rid] = rrf_scores.get(rid, 0.0) + 1.0 / (k + rank)
            if rid not in record_map:
                record_map[rid] = record

    sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)

    merged = []
    for rid in sorted_ids[:top_n]:
        r = record_map[rid].copy()
        r["rrf_score"] = round(rrf_scores[rid], 6)
        r["final_score"] = r.get("final_score", r.get("importance", 0.5))
        merged.append(r)

    return merged
