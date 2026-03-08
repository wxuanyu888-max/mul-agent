"""Chat API routes"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
from mul_agent.brain.brain import Brain
from mul_agent.brain.config_manager import ConfigManager
from mul_agent.brain.conversation import ConversationManager

router = APIRouter()

# Initialize logger
logger = logging.getLogger("mul_agent")

# Initialize config manager - 所有存储都在 wang 目录
BASE_DIR = Path(__file__).parent.parent.parent.parent
WANG_DIR = BASE_DIR / "wang"
config_manager = ConfigManager(config_dir=WANG_DIR, wang_dir=WANG_DIR)

# Cache brain instances
_brain_cache = {}

# Conversation manager
conversation_manager = ConversationManager(storage_path="storage/conversations")


def get_brain(agent_id: str) -> Brain:
    """Get or create brain instance for agent"""
    if agent_id not in _brain_cache:
        _brain_cache[agent_id] = Brain(agent_id, config_manager)
    return _brain_cache[agent_id]


class ChatRequest(BaseModel):
    message: str
    agent_id: Optional[str] = None
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: Optional[str] = None


class Session(BaseModel):
    session_id: str
    agent_id: str
    created_at: str
    last_message_at: str
    message_count: int
    preview: str


@router.post("/chat")
async def chat(request: ChatRequest):
    """Handle chat request"""
    import json as json_lib
    import re
    import time
    import httpx

    try:
        agent_id = request.agent_id or "wangyue"
        brain = get_brain(agent_id)

        logger.info(f"Chat request from agent: {agent_id}, message: {request.message[:50]}...")

        # Generate or use conversation_id
        conversation_id = request.conversation_id
        if not conversation_id:
            import uuid
            conversation_id = str(uuid.uuid4())

        # Update agent state to thinking
        start_time = time.time()
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8000/api/v1/agent/state/" + agent_id,
                json={
                    "status": "thinking",
                    "current_action": "Processing message",
                    "route": "chat",
                    "elapsed_ms": 0
                },
                timeout=5.0
            )

        logger.debug(f"Calling brain.think() for agent: {agent_id}")

        # Call brain think method
        result = brain.think(request.message)

        logger.info(f"Brain response for agent {agent_id}: route={result.get('route', 'unknown')}")

        # Save to conversation history
        conversation_manager.save_message(
            agent_id=agent_id,
            session_id=conversation_id,
            role="user",
            content=request.message
        )

        # Extract and save response
        response = ""
        if isinstance(result, dict):
            if result.get("status") == "error":
                error_msg = result.get("message", "Unknown error")
                error_code = result.get("error_code", 500)
                raise HTTPException(
                    status_code=500,
                    detail=f"Agent error ({error_code}): {error_msg}"
                )

            # Extract response from different result structures
            response = (
                result.get("response", "")
                or result.get("content", "")
                or result.get("message", "")
            )

            # Handle nested structures
            if not response and result.get("data"):
                result_data = result.get("data", {})
                if isinstance(result_data, dict):
                    response = result_data.get("message", "") or result_data.get("output", "")

            if not response and result.get("result"):
                result_data = result.get("result", {})
                if isinstance(result_data, dict):
                    response = result_data.get("message", "") or result_data.get("output", "")

            # Parse JSON if response is a JSON string
            if response and isinstance(response, str) and response.strip().startswith("{"):
                try:
                    parsed = json_lib.loads(response)
                    if isinstance(parsed, dict):
                        response = parsed.get("message", response)
                except (json_lib.JSONDecodeError, TypeError):
                    pass

        if not response:
            response = str(result) if result else "No response generated"

        # Ensure response is a clean string
        if isinstance(response, dict):
            response = response.get("message", str(response))

        # Clean up (preserve Markdown)
        if isinstance(response, str):
            response = response.strip()
            if response.startswith('{') and response.endswith('}'):
                try:
                    parsed = json_lib.loads(response)
                    if isinstance(parsed, dict):
                        response = parsed.get("message", response)
                except (json_lib.JSONDecodeError, TypeError):
                    pass

        # Save assistant response to history
        conversation_manager.save_message(
            agent_id=agent_id,
            session_id=conversation_id,
            role="assistant",
            content=response
        )

        # Update agent state to completed
        elapsed_ms = int((time.time() - start_time) * 1000)
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://localhost:8000/api/v1/agent/state/" + agent_id,
                json={
                    "status": "completed",
                    "current_action": "Response sent",
                    "route": "chat",
                    "elapsed_ms": elapsed_ms
                },
                timeout=5.0
            )

        logger.info(f"Chat response sent successfully. Elapsed: {elapsed_ms}ms")

        return {
            "response": response,
            "conversation_id": conversation_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")


@router.get("/chat/history")
async def get_history(agent_id: str = "wangyue", session_id: str = None, limit: int = 50):
    """Get chat history for a specific session or all sessions"""
    try:
        if session_id:
            # Get history for specific session
            messages = conversation_manager.get_history(
                agent_id=agent_id,
                session_id=session_id,
                limit=limit
            )
            return {
                "session_id": session_id,
                "messages": messages,
                "total": len(messages)
            }
        else:
            # Get all sessions with their latest messages
            sessions = get_all_sessions(agent_id)
            return {
                "sessions": sessions,
                "total": len(sessions)
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")


@router.get("/chat/sessions")
async def get_sessions(agent_id: str = "wangyue"):
    """Get all chat sessions"""
    try:
        sessions = get_all_sessions(agent_id)
        return {
            "sessions": sessions,
            "total": len(sessions)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get sessions: {str(e)}")


@router.get("/chat/session/{session_id}")
async def get_session_messages(agent_id: str = "wangyue", session_id: str = None, limit: int = 100):
    """Get messages for a specific session"""
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        messages = conversation_manager.get_history(
            agent_id=agent_id,
            session_id=session_id,
            limit=limit
        )
        return {
            "session_id": session_id,
            "messages": messages,
            "total": len(messages)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session messages: {str(e)}")


@router.delete("/chat/session/{session_id}")
async def delete_session(agent_id: str = "wangyue", session_id: str = None):
    """Delete a specific session"""
    try:
        if not session_id:
            raise HTTPException(status_code=400, detail="session_id is required")

        import shutil
        conv_path = conversation_manager._get_conversation_path(agent_id, session_id)
        if conv_path.exists():
            shutil.rmtree(conv_path)
        return {
            "status": "success",
            "message": f"Session {session_id} deleted"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")


def get_all_sessions(agent_id: str) -> List[dict]:
    """Get all sessions for an agent with metadata"""
    import os
    from datetime import datetime

    sessions = []
    conv_base = conversation_manager.base_path / agent_id

    if not conv_base.exists():
        return sessions

    # Get all session directories
    for session_dir in conv_base.iterdir():
        if not session_dir.is_dir():
            continue

        session_id = session_dir.name

        # Find all message files and get timestamps
        message_files = sorted(session_dir.glob("*.jsonl"))
        if not message_files:
            continue

        # Get created_at from first file
        created_at = datetime.fromtimestamp(
            message_files[0].stat().st_mtime
        ).isoformat()

        # Get last_message_at from last file
        last_message_at = datetime.fromtimestamp(
            message_files[-1].stat().st_mtime
        ).isoformat()

        # Count total messages
        message_count = 0
        first_message = ""
        last_message = ""

        for msg_file in message_files:
            try:
                with open(msg_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    message_count += len(lines)

                    if lines and not first_message:
                        try:
                            first_msg = json.loads(lines[0].strip())
                            first_message = first_msg.get("content", "")[:100]
                        except:
                            pass

                    if lines:
                        try:
                            last_msg = json.loads(lines[-1].strip())
                            last_message = last_msg.get("content", "")[:100]
                        except:
                            pass
            except:
                continue

        sessions.append({
            "session_id": session_id,
            "agent_id": agent_id,
            "created_at": created_at,
            "last_message_at": last_message_at,
            "message_count": message_count,
            "preview": last_message,
            "first_message": first_message
        })

    # Sort by last_message_at, most recent first
    sessions.sort(key=lambda x: x["last_message_at"], reverse=True)
    return sessions
