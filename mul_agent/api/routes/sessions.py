"""
Session API Routes - 会话 API 路由

使用 FastAPI 提供 RESTful 会话管理接口
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Literal, Generic, TypeVar
from datetime import datetime

from .session_manager import (
    SessionManager,
    SessionContext,
    SessionMessage,
    SessionRole,
    CompressionHint,
)

# ============================================================================
# 类型定义
# ============================================================================

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """成功响应"""
    success: bool = True
    data: T


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: str
    code: Optional[str] = None


# 请求/响应模型
class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    sessionId: Optional[str] = None
    agentId: Optional[str] = None
    title: Optional[str] = None
    initialMessages: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionMessageRequest(BaseModel):
    """添加消息请求"""
    role: SessionRole
    content: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class UpdateMetadataRequest(BaseModel):
    """更新元数据请求"""
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class SessionSummary(BaseModel):
    """会话摘要 (不含消息内容)"""
    id: str
    agentId: str
    title: Optional[str]
    createdAt: float
    updatedAt: float
    tokenCount: int
    messageCount: int
    needsCompression: bool


class SessionHistoryResponse(BaseModel):
    """会话历史响应"""
    sessionId: str
    messages: List[Dict[str, Any]]
    totalCount: int
    tokenCount: int


class AddMessageResponse(BaseModel):
    """添加消息响应"""
    sessionId: str
    messageCount: int
    tokenCount: int
    needsCompression: bool
    compressionReason: Optional[str]


# ============================================================================
# 路由工厂
# ============================================================================

def create_session_router(session_manager: SessionManager) -> APIRouter:
    """创建会话路由"""
    router = APIRouter(prefix="/sessions", tags=["sessions"])

    @router.get("", response_model=SuccessResponse[List[SessionSummary]])
    async def list_sessions(
        agentId: Optional[str] = Query(None, description="按 agent ID 过滤"),
        limit: Optional[int] = Query(None, ge=1, description="返回数量限制")
    ):
        """列出所有会话"""
        try:
            sessions = await session_manager.list_sessions(agentId)

            # 应用限制
            if limit:
                sessions = sessions[:limit]

            # 简化响应
            summary_sessions = [
                SessionSummary(
                    id=s.id,
                    agentId=s.agent_id,
                    title=s.title,
                    createdAt=s.created_at,
                    updatedAt=s.updated_at,
                    tokenCount=s.token_count,
                    messageCount=len(s.messages),
                    needsCompression=s.needs_compression,
                )
                for s in sessions
            ]

            return SuccessResponse(data=summary_sessions)

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/{session_id}", response_model=SuccessResponse[Dict[str, Any]])
    async def get_session(
        session_id: str,
        agentId: Optional[str] = Query(None, description="Agent ID"),
        maxMessages: Optional[int] = Query(None, ge=1, description="最大消息数")
    ):
        """获取会话详情"""
        try:
            session = await session_manager.load_session(
                session_id,
                agentId,
                maxMessages
            )
            return SuccessResponse(data=_session_to_dict(session))

        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Session not found")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("", response_model=SuccessResponse[Dict[str, Any]], status_code=201)
    async def create_session(request: CreateSessionRequest):
        """创建新会话"""
        try:
            session = await session_manager.create_session(
                session_id=request.sessionId,
                agent_id=request.agentId,
                title=request.title,
                initial_messages=request.initialMessages,
                metadata=request.metadata,
            )
            return SuccessResponse(data=_session_to_dict(session))

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.delete("/{session_id}", response_model=SuccessResponse[Dict[str, Any]])
    async def delete_session(
        session_id: str,
        agentId: Optional[str] = Query(None, description="Agent ID")
    ):
        """删除会话"""
        try:
            await session_manager.delete_session(session_id, agentId)
            return SuccessResponse(data={"deleted": True, "sessionId": session_id})

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/{session_id}/history", response_model=SuccessResponse[SessionHistoryResponse])
    async def get_session_history(
        session_id: str,
        agentId: Optional[str] = Query(None, description="Agent ID"),
        limit: Optional[int] = Query(None, ge=1, description="消息数量限制"),
        includeTools: Optional[bool] = Query(True, description="是否包含工具消息")
    ):
        """获取会话历史消息"""
        try:
            session = await session_manager.load_session(
                session_id,
                agentId,
                limit
            )

            messages = session.messages
            if not includeTools:
                messages = [m for m in messages if m.role != "tool"]

            return SuccessResponse(data=SessionHistoryResponse(
                sessionId=session_id,
                messages=[m.to_dict() for m in messages],
                totalCount=len(messages),
                tokenCount=session.token_count,
            ))

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post(
       ("/{session_id}/messages"),
        response_model=SuccessResponse[AddMessageResponse]
    )
    async def add_message(
        session_id: str,
        request: SessionMessageRequest,
        agentId: Optional[str] = Query(None, description="Agent ID")
    ):
        """添加消息到会话"""
        try:
            session = await session_manager.add_message(
                session_id,
                request.role,
                request.content,
                agentId,
                request.metadata,
            )

            return SuccessResponse(data=AddMessageResponse(
                sessionId=session_id,
                messageCount=len(session.messages),
                tokenCount=session.token_count,
                needsCompression=session.needs_compression,
                compressionReason=session.compression_reason if session.needs_compression else None,
            ))

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.put("/{session_id}/metadata", response_model=SuccessResponse[Dict[str, Any]])
    async def update_metadata(
        session_id: str,
        request: UpdateMetadataRequest,
        agentId: Optional[str] = Query(None, description="Agent ID")
    ):
        """更新会话元数据"""
        try:
            session = await session_manager.update_session_metadata(
                session_id,
                request.title,
                request.metadata,
                agentId,
            )
            return SuccessResponse(data=_session_to_dict(session))

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/{session_id}/compress", response_model=SuccessResponse[Dict[str, Any]])
    async def get_compress_hint(
        session_id: str,
        agentId: Optional[str] = Query(None, description="Agent ID")
    ):
        """获取压缩提示"""
        try:
            session = await session_manager.load_session(session_id, agentId)
            hint = session_manager.get_compression_hint(session)

            return SuccessResponse(data={
                "needsCompression": hint.needs_compression,
                "type": hint.compression_type,
                "currentTokens": hint.current_tokens,
                "targetTokens": hint.target_tokens,
                "reason": hint.reason,
                "prompt": hint.prompt,
            })

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return router


# ============================================================================
# 辅助函数
# ============================================================================

def _session_to_dict(session: SessionContext) -> Dict[str, Any]:
    """将会话上下文转换为字典"""
    return {
        "id": session.id,
        "agentId": session.agent_id,
        "title": session.title,
        "messages": [m.to_dict() for m in session.messages],
        "createdAt": session.created_at,
        "updatedAt": session.updated_at,
        "tokenCount": session.token_count,
        "bootstrapTokenCount": session.bootstrap_token_count,
        "needsCompression": session.needs_compression,
        "compressionReason": session.compression_reason,
        "metadata": session.metadata,
    }
