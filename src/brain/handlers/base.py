"""Base Handler - 处理器基类"""
from typing import Any, Dict


class BaseHandler:
    """所有处理器的基类"""

    def __init__(self, config_manager, agent_id: str = None):
        self.config_manager = config_manager
        self.agent_id = agent_id

    def get_agent_id(self, params: Dict[str, Any] = None) -> str:
        """获取 agent_id：优先从 params 获取，其次从 self.agent_id 获取，最后使用默认值

        Args:
            params: 请求参数（可能包含 agent_id）

        Returns:
            str: agent_id
        """
        if params and params.get("agent_id"):
            return params.get("agent_id")
        if self.agent_id:
            return self.agent_id
        # 默认回退到 wangyue（主 Agent）
        return "wangyue"
