#!/usr/bin/env python3
"""
Memory System v1.6.0 - 向量嵌入引擎
支持多种 Embedding 提供者：OpenAI、HuggingFace、本地模型
"""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np


class EmbeddingProvider(ABC):
    """嵌入提供者基类"""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """生成嵌入向量"""
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """获取向量维度"""
        pass


class OpenAIEmbedding(EmbeddingProvider):
    """OpenAI Embedding 提供者"""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-small",
        base_url: str | None = None,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

        self.dimensions = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }

    def embed(self, texts: list[str]) -> list[list[float]]:
        """调用 OpenAI API 生成嵌入"""
        import requests

        if not self.api_key:
            raise ValueError("OpenAI API Key 未配置，请设置 OPENAI_API_KEY 环境变量")

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        data = {"input": texts, "model": self.model}

        response = requests.post(
            f"{self.base_url}/embeddings",
            headers=headers,
            json=data,
            timeout=60,
        )

        if response.status_code != 200:
            raise Exception(f"OpenAI API error: {response.text}")

        result = response.json()
        return [item["embedding"] for item in result["data"]]

    def get_dimension(self) -> int:
        return self.dimensions.get(self.model, 1536)


class HuggingFaceEmbedding(EmbeddingProvider):
    """HuggingFace Embedding 提供者"""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        api_key: str | None = None,
    ):
        self.model_name = model_name
        self.api_key = api_key or os.getenv("HUGGINGFACE_API_KEY")

        self.dimensions = {
            "sentence-transformers/all-MiniLM-L6-v2": 384,
            "sentence-transformers/all-mpnet-base-v2": 768,
            "BAAI/bge-large-en-v1.5": 1024,
            "BAAI/bge-small-zh-v1.5": 512,
        }

    def embed(self, texts: list[str]) -> list[list[float]]:
        """调用 HuggingFace API 生成嵌入"""
        import requests

        if not self.api_key:
            raise ValueError("HuggingFace API Key 未配置，请设置 HUGGINGFACE_API_KEY 环境变量")

        headers = {"Authorization": f"Bearer {self.api_key}"}

        response = requests.post(
            f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model_name}",
            headers=headers,
            json={"inputs": texts},
            timeout=60,
        )

        if response.status_code != 200:
            raise Exception(f"HuggingFace API error: {response.text}")

        return response.json()

    def get_dimension(self) -> int:
        return self.dimensions.get(self.model_name, 384)


class LocalEmbedding(EmbeddingProvider):
    """本地模型 Embedding 提供者"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        """延迟加载模型"""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
            except ImportError as err:
                raise ImportError("请安装 sentence-transformers: pip install sentence-transformers") from err
        return self._model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """使用本地模型生成嵌入"""
        model = self._load_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def get_dimension(self) -> int:
        model = self._load_model()
        return model.get_sentence_embedding_dimension()


class VectorEmbeddingEngine:
    """向量嵌入引擎"""

    def __init__(
        self,
        provider: str = "openai",
        model: str | None = None,
        api_key: str | None = None,
        cache_dir: Path | None = None,
        cache_max_size: int = 10000,
    ):
        self.provider_name = provider
        self.cache_dir = cache_dir
        self.cache_max_size = cache_max_size
        self._cache: dict[str, list[float]] = {}

        if provider == "openai":
            self.provider = OpenAIEmbedding(api_key=api_key, model=model or "text-embedding-3-small")
        elif provider == "huggingface":
            self.provider = HuggingFaceEmbedding(
                model_name=model or "sentence-transformers/all-MiniLM-L6-v2",
                api_key=api_key,
            )
        elif provider == "local":
            self.provider = LocalEmbedding(model_name=model or "all-MiniLM-L6-v2")
        else:
            raise ValueError(f"Unknown provider: {provider}")

        self.dimension = self.provider.get_dimension()

    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        return hashlib.md5(text.encode()).hexdigest()

    def embed_single(self, text: str) -> list[float]:
        """生成单个文本的嵌入"""
        cache_key = self._get_cache_key(text)
        if cache_key in self._cache:
            return self._cache[cache_key]

        embeddings = self.provider.embed([text])
        embedding = embeddings[0]

        if len(self._cache) < self.cache_max_size:
            self._cache[cache_key] = embedding

        return embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量生成嵌入"""
        uncached_indices = []
        uncached_texts = []
        results = [None] * len(texts)

        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                results[i] = self._cache[cache_key]
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            embeddings = self.provider.embed(uncached_texts)
            for i, idx in enumerate(uncached_indices):
                results[idx] = embeddings[i]
                cache_key = self._get_cache_key(texts[idx])
                if len(self._cache) < self.cache_max_size:
                    self._cache[cache_key] = embeddings[i]

        return results

    @staticmethod
    def similarity(vec1: list[float], vec2: list[float]) -> float:
        """计算余弦相似度"""
        a = np.array(vec1)
        b = np.array(vec2)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()


def get_embedding_engine(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> VectorEmbeddingEngine | None:
    """
    获取嵌入引擎实例

    优先级：
    1. 参数传入
    2. 环境变量
    3. 配置文件
    """
    if provider is None:
        provider = os.getenv("MEMORY_EMBEDDING_PROVIDER", "openai")

    try:
        return VectorEmbeddingEngine(provider=provider, model=model, api_key=api_key)
    except Exception as e:
        print(f"⚠️ 嵌入引擎初始化失败: {e}")
        return None
