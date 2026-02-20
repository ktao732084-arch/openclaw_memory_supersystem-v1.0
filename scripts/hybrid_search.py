#!/usr/bin/env python3
"""
Memory System v1.6.0 - 混合检索引擎
结合关键词检索和向量检索，提供更智能的搜索结果
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SearchResult:
    """检索结果"""

    id: str
    content: str
    score: float
    keyword_score: float = 0.0
    vector_score: float = 0.0
    metadata: dict = field(default_factory=dict)
    match_source: str = "hybrid"


class HybridSearchEngine:
    """混合检索引擎"""

    def __init__(
        self,
        vector_index,
        embedding_engine,
        keyword_weight: float = 0.3,
        vector_weight: float = 0.7,
        min_score: float = 0.2,
    ):
        self.vector_index = vector_index
        self.embedding_engine = embedding_engine
        self.keyword_weight = keyword_weight
        self.vector_weight = vector_weight
        self.min_score = min_score

    def _normalize_scores(self, results: list[dict], score_key: str = "score") -> list[dict]:
        """归一化分数到 0-1 范围"""
        if not results:
            return results

        scores = [r.get(score_key, 0) for r in results]
        max_score = max(scores) if scores else 1
        min_score_val = min(scores) if scores else 0

        if max_score == min_score_val:
            return results

        for r in results:
            original = r.get(score_key, 0)
            r[f"normalized_{score_key}"] = (original - min_score_val) / (max_score - min_score_val)

        return results

    def vector_search(
        self,
        query: str,
        top_k: int = 10,
        memory_type: str | None = None,
    ) -> list[SearchResult]:
        """向量检索"""
        try:
            query_vector = self.embedding_engine.embed_single(query)
            raw_results = self.vector_index.search_similar(
                query_vector,
                top_k=top_k * 2,
                memory_type=memory_type,
            )

            results = []
            for memory_id, content, similarity, metadata in raw_results:
                results.append(
                    SearchResult(
                        id=memory_id,
                        content=content,
                        score=similarity,
                        vector_score=similarity,
                        keyword_score=0.0,
                        metadata=metadata,
                        match_source="vector",
                    )
                )

            return results
        except Exception as e:
            print(f"⚠️ 向量检索失败: {e}")
            return []

    def keyword_search(
        self,
        query: str,
        memory_dir: Path,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """关键词检索（使用现有的 BM25/关键词索引）"""
        import re

        memory_dir = Path(memory_dir)
        keywords_path = memory_dir / "layer2" / "index" / "keywords.json"

        if not keywords_path.exists():
            return []

        with open(keywords_path, encoding="utf-8") as f:
            keywords_index = json.load(f)

        query_words = set()
        segments = re.split(r"[，。！？、；：" r"''（）\[\]【】\s]+", query)
        for seg in segments:
            seg = seg.strip()
            if len(seg) >= 2:
                query_words.add(seg)
            for i in range(len(seg)):
                for length in [2, 3, 4]:
                    if i + length <= len(seg):
                        sub = seg[i : i + length]
                        if len(sub) >= 2:
                            query_words.add(sub)

        memory_scores: dict[str, float] = {}
        for word in query_words:
            if word in keywords_index:
                for mem_id in keywords_index[word]:
                    if mem_id not in memory_scores:
                        memory_scores[mem_id] = 0
                    memory_scores[mem_id] += 1

        all_memories = {}
        for mem_type in ["facts", "beliefs", "summaries"]:
            jsonl_path = memory_dir / "layer2" / "active" / f"{mem_type}.jsonl"
            if jsonl_path.exists():
                with open(jsonl_path, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                record = json.loads(line)
                                all_memories[record["id"]] = record
                            except json.JSONDecodeError as e:
                                print(f"⚠️ JSON解析失败: {e}")
                            except KeyError as e:
                                print(f"⚠️ 记录缺少必需字段: {e}")

        results = []
        sorted_ids = sorted(memory_scores.keys(), key=lambda x: memory_scores[x], reverse=True)

        for mem_id in sorted_ids[: top_k * 2]:
            if mem_id in all_memories:
                mem = all_memories[mem_id]
                raw_score = memory_scores[mem_id]
                normalized_score = min(1.0, raw_score / max(len(query_words), 1))

                results.append(
                    SearchResult(
                        id=mem_id,
                        content=mem.get("content", ""),
                        score=normalized_score,
                        keyword_score=normalized_score,
                        vector_score=0.0,
                        metadata={
                            "type": mem.get("type", "fact"),
                            "importance": mem.get("importance", 0.5),
                        },
                        match_source="keyword",
                    )
                )

        return results

    def search(
        self,
        query: str,
        memory_dir: Path,
        top_k: int = 10,
        use_keyword: bool = True,
        use_vector: bool = True,
        memory_type: str | None = None,
    ) -> list[SearchResult]:
        """
        混合检索

        Args:
            query: 查询文本
            memory_dir: 记忆目录
            top_k: 返回数量
            use_keyword: 是否使用关键词检索
            use_vector: 是否使用向量检索
            memory_type: 过滤记忆类型

        Returns:
            排序后的检索结果
        """
        results_by_id: dict[str, SearchResult] = {}

        if use_vector:
            vector_results = self.vector_search(query, top_k=top_k * 2, memory_type=memory_type)
            for r in vector_results:
                if r.id not in results_by_id:
                    results_by_id[r.id] = r
                else:
                    existing = results_by_id[r.id]
                    existing.vector_score = max(existing.vector_score, r.vector_score)

        if use_keyword:
            keyword_results = self.keyword_search(query, memory_dir=memory_dir, top_k=top_k * 2)
            for r in keyword_results:
                if r.id not in results_by_id:
                    results_by_id[r.id] = r
                else:
                    existing = results_by_id[r.id]
                    existing.keyword_score = max(existing.keyword_score, r.keyword_score)

        for r in results_by_id.values():
            r.score = self.keyword_weight * r.keyword_score + self.vector_weight * r.vector_score

        final_results = [r for r in results_by_id.values() if r.score >= self.min_score]

        final_results.sort(key=lambda x: x.score, reverse=True)
        return final_results[:top_k]

    def update_weights(self, keyword_weight: float, vector_weight: float):
        """更新权重"""
        total = keyword_weight + vector_weight
        if total > 0:
            self.keyword_weight = keyword_weight / total
            self.vector_weight = vector_weight / total

    def set_min_score(self, min_score: float):
        """设置最小分数阈值"""
        self.min_score = max(0.0, min(1.0, min_score))


def create_hybrid_search_engine(
    memory_dir: Path,
    embedding_engine,
    backend: str = "sqlite",
    keyword_weight: float = 0.3,
    vector_weight: float = 0.7,
    min_score: float = 0.2,
) -> HybridSearchEngine | None:
    """
    创建混合检索引擎

    Args:
        memory_dir: 记忆目录
        embedding_engine: 嵌入引擎
        backend: 向量存储后端
        keyword_weight: 关键词权重
        vector_weight: 向量权重
        min_score: 最小分数阈值

    Returns:
        HybridSearchEngine 实例或 None
    """
    from vector_index import VectorIndexManager

    try:
        vector_index = VectorIndexManager(
            memory_dir=memory_dir,
            dimension=embedding_engine.dimension,
            backend=backend,
        )

        return HybridSearchEngine(
            vector_index=vector_index,
            embedding_engine=embedding_engine,
            keyword_weight=keyword_weight,
            vector_weight=vector_weight,
            min_score=min_score,
        )
    except Exception as e:
        print(f"⚠️ 创建混合检索引擎失败: {e}")
        return None
