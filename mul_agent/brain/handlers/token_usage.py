"""Token Usage Handler - Token 使用统计处理器"""
from typing import Any, Dict

from .base import BaseHandler


class TokenUsageHandler(BaseHandler):
    """Token 使用统计处理器"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from mul_agent.brain.token_usage import TokenUsageCenter

        action = params.get("action", "list")
        agent_id = params.get("agent_id")
        center = TokenUsageCenter(self.config_manager)

        if action == "list":
            return {"status": "success", "action": "list", "data": center.get_all_agents_usage()}
        elif action == "get":
            if not agent_id:
                return {"status": "error", "error_code": 3001, "message": "Missing agent_id"}
            return {"status": "success", "action": "get", "agent_id": agent_id, "data": {"summary": center.get_usage_summary(agent_id), "details": center.get_usage(agent_id)}}
        elif action == "reset":
            if not agent_id:
                return {"status": "error", "error_code": 3001, "message": "Missing agent_id"}
            return {"status": "success" if center.reset_usage(agent_id) else "error", "action": "reset", "agent_id": agent_id}
        else:
            return {"status": "error", "error_code": 3002, "message": f"Unknown action: {action}"}
