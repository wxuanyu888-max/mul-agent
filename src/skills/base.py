"""Base Skill - 技能基类"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path


class BaseSkill(ABC):
    """所有技能的基类"""

    # 技能元数据
    skill_id: str = "base_skill"
    skill_name: str = "Base Skill"
    skill_version: str = "1.0.0"
    skill_description: str = "Base skill for all skills"
    skill_tags: List[str] = []  # 用于技能检索和分类

    # 技能配置
    enabled: bool = True
    priority: int = 5  # 1-10，数字越大优先级越高
    requires_confirmation: bool = False  # 是否需要用户确认

    def __init__(self, config_manager=None, agent_id: str = None):
        """初始化技能

        Args:
            config_manager: 配置管理器
            agent_id: Agent ID
        """
        self.config_manager = config_manager
        self.agent_id = agent_id or "default"
        self._initialized = False

    def initialize(self) -> bool:
        """初始化技能

        Returns:
            bool: 是否初始化成功
        """
        if self._initialized:
            return True

        try:
            self._initialize()
            self._initialized = True
            return True
        except Exception as e:
            print(f"Error initializing skill {self.skill_id}: {e}")
            return False

    @abstractmethod
    def _initialize(self) -> None:
        """技能初始化逻辑（由子类实现）"""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """执行技能

        Args:
            **kwargs: 执行参数

        Returns:
            Any: 执行结果
        """
        pass

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数

        Args:
            params: 参数字典

        Returns:
            bool: 参数是否有效
        """
        return True

    def get_metadata(self) -> Dict[str, Any]:
        """获取技能元数据

        Returns:
            Dict: 技能元数据
        """
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "skill_version": self.skill_version,
            "skill_description": self.skill_description,
            "skill_tags": self.skill_tags,
            "enabled": self.enabled,
            "priority": self.priority,
            "requires_confirmation": self.requires_confirmation,
            "agent_id": self.agent_id,
        }

    def to_dict(self) -> Dict[str, Any]:
        """将技能转换为字典

        Returns:
            Dict: 技能字典
        """
        return {
            **self.get_metadata(),
            "config_manager": self.config_manager.__class__.__name__ if self.config_manager else None,
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.skill_name} v{self.skill_version}"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"<{self.__class__.__name__}(id={self.skill_id}, name={self.skill_name})>"
