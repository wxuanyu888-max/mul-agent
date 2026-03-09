"""Memory Indexer - 记忆索引器

实现记忆文件的分块、嵌入生成、索引同步等功能
基于 openclaw 的 manager-sync-ops.ts 和 manager-embedding-ops.ts 设计
"""

import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable

from .embeddings import EmbeddingProvider, compute_text_hash
from .memory_schema import get_db_connection


# ============================================================================
# 常量定义
# ============================================================================

# 分块配置
DEFAULT_CHUNK_SIZE = 500  # 每块最大行数
DEFAULT_CHUNK_OVERLAP = 50  # 块间重叠行数

# 分块大小限制 (字符数)
MAX_CHUNK_CHARS = 2000
MIN_CHUNK_CHARS = 10  # 降低最小字符数限制


# ============================================================================
# 类型定义
# ============================================================================

@dataclass
class TextChunk:
    """文本分块"""
    id: str
    path: str
    source: str  # "memory" | "sessions"
    start_line: int
    end_line: int
    text: str
    hash: str
    model: str
    embedding: list[float] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)


@dataclass
class FileEntry:
    """文件条目"""
    path: str
    source: str
    hash: str
    mtime: int
    size: int


# ============================================================================
# 文本分块工具
# ============================================================================

def chunk_text(
    text: str,
    path: str,
    source: str = "memory",
    model: str = "",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[TextChunk]:
    """将文本分割成重叠的分块

    Args:
        text: 要分块的文本
        path: 文件路径
        source: 来源类型
        model: 嵌入模型名称
        chunk_size: 每块最大行数
        chunk_overlap: 块间重叠行数

    Returns:
        分块列表
    """
    lines = text.split('\n')
    chunks = []

    if len(lines) <= chunk_size:
        # 文本足够小，不需要分块
        chunk_text_content = '\n'.join(lines)
        if len(chunk_text_content) >= MIN_CHUNK_CHARS:
            chunks.append(create_chunk(
                id=generate_chunk_id(path, 0, len(lines)),
                path=path,
                source=source,
                start_line=1,
                end_line=len(lines),
                text=chunk_text_content,
                model=model,
            ))
        return chunks

    # 分块处理
    start = 0
    line_num = 1

    while start < len(lines):
        end = min(start + chunk_size, len(lines))

        # 确保不会以不完整的代码块结尾 (针对 Markdown)
        # 但要限制最大搜索范围，避免无限扩展
        original_end = end
        max_search_end = min(start + chunk_size + 10, len(lines))  # 最多额外搜索 10 行

        while end < max_search_end and end < len(lines) and not is_good_break_point(lines, end):
            end += 1

        chunk_lines = lines[start:end]
        chunk_text_content = '\n'.join(chunk_lines)

        # 跳过太小的分块
        if len(chunk_text_content) >= MIN_CHUNK_CHARS:
            chunks.append(create_chunk(
                id=generate_chunk_id(path, start, end),
                path=path,
                source=source,
                start_line=line_num + start,
                end_line=line_num + end - 1,
                text=chunk_text_content,
                model=model,
            ))

        # 移动起始位置 (考虑重叠)
        if end >= len(lines):
            break
        start = end - chunk_overlap
        if start < 0:
            start = 0

    return chunks


def is_good_break_point(lines: list[str], index: int) -> bool:
    """检查是否是好的分块断点

    好的断点特征:
    - 空行
    - Markdown 标题前
    - 段落之间
    """
    if index >= len(lines):
        return True

    line = lines[index].strip()

    # 空行是好断点
    if not line:
        return True

    # Markdown 标题前是好断点
    if line.startswith('#'):
        return True

    # 列表项前是好断点
    if line.startswith(('-', '*', '+')) or re.match(r'^\d+\.', line):
        return True

    return False


def create_chunk(
    id: str,
    path: str,
    source: str,
    start_line: int,
    end_line: int,
    text: str,
    model: str,
) -> TextChunk:
    """创建文本分块"""
    return TextChunk(
        id=id,
        path=path,
        source=source,
        start_line=start_line,
        end_line=end_line,
        text=truncate_if_needed(text, MAX_CHUNK_CHARS),
        hash=generate_chunk_hash(text),
        model=model,
    )


def generate_chunk_id(path: str, start: int, end: int) -> str:
    """生成分块 ID"""
    content = f"{path}:{start}:{end}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def generate_chunk_hash(text: str) -> str:
    """生成分块哈希"""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def truncate_if_needed(text: str, max_chars: int) -> str:
    """必要时截断文本"""
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


# ============================================================================
# 嵌入缓存
# ============================================================================

class EmbeddingCache:
    """嵌入缓存管理器"""

    def __init__(self, db):
        self.db = db
        self.cache_table = "embedding_cache"

    def get(
        self,
        provider: str,
        model: str,
        provider_key: str,
        text_hash: str,
    ) -> Optional[list[float]]:
        """从缓存获取嵌入"""
        cursor = self.db.cursor()
        cursor.execute(f"""
            SELECT embedding, dims FROM {self.cache_table}
            WHERE provider = ? AND model = ? AND provider_key = ? AND hash = ?
        """, (provider, model, provider_key, text_hash))

        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except (json.JSONDecodeError, TypeError):
                # 处理逗号分隔的字符串格式
                return [float(x.strip()) for x in row[0].split(',')]

        return None

    def set(
        self,
        provider: str,
        model: str,
        provider_key: str,
        text_hash: str,
        embedding: list[float],
    ) -> None:
        """设置嵌入缓存"""
        cursor = self.db.cursor()
        cursor.execute(f"""
            INSERT OR REPLACE INTO {self.cache_table}
            (provider, model, provider_key, hash, embedding, dims, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            provider,
            model,
            provider_key,
            text_hash,
            json.dumps(embedding),
            len(embedding),
            int(time.time()),
        ))
        self.db.commit()

    def get_stats(self) -> dict:
        """获取缓存统计"""
        cursor = self.db.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {self.cache_table}")
        entries = cursor.fetchone()[0]

        cursor.execute(f"SELECT MAX(dims) FROM {self.cache_table}")
        max_dims = cursor.fetchone()[0] or 0

        return {
            "entries": entries,
            "max_dimensions": max_dims,
        }


# ============================================================================
# 嵌入生成
# ============================================================================

async def generate_embeddings(
    chunks: list[TextChunk],
    provider: EmbeddingProvider,
    cache: EmbeddingCache,
    batch_size: int = 32,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> list[TextChunk]:
    """为分块生成嵌入

    Args:
        chunks: 分块列表
        provider: 嵌入提供商
        cache: 嵌入缓存
        batch_size: 批量大小
        progress_callback: 进度回调

    Returns:
        带嵌入的分块列表
    """
    results = []
    provider_key = f"{provider.id}:{provider.model}"

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [chunk.text for chunk in batch]
        embeddings = []

        # 检查缓存并批量生成
        texts_to_embed = []
        indices_to_embed = []

        for j, (chunk, text) in enumerate(zip(batch, texts)):
            text_hash = compute_text_hash(text)
            cached = cache.get(provider.id, provider.model, provider_key, text_hash)
            if cached:
                embeddings.append(cached)
            else:
                texts_to_embed.append(text)
                indices_to_embed.append(j)
                embeddings.append(None)  # 占位符

        # 批量生成缺失的嵌入
        if texts_to_embed:
            try:
                new_embeddings = await provider.embed_batch(texts_to_embed)

                # 缓存新嵌入
                for text, embedding in zip(texts_to_embed, new_embeddings):
                    text_hash = compute_text_hash(text)
                    cache.set(provider.id, provider.model, provider_key, text_hash, embedding)

                # 填充结果
                for idx, embedding in zip(indices_to_embed, new_embeddings):
                    embeddings[idx] = embedding

            except Exception as e:
                # 如果批量失败，尝试逐个生成
                for idx, text in zip(indices_to_embed, texts_to_embed):
                    try:
                        embedding = await provider.embed_query(text)
                        text_hash = compute_text_hash(text)
                        cache.set(provider.id, provider.model, provider_key, text_hash, embedding)
                        embeddings[idx] = embedding
                    except Exception:
                        embeddings[idx] = [0.0] * 100  # 零向量作为后备

        # 将嵌入添加到分块
        for chunk, embedding in zip(batch, embeddings):
            chunk.embedding = embedding or [0.0] * 100
            results.append(chunk)

        # 进度回调
        if progress_callback:
            progress_callback(i + len(batch), len(chunks))

    return results


# ============================================================================
# 数据库操作
# ============================================================================

class MemoryIndexOperations:
    """记忆索引操作类"""

    def __init__(self, db):
        self.db = db
        self.cache = EmbeddingCache(db)

    def save_file(self, file: FileEntry) -> None:
        """保存文件条目"""
        cursor = self.db.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO files (path, source, hash, mtime, size)
            VALUES (?, ?, ?, ?, ?)
        """, (file.path, file.source, file.hash, file.mtime, file.size))
        self.db.commit()

    def save_chunk(self, chunk: TextChunk) -> None:
        """保存分块"""
        cursor = self.db.cursor()

        # 保存到 chunks 表
        cursor.execute("""
            INSERT OR REPLACE INTO chunks
            (id, path, source, start_line, end_line, hash, model, text, embedding, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            chunk.id,
            chunk.path,
            chunk.source,
            chunk.start_line,
            chunk.end_line,
            chunk.hash,
            chunk.model,
            chunk.text,
            json.dumps(chunk.embedding),
            int(chunk.updated_at),
        ))

        self.db.commit()

    def delete_chunks_for_path(self, path: str) -> None:
        """删除指定路径的所有分块"""
        cursor = self.db.cursor()
        cursor.execute("DELETE FROM chunks WHERE path = ?", (path,))
        cursor.execute("DELETE FROM files WHERE path = ?", (path,))
        self.db.commit()

    def list_all_files(self, source: str = "memory") -> list[FileEntry]:
        """列出所有文件"""
        cursor = self.db.cursor()
        cursor.execute("""
            SELECT path, source, hash, mtime, size FROM files WHERE source = ?
        """, (source,))

        return [
            FileEntry(
                path=row[0],
                source=row[1],
                hash=row[2],
                mtime=row[3],
                size=row[4],
            )
            for row in cursor.fetchall()
        ]

    def get_dirty_files(self, source: str = "memory") -> list[str]:
        """获取可能需要重新索引的文件路径"""
        # 这里可以实现更复杂的脏文件检测逻辑
        return self.list_all_files(source)


# ============================================================================
# 文件监听和同步
# ============================================================================

async def sync_memory_files(
    workspace_dir: str,
    index_ops: MemoryIndexOperations,
    provider: Optional[EmbeddingProvider],
    sources: list[str] = None,
    force: bool = False,
    progress_callback: Optional[Callable[[dict], None]] = None,
) -> dict:
    """同步记忆文件到索引

    Args:
        workspace_dir: 工作目录
        index_ops: 索引操作类
        provider: 嵌入提供商
        sources: 记忆来源列表
        force: 是否强制重新索引
        progress_callback: 进度回调

    Returns:
        同步结果统计
    """
    sources = sources or ["memory"]
    workspace = Path(workspace_dir)

    stats = {
        "files_processed": 0,
        "chunks_created": 0,
        "chunks_updated": 0,
        "chunks_deleted": 0,
        "errors": [],
    }

    for source in sources:
        if source == "memory":
            # 处理 MEMORY.md 和 memory/*.md
            memory_files = await find_memory_files(workspace)

            for file_path in memory_files:
                try:
                    result = await process_memory_file(
                        file_path=file_path,
                        workspace_dir=workspace,
                        index_ops=index_ops,
                        provider=provider,
                        force=force,
                    )
                    stats["files_processed"] += 1
                    stats["chunks_created"] += result.get("chunks_created", 0)

                    if progress_callback:
                        progress_callback({
                            "phase": "indexing",
                            "file": str(file_path),
                            "chunks": result.get("chunks_created", 0),
                        })

                except Exception as e:
                    stats["errors"].append(f"{file_path}: {str(e)}")

    return stats


async def find_memory_files(workspace: Path) -> list[Path]:
    """查找所有记忆文件"""
    memory_files = []

    # MEMORY.md
    memory_md = workspace / "MEMORY.md"
    if memory_md.exists():
        memory_files.append(memory_md)

    # memory/*.md
    memory_dir = workspace / "memory"
    if memory_dir.exists() and memory_dir.is_dir():
        for md_file in memory_dir.glob("*.md"):
            memory_files.append(md_file)

    return memory_files


async def process_memory_file(
    file_path: Path,
    workspace_dir: Path,
    index_ops: MemoryIndexOperations,
    provider: Optional[EmbeddingProvider],
    force: bool = False,
) -> dict:
    """处理单个记忆文件"""
    # 读取文件
    content = file_path.read_text(encoding='utf-8')

    # 计算文件哈希
    file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    file_stat = file_path.stat()

    # 检查是否需要更新
    if not force:
        existing = index_ops.get_dirty_files()
        # TODO: 实现更智能的变更检测

    # 分块
    rel_path = str(file_path.relative_to(workspace_dir))
    chunks = chunk_text(
        text=content,
        path=rel_path,
        source="memory",
        model=provider.model if provider else "none",
    )

    # 生成嵌入
    if provider:
        chunks = await generate_embeddings(
            chunks=chunks,
            provider=provider,
            cache=index_ops.cache,
            progress_callback=lambda done, total: None,
        )

    # 保存到数据库
    for chunk in chunks:
        index_ops.save_chunk(chunk)

    # 保存文件条目
    index_ops.save_file(FileEntry(
        path=rel_path,
        source="memory",
        hash=file_hash,
        mtime=int(file_stat.st_mtime),
        size=file_stat.st_size,
    ))

    return {
        "path": rel_path,
        "chunks_created": len(chunks),
    }
