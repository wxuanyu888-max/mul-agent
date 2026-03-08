"""Create User Handler - 创建新 Agent 处理器"""
from typing import Any, Dict
import uuid

from .base import BaseHandler


class CreateUserHandler(BaseHandler):
    """创建新 Agent 处理器"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}

        agent_id = params.get("agent_id") or f"agent_{uuid.uuid4().hex[:8]}"
        name = params.get("name", agent_id)
        role_type = params.get("role_type", "worker")
        personality = params.get("personality", "Helpful assistant")

        config = {"agent_id": agent_id, "name": name, "role_type": role_type, "personality": personality}

        try:
            for config_type, data in self._generate_agent_configs(agent_id, config).items():
                self.config_manager.save(agent_id, config_type, data)
            return {"agent_id": agent_id, "name": name, "role_type": role_type, "status": "created", "message": f"Agent {agent_id} created!"}
        except Exception as e:
            return {"status": "error", "error_code": 1005, "message": f"Failed: {str(e)}"}

    def _generate_agent_configs(self, agent_id: str, config: Dict) -> Dict:
        return {
            "soul": {"version": "1.0", "name": agent_id, "description": "Agent", "core_traits": {"personality": config.get("personality"), "values": ["efficiency"], "goals": ["assist_user"]}, "evolution_rules": {"can_modify_self": False}},
            "user": {"version": "1.0", "agent_id": agent_id, "role": {"type": config.get("role_type"), "title": config.get("name")}, "capabilities": {"max_team_size": 1, "can_create_agent": False}, "tools": {"enabled": ["bash"]}},
            "skill": {"version": "1.0", "agent_id": agent_id, "skills": [], "skill_tree": {}},
            "memory": {"version": "1.0", "agent_id": agent_id, "memory_strategy": {"short_term": {"storage": "session"}, "long_term": {"storage": "file"}}}
        }
