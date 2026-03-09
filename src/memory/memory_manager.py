"""Memory Manager - 记忆管理器核心

基于 openclaw 的 manager.ts 设计
实现记忆的索引、搜索、同步等功能
"""

import json
import math
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable

import sqlite3

from .embeddings import EmbeddingProvider, sanitize_and_normalize_embedding
from .memory_schema import ensure_memory_index_schema, get_db_connection
from .mmr import mmr_rerank, MMRConfig, apply_temporal_decay


# ============================================================================
# 常量定义
# ============================================================================

SNIPPET_MAX_CHARS = 700
VECTOR_TABLE = "chunks_vec"
FTS_TABLE = "chunks_fts"
EMBEDDING_CACHE_TABLE = "embedding_cache"
BATCH_FAILURE_LIMIT = 2


# ============================================================================
# 配置类型
# ============================================================================

@dataclass
class MMRConfig:
    """MMR 配置"""
    enabled: bool = False
    lambda_param: float = 0.7


@dataclass
class TemporalDecayConfig:
    """时间衰减配置"""
    enabled: bool = False
    half_life_days: float = 30.0


DEFAULT_MMR_CONFIG = MMRConfig(enabled=False, lambda_param=0.7)
DEFAULT_TEMPORAL_DECAY_CONFIG = TemporalDecayConfig(enabled=False, half_life_days=30.0)


# ============================================================================
# 类型定义
# ============================================================================

MemorySource = str  # "memory" | "sessions"


@dataclass
class MemorySearchResult:
    """记忆搜索结果"""
    id: str
    path: str
    start_line: int
    end_line: int
    score: float
    snippet: str
    source: MemorySource
    citation: Optional[str] = None


@dataclass
class MemorySyncProgress:
    """同步进度"""
    completed: int
    total: int
    label: Optional[str] = None


@dataclass
class MemoryProviderStatus:
    """提供商状态"""
    backend: str = "builtin"
    provider: str = "none"
    model: Optional[str] = None
    files: int = 0
    chunks: int = 0
    dirty: bool = False
    workspace_dir: Optional[str] = None
    db_path: Optional[str] = None
    fts_enabled: bool = False
    fts_available: bool = False


# ============================================================================
# 工具函数
# ============================================================================

def parse_embedding(embedding_str: str) -> list[float]:
    """解析嵌入字符串为列表"""
    try:
        return json.loads(embedding_str)
    except json.JSONDecodeError:
        # 处理逗号分隔的字符串格式
        return [float(x.strip()) for x in embedding_str.split(",")]


def embedding_to_blob(embedding: list[float]) -> bytes:
    """将嵌入向量转换为 BLOB"""
    return bytes(embedding)


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """计算余弦相似度"""
    if len(vec1) != len(vec2) or len(vec1) == 0:
        return 0.0

    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))

    if magnitude1 < 1e-10 or magnitude2 < 1e-10:
        return 0.0

    return dot_product / (magnitude1 * magnitude2)


def bm25_rank_to_score(rank: float) -> float:
    """将 BM25 排名转换为分数 (排名越低越好)"""
    if rank >= 0:
        return 0.0
    return min(1.0, abs(rank) / 10.0)


def truncate_utf16_safe(text: str, max_chars: int) -> str:
    """安全截断文本 (UTF-16 安全)"""
    if len(text) <= max_chars:
        return text

    # 简单的截断处理
    return text[:max_chars]


def build_fts_query(raw: str) -> Optional[str]:
    """构建全文搜索查询"""
    cleaned = raw.strip()
    if not cleaned:
        return None

    # 简单处理：直接返回清理后的查询
    # TODO: 实现更复杂的查询构建逻辑
    return cleaned


# ============================================================================
# Memory Manager 核心类
# ============================================================================

