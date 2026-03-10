"""Memory System - 记忆系统

提供：
1. 会话上下文管理 (SessionContextManager)
2. 记忆索引和搜索 (MemoryIndexManager)
3. 记忆存档 (MemoryArchiver)
4. 记忆搜索工具 (MemorySearchTool)
5. 嵌入提供商 (EmbeddingProvider)
6. Bootstrap 记忆管理 (BootstrapMemoryManager)
"""

# 会话上下文管理
from .session_context import (
    SessionContextManager,
    SessionContext,
    TokenThreshold,
    estimate_tokens
)

# 记忆索引和搜索
from .memory_manager import (
    MemoryIndexManager,
    MemorySearchResult,
    MemoryProviderStatus,
    get_or_create_memory_index
)

# 记忆存档
from .archiver import (
    MemoryArchiver,
    MemoryArchive
)

# 记忆搜索工具
from .search_tool import (
    MemorySearchTool,
    MemorySearchOptions,
    MemorySearchResponse
)

# 嵌入提供商
from .embeddings import (
    EmbeddingProvider,
    EmbeddingProviderResult,
    create_embedding_provider,
    sanitize_and_normalize_embedding,
    # 具体提供商
    OpenAiEmbeddingProvider,
    GeminiEmbeddingProvider,
    VoyageEmbeddingProvider,
    MistralEmbeddingProvider,
    OllamaEmbeddingProvider
)

# Bootstrap 记忆管理
from .bootstrap_manager import (
    BootstrapMemoryManager,
    BootstrapEntry,
    BootstrapFolder
)


__all__ = [
    # 会话上下文
    "SessionContextManager",
    "SessionContext",
    "TokenThreshold",
    "estimate_tokens",

    # 记忆索引
    "MemoryIndexManager",
    "MemorySearchResult",
    "MemoryProviderStatus",
    "get_or_create_memory_index",

    # 记忆存档
    "MemoryArchiver",
    "MemoryArchive",

    # 记忆搜索
    "MemorySearchTool",
    "MemorySearchOptions",
    "MemorySearchResponse",

    # 嵌入提供商
    "EmbeddingProvider",
    "EmbeddingProviderResult",
    "create_embedding_provider",
    "sanitize_and_normalize_embedding",
    "OpenAiEmbeddingProvider",
    "GeminiEmbeddingProvider",
    "VoyageEmbeddingProvider",
    "MistralEmbeddingProvider",
    "OllamaEmbeddingProvider",

    # Bootstrap
    "BootstrapMemoryManager",
    "BootstrapEntry",
    "BootstrapFolder",
]
