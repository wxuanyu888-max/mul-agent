"""Memory Handler - 记忆管理处理器"""
from typing import Any, Dict

from .base import BaseHandler


class MemoryHandler(BaseHandler):
    """记忆管理处理器"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}
        action = params.get("action", "")
        memory_type = params.get("memory_type", "long_term")
        # 使用 get_agent_id 方法获取 agent_id（优先从 params，其次从 self.agent_id，最后默认 wangyue）
        agent_id = self.get_agent_id(params)
        content = params.get("content", {})

        if not action:
            return {"status": "error", "error_code": 1004, "message": "Missing: action"}

        from mul_agent.memory.memory import Memory
        memory_config = self.config_manager.load(agent_id, "memory")
        memory = Memory(agent_id=agent_id, config=memory_config)

        if action == "write":
            if not content:
                return {"status": "error", "error_code": 1004, "message": "Missing: content"}
            return {"action": "write", "memory_id": memory.write(memory_type, content), "status": "success"}
        elif action == "read":
            return {"action": "read", "memory": memory.read(memory_type, params.get("memory_id")), "status": "success"}
        elif action == "list":
            memories = memory.list_memories(memory_type)
            return {"action": "list", "count": len(memories), "memories": memories, "status": "success"}
        elif action == "search":
            query = params.get("query", "")
            if not query:
                return {"status": "error", "error_code": 1004, "message": "Missing: query"}
            return {"action": "search", "query": query, "results": memory.search(query), "status": "success"}
        else:
            return {"status": "error", "error_code": 1005, "message": f"Unknown action: {action}"}
