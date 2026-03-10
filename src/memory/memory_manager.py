"""Memory Manager - 记忆管理器

核心记忆索引和搜索系统：
1. SQLite + sqlite-vec 向量搜索
2. FTS5 全文搜索
3. 混合搜索（向量 + 全文）
4. 嵌入缓存
5. 文件监控和同步
"""

import os
import json
import hashlib
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import threading

from .embeddings import EmbeddingProvider, sanitize_and_normalize_embedding
from ..logging import get_subsystem_logger, LogLevel

# 初始化子系统日志记录器
logger = get_subsystem_logger("memory")


# 常量
SNIPPET_MAX_CHARS = 700
VECTOR_TABLE = "chunks_vec"
FTS_TABLE = "chunks_fts"
EMBEDDING_CACHE_TABLE = "embedding_cache"
BATCH_FAILURE_LIMIT = 2


@dataclass
class MemorySearchResult:
    """记忆搜索结果"""
    path: str
    start_line: int
    end_line: int
    score: float
    snippet: str
    source: str  # "memory" | "sessions"
    citation: Optional[str] = None
    id: Optional[str] = None


@dataclass
class MemoryProviderStatus:
    """记忆提供商状态"""
    backend: str = "builtin"  # "builtin" | "qmd"
    provider: str = ""
    model: Optional[str] = None
    requested_provider: Optional[str] = None
    files: int = 0
    chunks: int = 0
    dirty: bool = False
    workspace_dir: Optional[str] = None
    db_path: Optional[str] = None
    extra_paths: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    cache: Optional[Dict[str, Any]] = None
    fts: Optional[Dict[str, Any]] = None
    fallback: Optional[Dict[str, str]] = None
    vector: Optional[Dict[str, Any]] = None
    batch: Optional[Dict[str, Any]] = None


