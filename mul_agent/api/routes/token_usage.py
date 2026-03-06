"""Token Usage API routes"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

from mul_agent.brain.config_manager import ConfigManager
from mul_agent.brain.token_usage import TokenUsageCenter

router = APIRouter()

# Initialize config manager
config_manager = ConfigManager()
token_center = TokenUsageCenter(config_manager)


class TokenUsageResetResponse(BaseModel):
    status: str
    message: str


@router.get("/token-usage")
async def get_all_token_usage() -> Dict[str, Any]:
    """Get token usage statistics for all agents"""
    try:
        all_usage = token_center.get_all_agents_usage()
        return {"all_usage": all_usage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get token usage: {str(e)}")


@router.get("/token-usage/{agent_id}")
async def get_agent_token_usage(agent_id: str) -> Dict[str, Any]:
    """Get detailed token usage statistics for a specific agent"""
    try:
        usage = token_center.get_usage(agent_id)
        summary = token_center.get_usage_summary(agent_id)
        return {
            "summary": summary,
            "details": {
                "by_model": usage.get("by_model", {}),
                "by_function": usage.get("by_function", {}),
                "by_date": usage.get("by_date", {})
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get token usage: {str(e)}")


@router.post("/token-usage/{agent_id}/reset")
async def reset_agent_token_usage(agent_id: str) -> Dict[str, str]:
    """Reset token usage statistics for a specific agent"""
    try:
        success = token_center.reset_usage(agent_id)
        if success:
            return {"status": "success", "message": f"Token usage reset for {agent_id}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to reset token usage")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset token usage: {str(e)}")
