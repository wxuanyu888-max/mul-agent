"""Agent Repository - Agent 配置数据访问"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseRepository


class AgentRepository(BaseRepository):
    """Agent 配置 Repository

    负责 Agent 配置文件的 CRUD 操作
    """

    CONFIG_TYPES = ["soul", "user", "skill", "memory", "prompt"]

    def __init__(self, config_manager):
        """初始化 Repository

        Args:
            config_manager: ConfigManager 实例
        """
        self.config_manager = config_manager

    def find_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取 Agent 的所有配置

        Args:
            agent_id: Agent ID

        Returns:
            Agent 配置字典，如果不存在则返回 None
        """
        try:
            return self.config_manager.load_all(agent_id)
        except Exception:
            return None

    def find_by_type(self, agent_id: str, config_type: str) -> Optional[Dict[str, Any]]:
        """获取 Agent 指定类型的配置

        Args:
            agent_id: Agent ID
            config_type: 配置类型 (soul/user/skill/memory/prompt)

        Returns:
            配置字典，如果不存在则返回 None
        """
        if config_type not in self.CONFIG_TYPES:
            raise ValueError(f"Invalid config type: {config_type}")

        try:
            return self.config_manager.load(agent_id, config_type)
        except Exception:
            return None

    def find_text_content(self, agent_id: str, config_type: str) -> Optional[str]:
        """获取配置文件的完整文本内容

        Args:
            agent_id: Agent ID
            config_type: 配置类型

        Returns:
            文本内容，如果不存在则返回 None
        """
        try:
            content = self.config_manager.load_text_content(agent_id, config_type)
            return content if content else None
        except Exception:
            return None

    def find_prompt(self, agent_id: str, prompt_name: str) -> Optional[str]:
        """获取指定提示词

        Args:
            agent_id: Agent ID
            prompt_name: 提示词名称

        Returns:
            提示词内容，如果不存在则返回 None
        """
        try:
            return self.config_manager.load_prompt(agent_id, prompt_name)
        except Exception:
            return None

    def find_all(self) -> List[str]:
        """列出所有 Agent ID

        Returns:
            Agent ID 列表
        """
        return self.config_manager.list_agents()

    def find_by_team(self, team_name: str) -> List[str]:
        """根据团队名查找 Agent

        Args:
            team_name: 团队名称

        Returns:
            Agent ID 列表
        """
        teams = self.config_manager.list_teams()
        return teams.get(team_name, [])

    def save(self, agent_id: str, data: Dict[str, Any]) -> bool:
        """保存 Agent 所有配置

        Args:
            agent_id: Agent ID
            data: 包含所有配置类型的字典

        Returns:
            是否保存成功
        """
        success = True
        for config_type in self.CONFIG_TYPES:
            if config_type in data:
                if not self.config_manager.save(agent_id, config_type, data[config_type]):
                    success = False
        return success

    def save_type(self, agent_id: str, config_type: str, data: Dict[str, Any]) -> bool:
        """保存指定类型的配置

        Args:
            agent_id: Agent ID
            config_type: 配置类型
            data: 配置数据

        Returns:
            是否保存成功
        """
        if config_type not in self.CONFIG_TYPES:
            raise ValueError(f"Invalid config type: {config_type}")

        return self.config_manager.save(agent_id, config_type, data)

    def save_prompt(self, agent_id: str, prompt_name: str, content: str) -> bool:
        """保存提示词

        Args:
            agent_id: Agent ID
            prompt_name: 提示词名称
            content: 提示词内容

        Returns:
            是否保存成功
        """
        return self.config_manager.save_prompt(agent_id, prompt_name, content)

    def delete(self, agent_id: str) -> bool:
        """删除 Agent 所有配置

        Args:
            agent_id: Agent ID

        Returns:
            是否删除成功
        """
        # TODO: 实现删除逻辑
        return False

    def delete_type(self, agent_id: str, config_type: str) -> bool:
        """删除指定类型的配置

        Args:
            agent_id: Agent ID
            config_type: 配置类型

        Returns:
            是否删除成功
        """
        # TODO: 实现删除逻辑
        return False

    def exists(self, agent_id: str) -> bool:
        """检查 Agent 是否存在

        Args:
            agent_id: Agent ID

        Returns:
            是否存在
        """
        return agent_id in self.find_all()

    def validate(self, agent_id: str) -> Dict[str, Any]:
        """验证 Agent 配置完整性

        Args:
            agent_id: Agent ID

        Returns:
            验证结果
        """
        return self.config_manager.validate_config(agent_id)

    def restore_snapshot(self, snapshot_name: str) -> bool:
        """恢复配置快照

        Args:
            snapshot_name: 快照名称

        Returns:
            是否恢复成功
        """
        return self.config_manager.restore_snapshot(snapshot_name)

    def list_snapshots(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """列出配置快照

        Args:
            agent_id: 可选的 Agent ID 用于过滤

        Returns:
            快照列表
        """
        return self.config_manager.list_snapshots(agent_id)
