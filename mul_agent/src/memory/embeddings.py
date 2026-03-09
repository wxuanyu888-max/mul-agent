"""Embeddings - 嵌入向量生成客户端

支持多个嵌入提供商：OpenAI, Gemini, Ollama 等
基于 openclaw 的 embeddings.ts 设计
"""

import hashlib
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Optional

import httpx


# ============================================================================
# 类型定义
# ============================================================================

EmbeddingProviderId = Literal["openai", "gemini", "ollama", "local", "voyage", "mistral"]
EmbeddingProviderRequest = EmbeddingProviderId | Literal["auto"]
EmbeddingProviderFallback = EmbeddingProviderId | Literal["none"]


@dataclass
class EmbeddingProvider:
    """嵌入提供商协议"""
    id: str
    model: str
    max_input_tokens: Optional[int] = None

    async def embed_query(self, text: str) -> list[float]:
        """嵌入单个查询"""
        raise NotImplementedError

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入"""
        return [await self.embed_query(text) for text in texts]


@dataclass
class EmbeddingProviderResult:
    """嵌入提供商创建结果"""
    provider: Optional[EmbeddingProvider]
    requested_provider: EmbeddingProviderRequest
    fallback_from: Optional[EmbeddingProviderId] = None
    fallback_reason: Optional[str] = None
    provider_unavailable_reason: Optional[str] = None
    openai: Optional["OpenAiEmbeddingClient"] = None
    gemini: Optional["GeminiEmbeddingClient"] = None
    ollama: Optional["OllamaEmbeddingClient"] = None


@dataclass
class OpenAiEmbeddingClient:
    """OpenAI 嵌入客户端配置"""
    base_url: str
    api_key: str
    model: str
    headers: dict[str, str] | None = None
    max_input_tokens: Optional[int] = None


@dataclass
class GeminiEmbeddingClient:
    """Gemini 嵌入客户端配置"""
    api_key: str
    model: str
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"


@dataclass
class OllamaEmbeddingClient:
    """Ollama 嵌入客户端配置"""
    base_url: str
    model: str


# ============================================================================
# 工具函数
# ============================================================================

def sanitize_and_normalize_embedding(vec: list[float]) -> list[float]:
    """清理并归一化嵌入向量"""
    # 清理非有限值
    sanitized = [v if math.isfinite(v) else 0.0 for v in vec]

    # L2 归一化
    magnitude = math.sqrt(sum(v * v for v in sanitized))
    if magnitude < 1e-10:
        return sanitized

    return [v / magnitude for v in sanitized]


# ============================================================================
# OpenAI 嵌入客户端
# ============================================================================

DEFAULT_OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"

OPENAI_MAX_INPUT_TOKENS: dict[str, int] = {
    "text-embedding-3-small": 8192,
    "text-embedding-3-large": 8192,
    "text-embedding-ada-002": 8191,
}


def normalize_openai_model(model: str) -> str:
    """规范化 OpenAI 模型名称"""
    model = model.removeprefix("openai/").strip()
    return model or DEFAULT_OPENAI_EMBEDDING_MODEL


async def create_openai_embedding_provider(
    api_key: str,
    model: str = DEFAULT_OPENAI_EMBEDDING_MODEL,
    base_url: str = DEFAULT_OPENAI_BASE_URL,
    headers: dict[str, str] | None = None,
) -> tuple[EmbeddingProvider, OpenAiEmbeddingClient]:
    """创建 OpenAI 嵌入提供商"""
    client = OpenAiEmbeddingClient(
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        model=normalize_openai_model(model),
        headers=headers,
        max_input_tokens=OPENAI_MAX_INPUT_TOKENS.get(normalize_openai_model(model)),
    )

    provider = OpenAiEmbeddingProvider(client)
    return provider, client


class OpenAiEmbeddingProvider(EmbeddingProvider):
    """OpenAI 嵌入提供商实现"""

    def __init__(self, client: OpenAiEmbeddingClient):
        super().__init__(id="openai", model=client.model, max_input_tokens=client.max_input_tokens)
        self.client = client

    async def embed_query(self, text: str) -> list[float]:
        headers = {
            "Authorization": f"Bearer {self.client.api_key}",
            "Content-Type": "application/json",
            **(self.client.headers or {}),
        }

        payload = {
            "model": self.client.model,
            "input": text,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.client.base_url}/embeddings",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            embedding = data["data"][0]["embedding"]
            return sanitize_and_normalize_embedding(embedding)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        headers = {
            "Authorization": f"Bearer {self.client.api_key}",
            "Content-Type": "application/json",
            **(self.client.headers or {}),
        }

        payload = {
            "model": self.client.model,
            "input": texts,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.client.base_url}/embeddings",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return [
                sanitize_and_normalize_embedding(item["embedding"])
                for item in data["data"]
            ]


# ============================================================================
# Gemini 嵌入客户端
# ============================================================================

DEFAULT_GEMINI_EMBEDDING_MODEL = "text-embedding-004"
DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"


async def create_gemini_embedding_provider(
    api_key: str,
    model: str = DEFAULT_GEMINI_EMBEDDING_MODEL,
    base_url: str = DEFAULT_GEMINI_BASE_URL,
) -> tuple[EmbeddingProvider, GeminiEmbeddingClient]:
    """创建 Gemini 嵌入提供商"""
    client = GeminiEmbeddingClient(
        api_key=api_key,
        model=model.removeprefix("gemini/").strip() or DEFAULT_GEMINI_EMBEDDING_MODEL,
        base_url=base_url.rstrip("/"),
    )

    provider = GeminiEmbeddingProvider(client)
    return provider, client


class GeminiEmbeddingProvider(EmbeddingProvider):
    """Gemini 嵌入提供商实现"""

    def __init__(self, client: GeminiEmbeddingClient):
        super().__init__(id="gemini", model=client.model)
        self.client = client

    async def embed_query(self, text: str) -> list[float]:
        url = f"{self.client.base_url}/models/{self.client.model}:embedContent"
        params = {"key": self.client.api_key}

        payload = {
            "model": f"models/{self.client.model}",
            "content": {"parts": [{"text": text}]},
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, params=params, json=payload)
            response.raise_for_status()
            data = response.json()
            embedding = data["embedding"]["values"]
            return sanitize_and_normalize_embedding(embedding)


# ============================================================================
# Ollama 嵌入客户端
# ============================================================================

DEFAULT_OLLAMA_EMBEDDING_MODEL = "mxbai-embed-large"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"


async def create_ollama_embedding_provider(
    model: str = DEFAULT_OLLAMA_EMBEDDING_MODEL,
    base_url: str = DEFAULT_OLLAMA_BASE_URL,
) -> tuple[EmbeddingProvider, OllamaEmbeddingClient]:
    """创建 Ollama 嵌入提供商"""
    client = OllamaEmbeddingClient(
        base_url=base_url.rstrip("/"),
        model=model.removeprefix("ollama/").strip() or DEFAULT_OLLAMA_EMBEDDING_MODEL,
    )

    provider = OllamaEmbeddingProvider(client)
    return provider, client


class OllamaEmbeddingProvider(EmbeddingProvider):
    """Ollama 嵌入提供商实现"""

    def __init__(self, client: OllamaEmbeddingClient):
        super().__init__(id="ollama", model=client.model)
        self.client = client

    async def embed_query(self, text: str) -> list[float]:
        url = f"{self.client.base_url}/api/embeddings"

        payload = {
            "model": self.client.model,
            "prompt": text,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            embedding = data["embedding"]
            return sanitize_and_normalize_embedding(embedding)


# ============================================================================
# 自动提供商选择
# ============================================================================

REMOTE_EMBEDDING_PROVIDER_IDS: list[EmbeddingProviderId] = ["openai", "gemini", "voyage", "mistral"]


@dataclass
class EmbeddingProviderOptions:
    """嵌入提供商选项"""
    provider: EmbeddingProviderRequest
    model: str
    fallback: EmbeddingProviderFallback
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    headers: Optional[dict[str, str]] = None
    local_model_path: Optional[str] = None


async def create_embedding_provider(
    options: EmbeddingProviderOptions,
) -> EmbeddingProviderResult:
    """创建嵌入提供商

    支持自动选择提供商，按优先级尝试：
    1. 本地嵌入 (如果配置了模型路径)
    2. OpenAI (如果配置了 API key)
    3. Gemini (如果配置了 API key)
    4. Ollama (如果本地服务可用)

    Args:
        options: 提供商选项

    Returns:
        嵌入提供商结果
    """
    requested_provider = options.provider
    fallback = options.fallback

    async def create_provider(provider_id: EmbeddingProviderId):
        """内部函数：创建指定类型的提供商"""
        if provider_id == "openai":
            if not options.api_key:
                raise ValueError("OpenAI API key required")
            return await create_openai_embedding_provider(
                api_key=options.api_key,
                model=options.model,
                base_url=options.base_url or DEFAULT_OPENAI_BASE_URL,
            )
        elif provider_id == "gemini":
            if not options.api_key:
                raise ValueError("Gemini API key required")
            return await create_gemini_embedding_provider(
                api_key=options.api_key,
                model=options.model,
                base_url=options.base_url or DEFAULT_GEMINI_BASE_URL,
            )
        elif provider_id == "ollama":
            return await create_ollama_embedding_provider(
                model=options.model,
                base_url=options.base_url or DEFAULT_OLLAMA_BASE_URL,
            )
        else:
            raise ValueError(f"Unsupported provider: {provider_id}")

    # 处理自动选择
    if requested_provider == "auto":
        for provider_id in REMOTE_EMBEDDING_PROVIDER_IDS:
            try:
                provider_result = await create_provider(provider_id)
                return EmbeddingProviderResult(
                    provider=provider_result[0],
                    requested_provider=requested_provider,
                    **{provider_id: provider_result[1]},
                )
            except ValueError as e:
                if "API key required" in str(e):
                    continue  # 尝试下一个提供商
                raise  # 其他错误直接抛出

        # 所有远程提供商都不可用，返回 null provider (仅 FTS 模式)
        return EmbeddingProviderResult(
            provider=None,
            requested_provider=requested_provider,
            provider_unavailable_reason="No API keys configured for embedding providers",
        )

    # 处理指定提供商
    try:
        provider_result = await create_provider(requested_provider)
        return EmbeddingProviderResult(
            provider=provider_result[0],
            requested_provider=requested_provider,
            **{requested_provider: provider_result[1]},
        )
    except ValueError as e:
        if fallback and fallback != "none" and fallback != requested_provider:
            try:
                fallback_result = await create_provider(fallback)
                return EmbeddingProviderResult(
                    provider=fallback_result[0],
                    requested_provider=requested_provider,
                    fallback_from=requested_provider,
                    fallback_reason=str(e),
                    **{fallback: fallback_result[1]},
                )
            except ValueError as fallback_err:
                raise ValueError(
                    f"Primary provider ({requested_provider}) failed: {e}\n"
                    f"Fallback provider ({fallback}) also failed: {fallback_err}"
                ) from fallback_err
        raise


# ============================================================================
# 嵌入缓存
# ============================================================================

def compute_text_hash(text: str) -> str:
    """计算文本哈希用于缓存"""
    return hashlib.sha256(text.encode()).hexdigest()
