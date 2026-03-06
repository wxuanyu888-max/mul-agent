"""Chat API routes"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    agent_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: Optional[str] = None


@router.post("/chat")
async def chat(request: ChatRequest):
    """Handle chat request"""
    return {
        "response": f"收到消息：{request.message}",
        "conversation_id": request.conversation_id or "default"
    }


@router.get("/chat/history")
async def get_history(limit: int = 20):
    """Get chat history"""
    return {"history": [], "total": 0}


@router.get("/chat/sessions")
async def get_sessions():
    """Get chat sessions"""
    return {"sessions": []}
