"""Heart Handler - 自省/进化处理器"""
from typing import Any, Dict

from .base import BaseHandler


class HeartHandler(BaseHandler):
    """自省/进化处理器"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            params = {"trigger": "manual", "focus": "all"}
        trigger = params.get("trigger", "manual")
        focus = params.get("focus", "all")

        # 使用传入的 agent_id 或默认的 wangyue
        agent_id = self.get_agent_id(params)

        soul = self.config_manager.load(agent_id, "soul")
        user = self.config_manager.load(agent_id, "user")
        skill = self.config_manager.load(agent_id, "skill")

        current_state = {
            "role": user.get("role", {}).get("title", "未知"),
            "skills_count": len(skill.get("skills", [])),
            "soul_version": soul.get("version"),
            "can_modify_self": soul.get("evolution_rules", {}).get("can_modify_self", False)
        }

        return {
            "analysis": {"trigger": trigger, "focus": focus, "current_state": current_state, "issues_found": [], "analysis": "Self-evolution module loaded"},
            "can_evolve": current_state["can_modify_self"],
            "evolutions_applied": [],
            "status": "success"
        }