class MemoryIndexManager:
    """记忆索引管理器

    核心能力:
    1. 记忆文件索引和分块
    2. 向量搜索和全文搜索
    3. 混合搜索 (向量 + 全文)
    4. 嵌入缓存
    5. 自动同步
    """

    def __init__(
        self,
        workspace_dir: str,
        db_path: str,
        provider: Optional[EmbeddingProvider] = None,
        fts_enabled: bool = True,
        sources: Optional[list[MemorySource]] = None,
    ):
        """初始化记忆管理器

        Args:
            workspace_dir: 工作目录
            db_path: 数据库路径
            provider: 嵌入提供商 (可选，为 None 时仅使用 FTS)
            fts_enabled: 是否启用全文搜索
            sources: 记忆来源列表
        """
        self.workspace_dir = Path(workspace_dir)
        self.db_path = Path(db_path)
        self.provider = provider
        self.fts_enabled = fts_enabled
        self.sources = set(sources or ["memory"])

        # 打开数据库
        self.db = self._open_database()

        # 全文搜索状态
        self.fts_available = False
        self.fts_error: Optional[str] = None

        # 初始化 Schema
        self._ensure_schema()

        # 脏标记
        self.dirty = False

    def _open_database(self) -> sqlite3.Connection:
        """打开数据库连接"""
        return get_db_connection(self.db_path)

    def _ensure_schema(self) -> None:
        """确保数据库模式正确"""
        self.fts_available, self.fts_error = ensure_memory_index_schema(
            db=self.db,
            embedding_cache_table=EMBEDDING_CACHE_TABLE,
            fts_table=FTS_TABLE,
            fts_enabled=self.fts_enabled,
        )

    def close(self) -> None:
        """关闭数据库连接"""
        self.db.close()

    # =========================================================================
    # 搜索功能
    # =========================================================================

    def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float = 0.3,
        use_hybrid: bool = True,
    ) -> list[MemorySearchResult]:
        """搜索记忆

        Args:
            query: 搜索查询
            max_results: 最大结果数
            min_score: 最小分数阈值
            use_hybrid: 是否使用混合搜索

        Returns:
            搜索结果列表
        """
        cleaned = query.strip()
        if not cleaned:
            return []

        # 如果没有提供商且 FTS 不可用，返回空结果
        if not self.provider and not self.fts_available:
            return []

        # FTS-only 模式
        if not self.provider:
            return self._search_keyword_only(cleaned, max_results, min_score)

        # 混合搜索或向量搜索
        if use_hybrid and self.fts_available:
            return self._search_hybrid(cleaned, max_results, min_score)

        return self._search_vector_only(cleaned, max_results, min_score)

    def _search_vector_only(
        self,
        query: str,
        max_results: int,
        min_score: float,
    ) -> list[MemorySearchResult]:
        """纯向量搜索"""
        if not self.provider:
            return []

        # 生成查询向量
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        query_vec = loop.run_until_complete(self.provider.embed_query(query))

        if not query_vec or all(v == 0 for v in query_vec):
            return []

        return search_vector(
            db=self.db,
            vector_table=VECTOR_TABLE,
            provider_model=self.provider.model,
            query_vec=query_vec,
            limit=max_results,
            snippet_max_chars=SNIPPET_MAX_CHARS,
        )

    def _search_keyword_only(
        self,
        query: str,
        max_results: int,
        min_score: float,
    ) -> list[MemorySearchResult]:
        """纯全文搜索 (FTS-only 模式)"""
        if not self.fts_available:
            return []

        return search_keyword(
            db=self.db,
            fts_table=FTS_TABLE,
            provider_model=None,  # FTS-only 模式搜索所有模型
            query=query,
            limit=max_results,
            snippet_max_chars=SNIPPET_MAX_CHARS,
            build_fts_query=build_fts_query,
            bm25_rank_to_score=bm25_rank_to_score,
        )

    def _search_hybrid(
        self,
        query: str,
        max_results: int,
        min_score: float,
    ) -> list[MemorySearchResult]:
        """混合搜索 (向量 + 全文)"""
        # 获取向量搜索结果
        vector_results = self._search_vector_only(query, max_results * 2, 0)

        # 获取全文搜索结果
        keyword_results = self._search_keyword_only(query, max_results * 2, 0)

        # 合并结果
        return merge_hybrid_results(
            vector_results=vector_results,
            keyword_results=keyword_results,
            vector_weight=0.7,
            text_weight=0.3,
            max_results=max_results,
            min_score=min_score,
        )

    # =========================================================================
    # 索引同步功能
    # =========================================================================

    def sync(
        self,
        force: bool = False,
        progress_callback: Optional[callable] = None,
    ) -> None:
        """同步记忆索引

        Args:
            force: 是否强制重新索引
            progress_callback: 进度回调函数
        """
        # TODO: 实现完整的同步逻辑
        pass

    def status(self) -> MemoryProviderStatus:
        """获取当前状态"""
        cursor = self.db.cursor()

        # 统计文件数
        cursor.execute("SELECT COUNT(*) FROM files")
        files_count = cursor.fetchone()[0]

        # 统计分块数
        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunks_count = cursor.fetchone()[0]

        return MemoryProviderStatus(
            backend="builtin",
            provider=self.provider.id if self.provider else "none",
            model=self.provider.model if self.provider else None,
            files=files_count,
            chunks=chunks_count,
            dirty=self.dirty,
            workspace_dir=str(self.workspace_dir),
            db_path=str(self.db_path),
            fts_enabled=self.fts_enabled,
            fts_available=self.fts_available,
        )


