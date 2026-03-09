"""Memory API Routes - 记忆系统 API 路由

提供记忆搜索、索引管理、状态查询等功能的 HTTP API
"""

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from .memory_manager import MemoryIndexManager, MemorySearchResult
from .embeddings import create_embedding_provider, EmbeddingProviderOptions

# ============================================================================
# 路由器配置
# ============================================================================

router = APIRouter(prefix="/memory", tags=["memory"])

# 全局管理器缓存
_manager_cache: dict[str, MemoryIndexManager] = {}

# 配置
MEMORY_STORAGE_PATH = Path(__file__).parent.parent.parent / "storage" / "memory_index"
MEMORY_STORAGE_PATH.mkdir(parents=True, exist_ok=True)


# ============================================================================
# 请求/响应模型
# ============================================================================

class MemorySearchRequest(BaseModel):
    """记忆搜索请求"""
    query: str = Field(..., description="搜索查询")
    agent_id: str = Field(default="wang", description="Agent ID")
    max_results: int = Field(default=20, description="最大结果数", ge=1, le=100)
    min_score: float = Field(default=0.3, description="最小分数阈值", ge=0, le=1)
    use_hybrid: bool = Field(default=True, description="是否使用混合搜索")


class MemorySearchResponse(BaseModel):
    """记忆搜索响应"""
    query: str
    results: list[dict]
    total: int
    provider: str
    model: Optional[str] = None


class MemoryStatusResponse(BaseModel):
    """记忆状态响应"""
    agent_id: str
    backend: str
    provider: str
    model: Optional[str] = None
    files: int
    chunks: int
    dirty: bool
    workspace_dir: Optional[str] = None
    db_path: Optional[str] = None
    fts_enabled: bool
    fts_available: bool


class MemoryIndexRequest(BaseModel):
    """记忆索引请求"""
    agent_id: str = Field(default="wang", description="Agent ID")
    force: bool = Field(default=False, description="是否强制重新索引")
    rebuild: bool = Field(default=False, description="是否重建索引")


class MemoryIndexResponse(BaseModel):
    """记忆索引响应"""
    status: str
    agent_id: str
    files_processed: int
    chunks_created: int
    errors: list[str] = Field(default_factory=list)


# ============================================================================
# 辅助函数
# ============================================================================

def get_or_create_manager(
    agent_id: str,
    workspace_dir: Optional[str] = None,
    embedding_api_key: Optional[str] = None,
    embedding_provider: str = "auto",
    embedding_model: str = "text-embedding-3-small",
) -> MemoryIndexManager:
    """获取或创建记忆管理器

    Args:
        agent_id: Agent ID
        workspace_dir: 工作目录
        embedding_api_key: 嵌入 API 密钥
        embedding_provider: 嵌入提供商
        embedding_model: 嵌入模型

    Returns:
        记忆管理器实例
    """
    cache_key = f"{agent_id}:{workspace_dir}"

    if cache_key in _manager_cache:
        return _manager_cache[cache_key]

    # 设置路径
    if workspace_dir:
        workspace = Path(workspace_dir)
    else:
        workspace = Path(__file__).parent.parent.parent / "wang" / "agent-team" / agent_id

    db_path = MEMORY_STORAGE_PATH / f"{agent_id}.db"

    # 创建嵌入提供商
    provider = None
    if embedding_api_key:
        try:
            loop = asyncio.get_event_loop()
            provider_result = loop.run_until_complete(
                create_embedding_provider(EmbeddingProviderOptions(
                    provider=embedding_provider,  # type: ignore
                    model=embedding_model,
                    fallback="none",
                    api_key=embedding_api_key,
                ))
            )
            provider = provider_result.provider
        except Exception:
            # 如果创建失败，使用 FTS-only 模式
            pass

    # 创建管理器
    manager = MemoryIndexManager(
        workspace_dir=str(workspace),
        db_path=str(db_path),
        provider=provider,
        fts_enabled=True,
        sources=["memory"],
    )

    _manager_cache[cache_key] = manager
    return manager


def search_result_to_dict(result: MemorySearchResult) -> dict:
    """将搜索结果转换为字典"""
    return {
        "id": result.id,
        "path": result.path,
        "start_line": result.start_line,
        "end_line": result.end_line,
        "score": round(result.score, 4),
        "snippet": result.snippet,
        "source": result.source,
        "citation": result.citation,
    }


# ============================================================================
# API 端点
# ============================================================================

