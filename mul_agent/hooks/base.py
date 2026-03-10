"""Base Hook - 钩子基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class HookEvent(Enum):
    """钩子事件类型"""
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    PRE_MESSAGE = "pre_message"
    POST_MESSAGE = "post_message"
    PRE_COMMAND = "pre_command"
    POST_COMMAND = "post_command"


@dataclass
class HookMetadata:
    """钩子元数据"""
    hook_id: str = ""
    hook_name: str = ""
    hook_description: str = ""
    hook_version: str = "1.0.0"
    hook_tags: List[str] = None
    enabled: bool = True
    priority: int = 5  # 1-10，数字越大优先级越高
    events: List[HookEvent] = None

    def __post_init__(self):
        if self.hook_tags is None:
            self.hook_tags = []
        if self.events is None:
            self.events = []


class BaseHook(ABC):
    """所有钩子的基类"""

    # 钩子元数据（类级别默认值）
    hook_id: str = "base_hook"
    hook_name: str = "Base Hook"
    hook_description: str = "Base hook for all hooks"
    hook_version: str = "1.0.0"
    hook_tags: List[str] = []
    priority: int = 5
    enabled: bool = True

    def __init__(self, config_manager=None, agent_id: str = None):
        """初始化钩子

        Args:
            config_manager: 配置管理器
            agent_id: Agent ID
        """
        self.config_manager = config_manager
        self.agent_id = agent_id or "default"
        self._initialized = False

    def initialize(self) -> bool:
        """初始化钩子

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
            print(f"Error initializing hook {self.hook_id}: {e}")
            return False

    def _initialize(self) -> None:
        """钩子初始化逻辑（由子类覆盖）"""
        pass

    def get_metadata(self) -> HookMetadata:
        """获取钩子元数据

        Returns:
            HookMetadata: 钩子元数据
        """
        return HookMetadata(
            hook_id=self.hook_id,
            hook_name=self.hook_name,
            hook_description=self.hook_description,
            hook_version=self.hook_version,
            hook_tags=self.hook_tags.copy(),
            enabled=self.enabled,
            priority=self.priority,
        )

    # =========================================================================
    # 工具钩子
    # =========================================================================

    def pre_tool_use(self, route: str, params: dict) -> dict:
        """工具使用前钩子

        Args:
            route: 工具路由
            params: 工具参数

        Returns:
            dict: 修改后的参数（可以修改或返回原始参数）
        """
        return params

    def post_tool_use(self, route: str, params: dict, result: dict) -> dict:
        """工具使用后钩子

        Args:
            route: 工具路由
            params: 工具参数
            result: 工具执行结果

        Returns:
            dict: 修改后的结果（可以修改或返回原始结果）
        """
        return result

    # =========================================================================
    # 会话钩子
    # =========================================================================

    def session_start(self, context: dict) -> dict:
        """会话开始钩子

        Args:
            context: 会话上下文

        Returns:
            dict: 修改后的上下文
        """
        return context

    def session_end(self, context: dict) -> dict:
        """会话结束钩子

        Args:
            context: 会话上下文

        Returns:
            dict: 修改后的上下文
        """
        return context

    # =========================================================================
    # 消息钩子
    # =========================================================================

    def pre_message(self, context: dict) -> dict:
        """消息处理前钩子

        Args:
            context: 消息上下文

        Returns:
            dict: 修改后的上下文
        """
        return context

    def post_message(self, context: dict, response: dict) -> dict:
        """消息处理后钩子

        Args:
            context: 消息上下文
            response: 响应内容

        Returns:
            dict: 修改后的响应
        """
        return response

    # =========================================================================
    # 命令钩子
    # =========================================================================

    def pre_command(self, command: str, args: str) -> tuple:
        """命令执行前钩子

        Args:
            command: 命令名称
            args: 命令参数

        Returns:
            tuple: (command, args) 修改后的命令和参数
        """
        return command, args

    def post_command(self, command: str, args: str, result: dict) -> dict:
        """命令执行后钩子

        Args:
            command: 命令名称
            args: 命令参数
            result: 命令执行结果

        Returns:
            dict: 修改后的结果
        """
        return result

    # =========================================================================
    # 工具方法
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """将钩子转换为字典

        Returns:
            Dict: 钩子字典
        """
        return {
            **self.get_metadata().__dict__,
            "config_manager": self.config_manager.__class__.__name__ if self.config_manager else None,
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.hook_name} v{self.hook_version}"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"<{self.__class__.__name__}(id={self.hook_id}, name={self.hook_name})>"
