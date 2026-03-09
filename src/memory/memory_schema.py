"""Memory Schema - SQLite 数据库模式定义

基于 openclaw 的 memory-schema.ts 设计
支持向量搜索、全文搜索和嵌入缓存
"""

import sqlite3
from pathlib import Path
from typing import Tuple


def ensure_memory_index_schema(
    db: sqlite3.Connection,
    embedding_cache_table: str = "embedding_cache",
    fts_table: str = "chunks_fts",
    fts_enabled: bool = True,
) -> Tuple[bool, str | None]:
    """创建记忆索引的数据库模式

    Args:
        db: SQLite 数据库连接
        embedding_cache_table: 嵌入缓存表名
        fts_table: 全文搜索表名
        fts_enabled: 是否启用全文搜索

    Returns:
        (fts_available, fts_error) 元组
    """
    cursor = db.cursor()

    # 元数据表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)

    # 文件表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            source TEXT NOT NULL DEFAULT 'memory',
            hash TEXT NOT NULL,
            mtime INTEGER NOT NULL,
            size INTEGER NOT NULL
        )
    """)

    # 分块表 - 存储文本和嵌入向量
    cursor.execute("""
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

    # 嵌入缓存表 - 避免重复计算嵌入
    cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {embedding_cache_table} (
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

    # 嵌入缓存索引
    cursor.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_embedding_cache_updated_at
        ON {embedding_cache_table}(updated_at)
    """)

    # 尝试创建 FTS 虚拟表
    fts_available = False
    fts_error: str | None = None

    if fts_enabled:
        try:
            cursor.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {fts_table} USING fts5(
                    text,
                    id UNINDEXED,
                    path UNINDEXED,
                    source UNINDEXED,
                    model UNINDEXED,
                    start_line UNINDEXED,
                    end_line UNINDEXED
                )
            """)
            fts_available = True
        except sqlite3.Error as e:
            fts_available = False
            fts_error = str(e)

    # 确保 source 列存在 (向后兼容)
    _ensure_column(db, "files", "source", "TEXT NOT NULL DEFAULT 'memory'")
    _ensure_column(db, "chunks", "source", "TEXT NOT NULL DEFAULT 'memory'")

    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_path ON chunks(path)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source)")

    db.commit()

    return fts_available, fts_error


def _ensure_column(
    db: sqlite3.Connection,
    table: str,
    column: str,
    definition: str,
) -> None:
    """检查列是否存在，不存在则添加"""
    cursor = db.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]

    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        db.commit()


def get_db_connection(db_path: str | Path) -> sqlite3.Connection:
    """获取数据库连接

    Args:
        db_path: 数据库文件路径

    Returns:
        SQLite 数据库连接
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    db = sqlite3.connect(str(db_path))
    db.row_factory = sqlite3.Row

    # 启用外键
    db.execute("PRAGMA foreign_keys = ON")

    # 启用 WAL 模式以提高并发性能
    db.execute("PRAGMA journal_mode = WAL")

    return db
