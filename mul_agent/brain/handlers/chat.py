"""Chat Handler - 对话处理器"""
import re
from typing import Any, Dict

from .base import BaseHandler


class ChatHandler(BaseHandler):
    """Chat 对话处理器"""
    conversations: dict = {}

    def __init__(self, config_manager, agent_id: str = None):
        self.config_manager = config_manager
        self.agent_id = agent_id

    def _load_response_prompt(self, agent_id: str, prompt_name: str, default: str) -> str:
        """从配置加载响应 prompt

        加载优先级：
        1. 先从 wang/agent-team/{agent_id}/prompt.md 加载（Agent 自定义）
        2. 再从 wang/agent-team/.templates/prompt.md.template 加载（标准模板）
        3. 最后返回默认值
        """
        # 1. 尝试从 Agent 自定义的 prompt.md 加载
        loaded = self.config_manager.load_prompt(agent_id, prompt_name)
        if loaded:
            return loaded

        # 2. 从标准模板加载（config_manager.load_prompt 已经处理）
        # 如果 config_manager.load_prompt 返回 None，直接返回默认值
        return default

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}
        action = params.get("action", "send")
        # 使用 get_agent_id 方法获取 agent_id（优先从 params，其次从 self.agent_id，最后默认 wangyue）
        agent_id = self.get_agent_id(params)
        message = params.get("message", "")
        conversation_id = params.get("conversation_id")

        if action == "send":
            return self._handle_send(agent_id, message, conversation_id)
        elif action == "switch":
            return self._handle_switch(agent_id, conversation_id)
        elif action == "list":
            return self._handle_list(agent_id)
        elif action == "clear":
            return self._handle_clear(conversation_id)
        else:
            return {"status": "error", "error_code": 2001, "message": f"Unknown action: {action}"}

    def _handle_send(self, agent_id: str, message: str, conversation_id: str = None) -> Dict[str, Any]:
        if not conversation_id:
            conversation_id = f"{agent_id}_001"
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        try:
            agent_config = self.config_manager.load(agent_id, "user")
            soul_config = self.config_manager.load(agent_id, "soul")
        except Exception:
            return {"status": "error", "error_code": 2002, "message": f"Agent not found: {agent_id}"}
        personality = soul_config.get("core_traits", {}).get("personality", "Helpful assistant")
        role_title = agent_config.get("role", {}).get("title", "Assistant")
        system_prompt = self.config_manager.load_prompt(agent_id, "agent_chat") or f"You are {role_title}. Personality: {personality}"
        self.conversations[conversation_id].append({"role": "user", "content": message})
        response = self._generate_response(agent_id, message, self.conversations[conversation_id], system_prompt)
        self.conversations[conversation_id].append({"role": "assistant", "content": response["content"]})
        return {"status": "success", "action": "send", "conversation_id": conversation_id, "agent_id": agent_id, "response": response["content"], "history_count": len(self.conversations[conversation_id])}

    def _handle_switch(self, agent_id: str, conversation_id: str = None) -> Dict[str, Any]:
        try:
            agent_config = self.config_manager.load(agent_id, "user")
        except Exception:
            return {"status": "error", "error_code": 2002, "message": f"Agent not found: {agent_id}"}
        new_conversation_id = f"{agent_id}_001"
        if new_conversation_id not in self.conversations:
            self.conversations[new_conversation_id] = []
        return {"status": "success", "action": "switch", "agent_id": agent_id, "conversation_id": new_conversation_id, "role": agent_config.get("role", {}).get("title")}

    def _handle_list(self, agent_id: str = None) -> Dict[str, Any]:
        if agent_id:
            convs = [{"conversation_id": k, "messages": len(v)} for k, v in self.conversations.items() if k.startswith(agent_id)]
            return {"status": "success", "agent_id": agent_id, "conversations": convs}
        agents = self.config_manager.list_agents()
        return {"status": "success", "available_agents": agents, "active_conversations": list(self.conversations.keys())}

    def _handle_clear(self, conversation_id: str = None) -> Dict[str, Any]:
        if conversation_id:
            if conversation_id in self.conversations:
                del self.conversations[conversation_id]
                return {"status": "success", "message": f"Conversation {conversation_id} cleared"}
            return {"status": "error", "error_code": 2003, "message": f"Conversation not found: {conversation_id}"}
        self.conversations.clear()
        return {"status": "success", "message": "All conversations cleared"}

    def _generate_response(self, agent_id: str, message: str, history: list, system_prompt: str) -> Dict[str, Any]:
        from mul_agent.brain.llm import LLMClient
        llm = LLMClient(config_manager=self.config_manager, agent_id=agent_id)
        if llm.is_available():
            response = llm.chat(message=message, system_prompt=system_prompt, history=history[:-1])
            return {"content": response.get("content", "..."), "source": "llm"}
        message_lower = message.lower()
        if "coder" in agent_id.lower() or "developer" in agent_id.lower():
            return {"content": self._load_response_prompt(agent_id, "coder_greeting", "你好！我是编码助手。"), "source": "config"}
        elif "writer" in agent_id.lower():
            return {"content": self._load_response_prompt(agent_id, "writer_greeting", "你好！我是写作助手。"), "source": "config"}
        else:
            return {"content": self._load_response_prompt(agent_id, "greeting_style", "你好！"), "source": "config"}
