"""Key Repository - Agent Key 配置数据访问"""
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseRepository


class KeyRepository(BaseRepository):
    """Agent Key 配置 Repository

    负责 Agent LLM Key 配置的管理
    配置存储在 wang/agent-team/{agent_id}/user.md 的 llm_config 字段中
    """

    def __init__(self, config_manager):
        """初始化 Repository

        Args:
            config_manager: ConfigManager 实例
        """
        self.config_manager = config_manager

    def find_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取 Agent 的 Key 配置

        Args:
            agent_id: Agent ID

        Returns:
            Key 配置字典，如果不存在则返回 None
        """
        user_config = self.config_manager.load(agent_id, "user")
        return user_config.get("llm_config") if user_config else None

    def find_all(self) -> Dict[str, Dict[str, Any]]:
        """获取所有 Agent 的 Key 配置

        Returns:
            Agent ID 到 Key 配置的映射
        """
        result = {}
        for agent_id in self.config_manager.list_agents():
            key_config = self.find_by_id(agent_id)
            if key_config:
                result[agent_id] = key_config
        return result

    def save(self, agent_id: str, data: Dict[str, Any]) -> bool:
        """保存 Agent 的 Key 配置

        Args:
            agent_id: Agent ID
            data: Key 配置数据，包含 url, provider, model, key

        Returns:
            是否保存成功
        """
        # 验证必需字段
        required_fields = ["url", "provider", "model", "key"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # 获取当前的 user 配置
        user_config = self.config_manager.load(agent_id, "user")
        if not user_config:
            user_config = {}

        # 更新 llm_config
        user_config["llm_config"] = {
            "url": data["url"],
            "provider": data["provider"],
            "model": data["model"],
            "key": data["key"]
        }

        # 保存回 user.md
        return self.config_manager.save(agent_id, "user", user_config)

    def delete(self, agent_id: str) -> bool:
        """删除 Agent 的 Key 配置

        Args:
            agent_id: Agent ID

        Returns:
            是否删除成功
        """
        user_config = self.config_manager.load(agent_id, "user")
        if user_config and "llm_config" in user_config:
            del user_config["llm_config"]
            return self.config_manager.save(agent_id, "user", user_config)
        return True

    def exists(self, agent_id: str) -> bool:
        """检查 Agent 是否有 Key 配置

        Args:
            agent_id: Agent ID

        Returns:
            是否存在
        """
        key_config = self.find_by_id(agent_id)
        return key_config is not None

    def get_key(self, agent_id: str) -> Optional[str]:
        """获取 Agent 的 Key

        Args:
            agent_id: Agent ID

        Returns:
            Key 值，如果不存在则返回 None
        """
        key_config = self.find_by_id(agent_id)
        return key_config.get("key") if key_config else None

    def update_key(self, agent_id: str, key: str) -> bool:
        """仅更新 Agent 的 Key

        Args:
            agent_id: Agent ID
            key: 新的 Key 值

        Returns:
            是否更新成功
        """
        key_config = self.find_by_id(agent_id)
        if not key_config:
            # 如果不存在，需要创建完整的配置
            raise ValueError("Key config does not exist. Please create full config first.")

        key_config["key"] = key
        return self._save_key_config(agent_id, key_config)

    def update_all(self, agent_id: str, url: str, provider: str, model: str, key: str) -> bool:
        """更新所有 Key 配置参数

        Args:
            agent_id: Agent ID
            url: API URL
            provider: 提供商名称
            model: 模型名称
            key: API Key

        Returns:
            是否更新成功
        """
        key_config = {
            "url": url,
            "provider": provider,
            "model": model,
            "key": key
        }
        return self._save_key_config(agent_id, key_config)

    def _save_key_config(self, agent_id: str, key_config: Dict[str, Any]) -> bool:
        """保存 Key 配置

        Args:
            agent_id: Agent ID
            key_config: Key 配置数据

        Returns:
            是否保存成功
        """
        user_config = self.config_manager.load(agent_id, "user")
        if not user_config:
            user_config = {}

        user_config["llm_config"] = key_config
        return self.config_manager.save(agent_id, "user", user_config)