@router.post("/search", response_model=MemorySearchResponse)
async def search_memory(request: MemorySearchRequest):
    """搜索记忆

    支持向量搜索、全文搜索和混合搜索模式。
    当嵌入提供商不可用时，自动降级为 FTS-only 模式。
    """
    try:
        manager = get_or_create_manager(agent_id=request.agent_id)

        results = manager.search(
            query=request.query,
            max_results=request.max_results,
            min_score=request.min_score,
            use_hybrid=request.use_hybrid,
        )

        status = manager.status()

        return MemorySearchResponse(
            query=request.query,
            results=[search_result_to_dict(r) for r in results],
            total=len(results),
            provider=status.provider,
            model=status.model,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/search", response_model=MemorySearchResponse)
async def search_memory_get(
    query: str = Query(..., description="搜索查询"),
    agent_id: str = Query(default="wang", description="Agent ID"),
    max_results: int = Query(default=20, description="最大结果数"),
    min_score: float = Query(default=0.3, description="最小分数阈值"),
    use_hybrid: bool = Query(default=True, description="是否使用混合搜索"),
):
    """搜索记忆 (GET 方式)"""
    request = MemorySearchRequest(
        query=query,
        agent_id=agent_id,
        max_results=max_results,
        min_score=min_score,
        use_hybrid=use_hybrid,
    )
    return await search_memory(request)


@router.get("/status", response_model=MemoryStatusResponse)
async def get_memory_status(agent_id: str = Query(default="wang", description="Agent ID")):
    """获取记忆索引状态

    返回当前索引的文件数、分块数、提供商信息等。
    """
    try:
        manager = get_or_create_manager(agent_id=agent_id)
        status = manager.status()

        return MemoryStatusResponse(
            agent_id=agent_id,
            backend=status.backend,
            provider=status.provider,
            model=status.model,
            files=status.files,
            chunks=status.chunks,
            dirty=status.dirty,
            workspace_dir=status.workspace_dir,
            db_path=status.db_path,
            fts_enabled=status.fts_enabled,
            fts_available=status.fts_available,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get status failed: {str(e)}")


@router.post("/index", response_model=MemoryIndexResponse)
async def index_memory(request: MemoryIndexRequest):
    """重建/更新记忆索引

    会扫描工作目录下的所有记忆文件 (MEMORY.md 和 memory/*.md),
    生成文本分块并计算嵌入向量。
    """
    from .memory_indexer import sync_memory_files, MemoryIndexOperations

    try:
        manager = get_or_create_manager(agent_id=request.agent_id)

        # 执行同步
        index_ops = MemoryIndexOperations(manager.db)

        # 运行同步
        from .memory_indexer import sync_memory_files

        # 注意：这里需要异步运行
        stats = await sync_memory_files(
            workspace_dir=manager.workspace_dir,
            index_ops=index_ops,
            provider=manager.provider,
            sources=["memory"],
            force=request.force,
        )

        return MemoryIndexResponse(
            status="success",
            agent_id=request.agent_id,
            files_processed=stats.get("files_processed", 0),
            chunks_created=stats.get("chunks_created", 0),
            errors=stats.get("errors", []),
        )
    except Exception as e:
        return MemoryIndexResponse(
            status="error",
            agent_id=request.agent_id,
            files_processed=0,
            chunks_created=0,
            errors=[str(e)],
        )


@router.post("/index/rebuild")
async def rebuild_memory_index(agent_id: str = Query(default="wang", description="Agent ID")):
    """重建记忆索引 (删除所有现有索引并重新创建)"""
    try:
        manager = get_or_create_manager(agent_id=agent_id)

        # 删除现有分块
        cursor = manager.db.cursor()
        cursor.execute("DELETE FROM chunks")
        cursor.execute("DELETE FROM files")
        manager.db.commit()

        # 重新索引
        from .memory_indexer import MemoryIndexOperations, sync_memory_files

        index_ops = MemoryIndexOperations(manager.db)
        stats = await sync_memory_files(
            workspace_dir=manager.workspace_dir,
            index_ops=index_ops,
            provider=manager.provider,
            sources=["memory"],
            force=True,
        )

        return {
            "status": "success",
            "agent_id": agent_id,
            "files_processed": stats.get("files_processed", 0),
            "chunks_created": stats.get("chunks_created", 0),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {str(e)}")


@router.delete("/cache")
async def clear_embedding_cache(agent_id: str = Query(default="wang", description="Agent ID")):
    """清除嵌入缓存"""
    try:
        manager = get_or_create_manager(agent_id=agent_id)

        cursor = manager.db.cursor()
        cursor.execute("DELETE FROM embedding_cache")
        manager.db.commit()

        return {
            "status": "success",
            "agent_id": agent_id,
            "message": "Embedding cache cleared",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear cache failed: {str(e)}")


@router.get("/stats")
async def get_memory_stats(agent_id: str = Query(default="wang", description="Agent ID")):
    """获取记忆统计信息"""
    try:
        manager = get_or_create_manager(agent_id=agent_id)

        # 获取缓存统计
        cache_stats = manager.cache.get_stats() if hasattr(manager, 'cache') else {}

        # 获取文件统计
        cursor = manager.db.cursor()
        cursor.execute("SELECT COUNT(DISTINCT path) FROM chunks")
        unique_files = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM chunks")
        total_chunks = cursor.fetchone()[0]

        cursor.execute("SELECT source, COUNT(*) FROM chunks GROUP BY source")
        by_source = {row[0]: row[1] for row in cursor.fetchall()}

        return {
            "agent_id": agent_id,
            "unique_files": unique_files,
            "total_chunks": total_chunks,
            "chunks_by_source": by_source,
            "embedding_cache": cache_stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get stats failed: {str(e)}")


# ============================================================================
# 清理
# ============================================================================

def cleanup_managers():
    """清理所有管理器 (关闭数据库连接)"""
    for manager in _manager_cache.values():
        try:
            manager.close()
        except Exception:
            pass
    _manager_cache.clear()