class MemoryIndexManager:
    """记忆索引管理器"""

    def __init__(
        self,
        agent_id: str,
        workspace_dir: str,
        db_path: Optional[str] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        fts_enabled: bool = True,
        cache_enabled: bool = True,
        max_cache_entries: int = 10000
    ):
        """初始化记忆索引管理器

        Args:
            agent_id: Agent ID
            workspace_dir: 工作空间目录
            db_path: 数据库路径（可选）
            embedding_provider: 嵌入提供商
            fts_enabled: 是否启用 FTS
            cache_enabled: 是否启用缓存
            max_cache_entries: 最大缓存条目数
        """
        self.agent_id = agent_id
        self.workspace_dir = Path(workspace_dir)
        self.provider = embedding_provider
        self.fts_enabled = fts_enabled
        self.cache_enabled = cache_enabled
        self.max_cache_entries = max_cache_entries

        # 数据库路径
        if db_path:
            self.db_path = Path(db_path)
        else:
            storage_path = self.workspace_dir.parent / "storage" / "memory"
            storage_path.mkdir(parents=True, exist_ok=True)
            self.db_path = storage_path / f"{agent_id}.db"

        # 来源
        self.sources: Set[str] = {"memory"}

        # 向量状态
        self.vector_available: Optional[bool] = None
        self.vector_dims: Optional[int] = None
        self.vector_error: Optional[str] = None

        # FTS 状态
        self.fts_available: bool = False
        self.fts_error: Optional[str] = None

        # 打开数据库
        self.db = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._lock = threading.Lock()

        # 初始化 schema
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """确保数据库 schema 存在"""
        with self._lock:
            # 元数据表
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            # 文件表
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    path TEXT PRIMARY KEY,
                    source TEXT NOT NULL DEFAULT 'memory',
                    hash TEXT NOT NULL,
                    mtime INTEGER NOT NULL,
                    size INTEGER NOT NULL
                )
            """)

            # 块表
            self.db.execute("""
                CREATE TABLE IF NOT EXISTS chunks (
                    id TEXT PRIMARY KEY,
                    path TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'memory',
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    hash TEXT NOT NULL,
                    model TEXT NOT NULL,
                    text TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)

            # 嵌入缓存表
            self.db.execute(f"""
                CREATE TABLE IF NOT EXISTS {EMBEDDING_CACHE_TABLE} (
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    provider_key TEXT NOT NULL,
                    hash TEXT NOT NULL,
                    embedding TEXT NOT NULL,
                    dims INTEGER,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (provider, model, provider_key, hash)
                )
            """)
            self.db.execute(f"""
                CREATE INDEX IF NOT EXISTS idx_embedding_cache_updated_at
                ON {EMBEDDING_CACHE_TABLE}(updated_at)
            """)

            # 确保 source 列存在
            self._ensure_column("files", "source", "TEXT NOT NULL DEFAULT 'memory'")
            self._ensure_column("chunks", "source", "TEXT NOT NULL DEFAULT 'memory'")

            # 索引
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path)")
            self.db.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source)")

            # 创建 FTS 表
            if self.fts_enabled:
                try:
                    self.db.execute(f"""
                        CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE} USING fts5(
                            text,
                            id UNINDEXED,
                            path UNINDEXED,
                            source UNINDEXED,
                            model UNINDEXED,
                            start_line UNINDEXED,
                            end_line UNINDEXED
                        )
                    """)
                    self.fts_available = True
                except sqlite3.Error as e:
                    self.fts_available = False
                    self.fts_error = str(e)

            self.db.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        """确保表列存在"""
        cursor = self.db.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]

        if column not in columns:
            self.db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            self.db.commit()

    def _compute_hash(self, text: str) -> str:
        """计算文本哈希"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]

    def _get_embedding_from_cache(self, text: str) -> Optional[List[float]]:
        """从缓存获取嵌入"""
        if not self.cache_enabled or not self.provider:
            return None

        text_hash = self._compute_hash(text)
        cursor = self.db.execute(f"""
            SELECT embedding, dims FROM {EMBEDDING_CACHE_TABLE}
            WHERE provider = ? AND model = ? AND hash = ?
            ORDER BY updated_at DESC LIMIT 1
        """, (self.provider.id, self.provider.model, text_hash))

        row = cursor.fetchone()
        if row:
            embedding_str = row[0]
            embedding = json.loads(embedding_str)
            return embedding
        return None

    def _save_embedding_to_cache(
        self,
        text: str,
        embedding: List[float],
        dims: int
    ) -> None:
        """保存嵌入到缓存"""
        if not self.cache_enabled or not self.provider:
            return

        text_hash = self._compute_hash(text)
        now = int(datetime.now().timestamp())

        self.db.execute(f"""
            INSERT OR REPLACE INTO {EMBEDDING_CACHE_TABLE}
            (provider, model, provider_key, hash, embedding, dims, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            self.provider.id,
            self.provider.model,
            self.agent_id,
            text_hash,
            json.dumps(embedding),
            dims,
            now
        ))
        self.db.commit()

        # 清理旧缓存
        if self.max_cache_entries:
            self.db.execute(f"""
                DELETE FROM {EMBEDDING_CACHE_TABLE}
                WHERE rowid NOT IN (
                    SELECT rowid FROM {EMBEDDING_CACHE_TABLE}
                    ORDER BY updated_at DESC
                    LIMIT ?
                )
            """, (self.max_cache_entries,))
            self.db.commit()

    async def get_embedding(self, text: str) -> List[float]:
        """获取文本嵌入（带缓存）"""
        if not self.provider:
            raise ValueError("No embedding provider configured")

        # 检查缓存
        cached = self._get_embedding_from_cache(text)
        if cached:
            return cached

        # 调用提供商
        embedding = await self.provider.embed_query(text)
        dims = len(embedding)

        # 保存到缓存
        self._save_embedding_to_cache(text, embedding, dims)

        return embedding

    def index_text(
        self,
        text: str,
        path: str,
        start_line: int = 0,
        end_line: int = 0,
        source: str = "memory"
    ) -> str:
        """索引文本到数据库

        Args:
            text: 要索引的文本
            path: 源文件路径
            start_line: 起始行号
            end_line: 结束行号
            source: 来源类型

        Returns:
            块 ID
        """
        # 生成块 ID
        chunk_hash = self._compute_hash(f"{path}:{start_line}:{end_line}:{text}")
        chunk_id = f"{chunk_hash[:16]}:{path.split('/')[-1]}"

        with self._lock:
            # 检查是否已存在
            cursor = self.db.execute(
                "SELECT id, hash FROM chunks WHERE id = ?",
                (chunk_id,)
            )
            existing = cursor.fetchone()

            if existing:
                # 如果哈希相同，跳过
                if existing[1] == self._compute_hash(text):
                    return chunk_id

            # 获取嵌入
            embedding = []
            model = "unknown"
            if self.provider:
                try:
                    import asyncio
                    loop = asyncio.get_event_loop()
                    embedding = loop.run_until_complete(self.get_embedding(text))
                    model = self.provider.model
                except Exception as e:
                    print(f"Warning: Failed to get embedding: {e}")

            now = int(datetime.now().timestamp())

            # 保存块
            self.db.execute("""
                INSERT OR REPLACE INTO chunks
                (id, path, source, start_line, end_line, hash, model, text, embedding, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                chunk_id, path, source, start_line, end_line,
                self._compute_hash(text), model, text, json.dumps(embedding), now
            ))

            # 保存到 FTS
            if self.fts_available:
                # 使用 chunk_id 的哈希作为整数 rowid
                rowid = int(self._compute_hash(chunk_id)[:8], 16)
                self.db.execute(f"""
                    INSERT OR REPLACE INTO {FTS_TABLE}
                    (rowid, id, path, source, model, start_line, end_line, text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (rowid, chunk_id, path, source, model, start_line, end_line, text))

            # 更新文件表
            self.db.execute("""
                INSERT OR REPLACE INTO files (path, source, hash, mtime, size)
                VALUES (?, ?, ?, ?, ?)
            """, (path, source, self._compute_hash(text), now, len(text)))

            self.db.commit()

        return chunk_id

    def search(
        self,
        query: str,
        max_results: int = 20,
        min_score: float = 0.3,
        use_hybrid: bool = True
    ) -> List[MemorySearchResult]:
        """搜索记忆

        Args:
            query: 搜索查询
            max_results: 最大结果数
            min_score: 最低分数阈值
            use_hybrid: 是否使用混合搜索

        Returns:
            搜索结果列表
        """
        results: List[MemorySearchResult] = []

        if use_hybrid and self.provider and self.fts_available:
            # 混合搜索：向量 + FTS
            vector_results = self._search_vector(query, max_results)
            fts_results = self._search_fts(query, max_results)

            # 合并结果
            results = self._merge_hybrid_results(vector_results, fts_results)
        elif self.provider:
            # 仅向量搜索
            results = self._search_vector(query, max_results)
        elif self.fts_available:
            # 尝试 FTS 搜索，如果失败则回退到简单搜索
            fts_results = self._search_fts(query, max_results)
            if fts_results:
                results = fts_results
            else:
                results = self._search_simple(query, max_results)
        else:
            # 简单文本搜索
            results = self._search_simple(query, max_results)

        # 应用分数阈值
        results = [r for r in results if r.score >= min_score]

        # 去重和排序
        return self._deduplicate_and_sort(results, query)[:max_results]

    def _search_vector(self, query: str, max_results: int) -> List[MemorySearchResult]:
        """向量搜索"""
        if not self.provider:
            return []

        try:
            import asyncio
            loop = asyncio.get_event_loop()
            query_embedding = loop.run_until_complete(self.get_embedding(query))
        except Exception as e:
            print(f"Vector search error: {e}")
            return []

        # SQLite 向量搜索（需要 sqlite-vec 扩展）
        try:
            # 尝试使用 sqlite-vec
            embedding_str = json.dumps(query_embedding)

            # 简单的余弦相似度计算
            cursor = self.db.execute("""
                SELECT id, path, source, start_line, end_line, text, embedding
                FROM chunks
                ORDER BY rowid
                LIMIT ?
            """, (max_results * 10,))  # 获取更多的候选

            results = []
            for row in cursor.fetchall():
                stored_embedding = json.loads(row[6])
                if stored_embedding:
                    score = self._cosine_similarity(query_embedding, stored_embedding)
                    if score > 0:
                        results.append(MemorySearchResult(
                            id=row[0],
                            path=row[1],
                            source=row[2],
                            start_line=row[3],
                            end_line=row[4],
                            text=row[5],
                            score=score,
                            snippet=row[5][:SNIPPET_MAX_CHARS]
                        ))

            return sorted(results, key=lambda x: x.score, reverse=True)[:max_results]
        except Exception as e:
            print(f"Vector search failed: {e}")
            return []

    def _search_fts(self, query: str, max_results: int) -> List[MemorySearchResult]:
        """FTS5 全文搜索"""
        if not self.fts_available:
            return []

        try:
            # FTS5 查询 - 使用简单的 LIKE 模式而不是 MATCH 以支持中文
            # FTS5 MATCH 对中文支持有限，这里使用 chunks 表的 LIKE 查询
            query_lower = query.lower()

            cursor = self.db.execute("""
                SELECT c.id, c.path, c.source, c.start_line, c.end_line, c.text
                FROM chunks c
                WHERE LOWER(c.text) LIKE ?
                ORDER BY c.updated_at DESC
                LIMIT ?
            """, (f"%{query_lower}%", max_results))

            results = []
            for row in cursor.fetchall():
                text = row[5]
                # 计算简单的相关度分数
                text_lower = text.lower()
                matches = text_lower.count(query_lower)

                # 分数计算：基于匹配次数和查询覆盖率
                # 至少匹配一次给 0.5 基础分，每次额外匹配加 0.1
                if matches > 0:
                    score = 0.5 + min(0.5, matches * 0.1)
                else:
                    score = 0.0

                results.append(MemorySearchResult(
                    id=row[0],
                    path=row[1],
                    source=row[2],
                    start_line=row[3],
                    end_line=row[4],
                    score=score,
                    snippet=text[:SNIPPET_MAX_CHARS]
                ))

            return results
        except sqlite3.Error as e:
            print(f"FTS search failed: {e}")
            return []

    def _search_simple(self, query: str, max_results: int) -> List[MemorySearchResult]:
        """简单文本搜索（无向量/FTS）"""
        query_lower = query.lower()

        cursor = self.db.execute("""
            SELECT id, path, source, start_line, end_line, text
            FROM chunks
            WHERE LOWER(text) LIKE ?
            LIMIT ?
        """, (f"%{query_lower}%", max_results * 5))

        results = []
        for row in cursor.fetchall():
            # 计算简单的相关度
            text = row[5]
            text_lower = text.lower()
            matches = text_lower.count(query_lower)

            # 分数计算：基于匹配次数
            if matches > 0:
                score = 0.5 + min(0.5, matches * 0.1)
            else:
                score = 0.0

            results.append(MemorySearchResult(
                id=row[0],
                path=row[1],
                source=row[2],
                start_line=row[3],
                end_line=row[4],
                score=score,
                snippet=text[:SNIPPET_MAX_CHARS]
            ))

        return results

    def _merge_hybrid_results(
        self,
        vector_results: List[MemorySearchResult],
        fts_results: List[MemorySearchResult]
    ) -> List[MemorySearchResult]:
        """合并混合搜索结果"""
        # 简单合并并重新排序
        all_results = vector_results + fts_results
        return all_results

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """计算余弦相似度"""
        import math

        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = math.sqrt(sum(x * x for x in a))
        magnitude_b = math.sqrt(sum(x * x for x in b))

        if magnitude_a < 1e-10 or magnitude_b < 1e-10:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)

    def _deduplicate_and_sort(
        self,
        results: List[MemorySearchResult],
        query: str
    ) -> List[MemorySearchResult]:
        """去重并排序"""
        seen_ids: Set[str] = set()
        unique_results: List[MemorySearchResult] = []

        for result in results:
            if result.id not in seen_ids:
                seen_ids.add(result.id)
                unique_results.append(result)

        # 按分数排序
        return sorted(unique_results, key=lambda x: x.score, reverse=True)

    def status(self) -> MemoryProviderStatus:
        """获取提供商状态"""
        # 统计文件和块
        cursor = self.db.execute("SELECT COUNT(*) FROM files")
        files_count = cursor.fetchone()[0]

        cursor = self.db.execute("SELECT COUNT(*) FROM chunks")
        chunks_count = cursor.fetchone()[0]

        # 来源统计
        source_counts = []
        for source in self.sources:
            cursor = self.db.execute(
                "SELECT COUNT(*), COUNT(DISTINCT path) FROM chunks WHERE source = ?",
                (source,)
            )
            row = cursor.fetchone()
            source_counts.append({
                "source": source,
                "chunks": row[0],
                "files": row[1]
            })

        # 缓存统计
        cache_info = None
        if self.cache_enabled:
            cursor = self.db.execute(
                f"SELECT COUNT(*) FROM {EMBEDDING_CACHE_TABLE}"
            )
            cache_info = {
                "enabled": True,
                "entries": cursor.fetchone()[0],
                "max_entries": self.max_cache_entries
            }

        # FTS 状态
        fts_info = {
            "enabled": self.fts_enabled,
            "available": self.fts_available
        }
        if self.fts_error:
            fts_info["error"] = self.fts_error

        # 向量状态
        vector_info = {
            "enabled": self.provider is not None,
            "available": self.provider is not None
        }
        if self.vector_error:
            vector_info["error"] = self.vector_error
        if self.vector_dims:
            vector_info["dims"] = self.vector_dims

        return MemoryProviderStatus(
            backend="builtin",
            provider=self.provider.id if self.provider else "none",
            model=self.provider.model if self.provider else None,
            requested_provider=self.provider.id if self.provider else None,
            files=files_count,
            chunks=chunks_count,
            workspace_dir=str(self.workspace_dir),
            db_path=str(self.db_path),
            sources=list(self.sources),
            cache=cache_info,
            fts=fts_info,
            vector=vector_info
        )

    def close(self) -> None:
        """关闭数据库连接"""
        with self._lock:
            self.db.close()


# 缓存管理器实例
_index_cache: Dict[str, MemoryIndexManager] = {}
_index_cache_pending: Dict[str, MemoryIndexManager] = {}


async def get_or_create_memory_index(
    agent_id: str,
    workspace_dir: str,
    db_path: Optional[str] = None,
    embedding_provider: Optional[EmbeddingProvider] = None,
    **kwargs
) -> MemoryIndexManager:
    """获取或创建记忆索引管理器（带缓存）"""
    cache_key = f"{agent_id}:{workspace_dir}"

    if cache_key in _index_cache:
        return _index_cache[cache_key]

    if cache_key in _index_cache_pending:
        # 等待创建完成
        while cache_key in _index_cache_pending:
            import asyncio
            await asyncio.sleep(0.1)
        return _index_cache.get(cache_key)

    # 创建新的实例
    _index_cache_pending[cache_key] = None  # 标记为正在创建

    try:
        manager = MemoryIndexManager(
            agent_id=agent_id,
            workspace_dir=workspace_dir,
            db_path=db_path,
            embedding_provider=embedding_provider,
            **kwargs
        )
        _index_cache[cache_key] = manager
        return manager
    finally:
        _index_cache_pending.pop(cache_key, None)
