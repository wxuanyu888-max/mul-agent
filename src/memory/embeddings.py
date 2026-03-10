"""Embedding Providers - 嵌入向量提供商

提供多种嵌入向量提供商：
1. OpenAI API
2. Google Gemini
3. Voyage AI
4. Mistral AI
5. Ollama (本地)
6. Local (node-llama-cpp)
"""

import os
import hashlib
import urllib.request
import urllib.error
import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol
from dataclasses import dataclass
from pathlib import Path


def sanitize_and_normalize_embedding(vec: List[float]) -> List[float]:
    """标准化嵌入向量

    1. 将非有限值替换为 0
    2. L2 归一化
    """
    import math

    # 清理非有限值
    sanitized = [v if math.isfinite(v) else 0.0 for v in vec]

    # L2 归一化
    magnitude = math.sqrt(sum(v * v for v in sanitized))
    if magnitude < 1e-10:
        return sanitized

    return [v / magnitude for v in sanitized]


@dataclass
class EmbeddingProviderResult:
    """嵌入提供商结果"""
    provider: Optional['EmbeddingProvider']
    requested_provider: str
    fallback_from: Optional[str] = None
    fallback_reason: Optional[str] = None
    provider_unavailable_reason: Optional[str] = None


class EmbeddingProvider(Protocol):
    """嵌入提供商协议"""

    id: str
    model: str
    max_input_tokens: Optional[int]

    def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        ...

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """嵌入批处理"""
        ...


class BaseEmbeddingProvider(ABC):
    """嵌入提供商基类"""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.max_input_tokens: Optional[int] = None

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """嵌入批处理"""
        pass


class OpenAiEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI 嵌入提供商"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "text-embedding-3-small"
    ):
        super().__init__(api_key, base_url)
        self.model = model
        self.id = "openai"
        self.base_url = base_url or "https://api.openai.com/v1"
        self.max_input_tokens = 8191

    async def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """嵌入批处理"""
        if not self.api_key:
            raise ValueError("No API key found for provider openai")

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                embeddings = [item["embedding"] for item in result["data"]]
                return [sanitize_and_normalize_embedding(e) for e in embeddings]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"OpenAI API error: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"OpenAI API connection error: {e.reason}")


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini 嵌入提供商"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-004"
    ):
        super().__init__(api_key)
        self.model = model
        self.id = "gemini"
        self.max_input_tokens = 2048

    async def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        if not self.api_key:
            raise ValueError("No API key found for provider gemini")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:embedContent"
        params = f"?key={self.api_key}"

        data = {
            "model": f"models/{self.model}",
            "content": {
                "parts": [{"text": text}]
            }
        }

        req = urllib.request.Request(
            f"{url}{params}",
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                embedding = result.get("embedding", {}).get("values", [])
                return sanitize_and_normalize_embedding(embedding)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Gemini API error: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Gemini API connection error: {e.reason}")

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """嵌入批处理 - 逐个处理"""
        results = []
        for text in texts:
            result = await self.embed_query(text)
            results.append(result)
        return results


class VoyageEmbeddingProvider(BaseEmbeddingProvider):
    """Voyage AI 嵌入提供商"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "voyage-3"
    ):
        super().__init__(api_key)
        self.model = model
        self.id = "voyage"
        self.base_url = "https://api.voyageai.com/v1"
        self.max_input_tokens = 32000

    async def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """嵌入批处理"""
        if not self.api_key:
            raise ValueError("No API key found for provider voyage")

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "input": texts,
            "input_type": "document"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                embeddings = result.get("data", [])
                return [
                    sanitize_and_normalize_embedding(item["embedding"])
                    for item in embeddings
                ]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Voyage API error: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Voyage API connection error: {e.reason}")


class MistralEmbeddingProvider(BaseEmbeddingProvider):
    """Mistral AI 嵌入提供商"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "mistral-embed"
    ):
        super().__init__(api_key)
        self.model = model
        self.id = "mistral"
        self.base_url = "https://api.mistral.ai/v1"
        self.max_input_tokens = 8192

    async def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """嵌入批处理"""
        if not self.api_key:
            raise ValueError("No API key found for provider mistral")

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                embeddings = [item["embedding"] for item in result["data"]]
                return [sanitize_and_normalize_embedding(e) for e in embeddings]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Mistral API error: {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Mistral API connection error: {e.reason}")


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Ollama 本地嵌入提供商"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text"
    ):
        super().__init__(None, base_url)
        self.model = model
        self.id = "ollama"
        self.max_input_tokens = 2048

    async def embed_query(self, text: str) -> List[float]:
        """嵌入单个查询"""
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """嵌入批处理"""
        url = f"{self.base_url}/api/embed"

        data = {
            "model": self.model,
            "input": texts
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                embeddings = result.get("embeddings", [])
                return [sanitize_and_normalize_embedding(e) for e in embeddings]
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama connection error: {e.reason}")


def _compute_text_hash(text: str) -> str:
    """计算文本哈希"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


async def create_embedding_provider(
    config: Dict[str, Any],
    agent_dir: Optional[str] = None,
    provider: str = "auto",
    model: Optional[str] = None,
    fallback: str = "none",
    remote: Optional[Dict[str, Any]] = None,
    local: Optional[Dict[str, Any]] = None
) -> EmbeddingProviderResult:
    """创建嵌入提供商

    Args:
        config: 配置字典
        agent_dir: Agent 目录
        provider: 提供商名称 ("auto", "openai", "gemini", "voyage", "mistral", "ollama", "local")
        model: 模型名称
        fallback: 回退策略
        remote: 远程配置
        local: 本地配置

    Returns:
        EmbeddingProviderResult 实例
    """
    # 获取 API keys
    api_keys = config.get("api_keys", {})

    # 远程提供商列表（用于 auto 模式）
    remote_providers = ["openai", "gemini", "voyage", "mistral"]

    # 默认模型
    default_models = {
        "openai": "text-embedding-3-small",
        "gemini": "text-embedding-004",
        "voyage": "voyage-3",
        "mistral": "mistral-embed",
        "ollama": "nomic-embed-text",
        "local": "ggml-org/embeddinggemma-300m-qat-q8_0-GGUF/embeddinggemma-300m-qat-Q8_0.gguf"
    }

    # Auto 模式：尝试远程提供商
    if provider == "auto":
        for provider_id in remote_providers:
            key = api_keys.get(provider_id)
            if key:
                provider = provider_id
                break
        else:
            # 没有远程 key，尝试本地
            provider = "ollama"

    # 创建提供商
    provider_instance: Optional[EmbeddingProvider] = None
    unavailable_reason: Optional[str] = None

    try:
        if provider == "openai":
            key = api_keys.get("openai") or (remote or {}).get("apiKey")
            if not key:
                unavailable_reason = "No OpenAI API key found"
            else:
                provider_instance = OpenAiEmbeddingProvider(
                    api_key=key,
                    base_url=(remote or {}).get("baseUrl"),
                    model=model or default_models["openai"]
                )

        elif provider == "gemini":
            key = api_keys.get("gemini") or (remote or {}).get("apiKey")
            if not key:
                unavailable_reason = "No Gemini API key found"
            else:
                provider_instance = GeminiEmbeddingProvider(
                    api_key=key,
                    model=model or default_models["gemini"]
                )

        elif provider == "voyage":
            key = api_keys.get("voyage") or (remote or {}).get("apiKey")
            if not key:
                unavailable_reason = "No Voyage API key found"
            else:
                provider_instance = VoyageEmbeddingProvider(
                    api_key=key,
                    model=model or default_models["voyage"]
                )

        elif provider == "mistral":
            key = api_keys.get("mistral") or (remote or {}).get("apiKey")
            if not key:
                unavailable_reason = "No Mistral API key found"
            else:
                provider_instance = MistralEmbeddingProvider(
                    api_key=key,
                    model=model or default_models["mistral"]
                )

        elif provider == "ollama":
            base_url = (remote or {}).get("baseUrl", "http://localhost:11434")
            try:
                provider_instance = OllamaEmbeddingProvider(
                    base_url=base_url,
                    model=model or default_models["ollama"]
                )
                # 测试连接
                await provider_instance.embed_query("test")
            except Exception as e:
                unavailable_reason = f"Ollama not available: {e}"
                provider_instance = None

        elif provider == "local":
            # 本地 node-llama-cpp（需要额外安装）
            unavailable_reason = "Local embedding not implemented in Python yet"

    except Exception as e:
        unavailable_reason = f"Error creating provider: {e}"

    # 处理回退
    fallback_from = None
    fallback_reason = None

    if provider_instance is None and fallback != "none":
        # 尝试回退
        if fallback == "ollama":
            try:
                base_url = (local or {}).get("baseUrl", "http://localhost:11434")
                provider_instance = OllamaEmbeddingProvider(
                    base_url=base_url,
                    model=model or default_models["ollama"]
                )
                fallback_from = provider
                fallback_reason = f"Provider {provider} unavailable, falling back to ollama"
            except Exception as e:
                fallback_reason = f"Also failed to fallback to ollama: {e}"

    return EmbeddingProviderResult(
        provider=provider_instance,
        requested_provider=provider,
        fallback_from=fallback_from,
        fallback_reason=fallback_reason,
        provider_unavailable_reason=unavailable_reason
    )