# ============================================================================
# 向量搜索实现
# ============================================================================

def search_vector(
    db: sqlite3.Connection,
    vector_table: str,
    provider_model: str,
    query_vec: list[float],
    limit: int,
    snippet_max_chars: int = SNIPPET_MAX_CHARS,
) -> list[MemorySearchResult]:
    """向量搜索实现

    Args:
        db: 数据库连接
        vector_table: 向量表名
        provider_model: 提供商模型名称
        query_vec: 查询向量
        limit: 结果限制
        snippet_max_chars: 片段最大字符数

    Returns:
        搜索结果列表
    """
    if not query_vec or limit <= 0:
        return []

    cursor = db.cursor()

    # 将向量转换为 BLOB
    vec_blob = embedding_to_blob(query_vec)

    # 使用 sqlite-vec 进行余弦相似度搜索
    # 注意：需要先加载 sqlite-vec 扩展
    try:
        cursor.execute("""
            SELECT c.id, c.path, c.start_line, c.end_line, c.text, c.source,
                   vec_distance_cosine(v.embedding, ?) AS dist
            FROM chunks_vec v
            JOIN chunks c ON c.id = v.id
            WHERE c.model = ?
            ORDER BY dist ASC
            LIMIT ?
        """, (vec_blob, provider_model, limit))
    except sqlite3.OperationalError:
        # 如果没有 sqlite-vec 扩展，使用 CPU 计算
        return _search_vector_cpu(db, provider_model, query_vec, limit, snippet_max_chars)

    rows = cursor.fetchall()

    return [
        MemorySearchResult(
            id=row[0],
            path=row[1],
            start_line=row[2],
            end_line=row[3],
            score=1 - row[4],  # 距离转分数
            snippet=truncate_utf16_safe(row[5], snippet_max_chars),
            source=row[6],
        )
        for row in rows
    ]


def _search_vector_cpu(
    db: sqlite3.Connection,
    provider_model: str,
    query_vec: list[float],
    limit: int,
    snippet_max_chars: int,
) -> list[MemorySearchResult]:
    """CPU 向量搜索 (后备方案)"""
    cursor = db.cursor()

    # 获取所有相关分块
    cursor.execute("""
        SELECT id, path, start_line, end_line, text, embedding, source
        FROM chunks
        WHERE model = ?
    """, (provider_model,))

    rows = cursor.fetchall()

    # 计算余弦相似度
    scored = []
    for row in rows:
        embedding = parse_embedding(row[5])
        score = cosine_similarity(query_vec, embedding)
        if math.isfinite(score) and score > 0:
            scored.append((row, score))

    # 排序并返回
    scored.sort(key=lambda x: x[1], reverse=True)

    return [
        MemorySearchResult(
            id=row[0],
            path=row[1],
            start_line=row[2],
            end_line=row[3],
            score=score,
            snippet=truncate_utf16_safe(row[4], snippet_max_chars),
            source=row[6],
        )
        for (row, score) in scored[:limit]
    ]


# ============================================================================
# 全文搜索实现
# ============================================================================

