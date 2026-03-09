"""Memory System - 记忆系统

基于 openclaw 的 memory 系统设计的 Python 版本

核心功能:
1. 向量搜索 - 使用嵌入向量进行语义相似度搜索
2. 全文搜索 (FTS) - 基于 SQLite FTS5 的 BM25 关键词搜索
3. 混合搜索 - 结合向量和全文搜索，使用 MMR 重新排序
4. 嵌入缓存 - 避免重复计算嵌入
5. 自动同步 - 文件变更检测和增量索引

使用示例:
    ```python
    from mul_agent.memory import MemoryIndexManager, create_embedding_provider

    # 创建管理器
    manager = MemoryIndexManager(
        workspace_dir="/path/to/workspace",
        db_path="/path/to/memory.db",
        provider=embedding_provider,  # 可选，None 为 FTS-only 模式
    )

    # 搜索
    results = manager.search("如何部署应用", max_results=10)

    # 获取状态
    status = manager.status()
    print(f"Indexed: {status.files} files, {status.chunks} chunks")
    ```
"""

from .memory_schema import (
    ensure_memory_index_schema,
    get_db_connection,
)
from .embeddings import (
    EmbeddingProvider,
    EmbeddingProviderOptions,
    EmbeddingProviderResult,
    create_embedding_provider,
    sanitize_and_normalize_embedding,
    compute_text_hash,
)
from .memory_manager import (
    MemoryIndexManager,
    MemorySearchResult,
    MemoryProviderStatus,
    search_vector,
    search_keyword,
    merge_hybrid_results,
)
from .memory_indexer import (
    TextChunk,
    FileEntry,
    EmbeddingCache,
    MemoryIndexOperations,
    chunk_text,
    generate_embeddings,
    sync_memory_files,
    find_memory_files,
    process_memory_file,
)
from .mmr import (
    MMRConfig,
    MMRItem,
    mmr_rerank,
    apply_mmr_to_hybrid_results,
    text_similarity,
    temporal_decay_factor,
    apply_temporal_decay,
)

# FastAPI 路由
from .memory_routes import router as memory_router

__all__ = [
    # Schema
    "ensure_memory_index_schema",
    "get_db_connection",
    # Embeddings
    "EmbeddingProvider",
    "EmbeddingProviderOptions",
    "EmbeddingProviderResult",
    "create_embedding_provider",
    "sanitize_and_normalize_embedding",
    "compute_text_hash",
    # Manager
    "MemoryIndexManager",
    "MemorySearchResult",
    "MemoryProviderStatus",
    "search_vector",
    "search_keyword",
    "merge_hybrid_results",
    # Indexer
    "TextChunk",
    "FileEntry",
    "EmbeddingCache",
    "MemoryIndexOperations",
    "chunk_text",
    "generate_embeddings",
    "sync_memory_files",
    "find_memory_files",
    "process_memory_file",
    # MMR
    "MMRConfig",
    "MMRItem",
    "mmr_rerank",
    "apply_mmr_to_hybrid_results",
    "text_similarity",
    "temporal_decay_factor",
    "apply_temporal_decay",
    # Routes
    "memory_router",
]
