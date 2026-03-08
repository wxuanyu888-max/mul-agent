"""Base Hook - 钩子基类"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum
from dataclasses import dataclass, field
import time


class HookEvent(str, Enum):
    """钩子事件类型"""

    # 工具执行前后
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"

    # 会话生命周期
    SESSION_START = "session_start"
    SESSION_END = "session_end"

    # 消息处理
    PRE_MESSAGE = "pre_message"
    POST_MESSAGE = "post_message"

    # 路由处理
    PRE_ROUTE = "pre_route"
    POST_ROUTE = "post_route"

    # 技能执行
    PRE_SKILL_EXECUTE = "pre_skill_execute"
    POST_SKILL_EXECUTE = "post_skill_execute"


class HookPriority(int, Enum):
    """钩子优先级"""

    HIGH = 1      # 高优先级（最先执行）
    NORMAL = 5    # 普通优先级
    LOW = 10      # 低优先级（最后执行）


@dataclass
class HookContext:
    """钩子上下文

    Attributes:
        event: 事件类型
        agent_id: Agent ID
        data: 事件相关数据
        timestamp: 时间戳
        metadata: 元数据
    """
    event: HookEvent
    agent_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """获取数据"""
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """设置数据"""
        self.data[key] = value

    def has(self, key: str) -> bool:
        """检查是否存在键"""
        return key in self.data


class BaseHook(ABC):
    """所有钩子的基类"""

    # 钩子元数据
    hook_id: str = "base_hook"
    hook_name: str = "Base Hook"
    hook_version: str = "1.0.0"
    hook_description: str = "Base hook for all hooks"

    # 钩子配置
    enabled: bool = True
    priority: HookPriority = HookPriority.NORMAL
    events: List[HookEvent] = []  # 订阅的事件

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

    @abstractmethod
    def _initialize(self) -> None:
        """钩子初始化逻辑（由子类实现）"""
        pass

    @abstractmethod
    def execute(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """执行钩子

        Args:
            context: 钩子上下文

        Returns:
            Optional[Dict]: 处理结果（可以修改 context.data）
        """
        pass

    def supports_event(self, event: HookEvent) -> bool:
        """检查是否支持某个事件

        Args:
            event: 事件类型

        Returns:
            bool: 是否支持
        """
        return event in self.events

    def get_metadata(self) -> Dict[str, Any]:
        """获取钩子元数据

        Returns:
            Dict: 钩子元数据
        """
        return {
            "hook_id": self.hook_id,
            "hook_name": self.hook_name,
            "hook_version": self.hook_version,
            "hook_description": self.hook_description,
            "enabled": self.enabled,
            "priority": self.priority.value,
            "events": [e.value for e in self.events],
            "agent_id": self.agent_id,
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.hook_name} v{self.hook_version}"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"<{self.__class__.__name__}(id={self.hook_id}, events={self.events})>"


class PreToolUseHook(BaseHook):
    """PreToolUse 钩子基类"""

    events = [HookEvent.PRE_TOOL_USE]
    priority = HookPriority.HIGH

    @abstractmethod
    def on_pre_tool_use(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """工具执行前的处理

        Args:
            context: 钩子上下文，包含 tool_name, params 等

        Returns:
            Optional[Dict]: 可以修改参数或返回错误阻止执行
        """
        pass

    def execute(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """执行钩子"""
        return self.on_pre_tool_use(context)


class PostToolUseHook(BaseHook):
    """PostToolUse 钩子基类"""

    events = [HookEvent.POST_TOOL_USE]
    priority = HookPriority.NORMAL

    @abstractmethod
    def on_post_tool_use(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """工具执行后的处理

        Args:
            context: 钩子上下文，包含 tool_name, result 等

        Returns:
            Optional[Dict]: 可以修改结果或执行后续操作
        """
        pass

    def execute(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """执行钩子"""
        return self.on_post_tool_use(context)


class SessionStartHook(BaseHook):
    """SessionStart 钩子基类"""

    events = [HookEvent.SESSION_START]
    priority = HookPriority.HIGH

    @abstractmethod
    def on_session_start(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """会话开始时的处理

        Args:
            context: 钩子上下文

        Returns:
            Optional[Dict]: 初始化结果
        """
        pass

    def execute(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """执行钩子"""
        return self.on_session_start(context)


class SessionEndHook(BaseHook):
    """SessionEnd 钩子基类"""

    events = [HookEvent.SESSION_END]
    priority = HookPriority.LOW

    @abstractmethod
    def on_session_end(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """会话结束时的处理

        Args:
            context: 钩子上下文

        Returns:
            Optional[Dict]: 清理结果
        """
        pass

    def execute(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """执行钩子"""
        return self.on_session_end(context)