def search_keyword(
    db: sqlite3.Connection,
    fts_table: str,
    provider_model: Optional[str],
    query: str,
    limit: int,
    snippet_max_chars: int = SNIPPET_MAX_CHARS,
    build_fts_query: callable = build_fts_query,
    bm25_rank_to_score: callable = bm25_rank_to_score,
) -> list[MemorySearchResult]:
    """全文搜索实现 (基于 FTS5)

    Args:
        db: 数据库连接
        fts_table: FTS 表名
        provider_model: 提供商模型 (None 表示搜索所有模型)
        query: 搜索查询
        limit: 结果限制
        snippet_max_chars: 片段最大字符数
        build_fts_query: 查询构建函数
        bm25_rank_to_score: BM25 评分转换函数

    Returns:
        搜索结果列表
    """
    if limit <= 0:
        return []

    fts_query = build_fts_query(query)
    if not fts_query:
        return []

    cursor = db.cursor()

    # FTS-only 模式支持搜索所有模型
    model_clause = "AND model = ?" if provider_model else ""
    model_params = [provider_model] if provider_model else []

    cursor.execute(f"""
        SELECT id, path, source, start_line, end_line, text,
               bm25({fts_table}) AS rank
        FROM {fts_table}
        WHERE {fts_table} MATCH ? {model_clause}
        ORDER BY rank ASC
        LIMIT ?
    """, (fts_query, *model_params, limit))

    rows = cursor.fetchall()

    return [
        MemorySearchResult(
            id=row[0],
            path=row[1],
            start_line=row[3],
            end_line=row[4],
            score=bm25_rank_to_score(row[6]),
            snippet=truncate_utf16_safe(row[5], snippet_max_chars),
            source=row[2],
            citation=f"{row[1]}:L{row[3]}-L{row[4]}",
        )
        for row in rows
    ]


# ============================================================================
# 混合搜索实现
# ============================================================================

def merge_hybrid_results(
    vector_results: list[MemorySearchResult],
    keyword_results: list[MemorySearchResult],
    vector_weight: float = 0.7,
    text_weight: float = 0.3,
    max_results: int = 20,
    min_score: float = 0.3,
) -> list[MemorySearchResult]:
    """合并混合搜索结果

    使用加权平均法合并向量和全文搜索结果

    Args:
        vector_results: 向量搜索结果
        keyword_results: 全文搜索结果
        vector_weight: 向量权重
        text_weight: 文本权重
        max_results: 最大结果数
        min_score: 最小分数阈值

    Returns:
        合并后的搜索结果
    """
    # 使用 RRFP (Reciprocal Rank Fusion) 或简单加权平均
    results_by_id: dict[str, dict] = {}

    # 添加向量搜索结果
    for i, result in enumerate(vector_results):
        key = f"{result.source}:{result.path}:{result.start_line}:{result.end_line}"
        results_by_id[key] = {
            "result": result,
            "vector_score": result.score,
            "text_score": 0.0,
            "rank_vector": i + 1,
            "rank_text": None,
        }

    # 添加全文搜索结果并更新已有结果
    for i, result in enumerate(keyword_results):
        key = f"{result.source}:{result.path}:{result.start_line}:{result.end_line}"
        if key in results_by_id:
            results_by_id[key]["text_score"] = result.score
            results_by_id[key]["rank_text"] = i + 1
        else:
            results_by_id[key] = {
                "result": result,
                "vector_score": 0.0,
                "text_score": result.score,
                "rank_vector": None,
                "rank_text": i + 1,
            }

    # 计算加权分数
    for entry in results_by_id.values():
        # 使用排名来计算最终分数
        rank_vector = entry["rank_vector"]
        rank_text = entry["rank_text"]

        # 将排名转换为分数 (排名越高分数越高)
        vector_norm = 1.0 / rank_vector if rank_vector else 0.0
        text_norm = 1.0 / rank_text if rank_text else 0.0

        # 加权平均
        entry["combined_score"] = (
            vector_norm * vector_weight * entry["vector_score"] +
            text_norm * text_weight * entry["text_score"]
        )

    # 排序并过滤
    sorted_results = sorted(
        results_by_id.values(),
        key=lambda x: x["combined_score"],
        reverse=True,
    )

    return [
        entry["result"]
        for entry in sorted_results
        if entry["combined_score"] >= min_score
    ][:max_results]
