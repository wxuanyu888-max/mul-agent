"""插件系统类型定义"""

from typing import Any, Callable, Awaitable, Optional, List, Dict
from dataclasses import dataclass, field
from pathlib import Path
from enum import Enum


# ========== 插件清单 ==========

@dataclass
class PluginManifest:
    """插件清单"""
    name: str
    version: str
    description: str
    author: str
    entry: str  # 入口文件路径
    tools: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    commands: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)


# ========== 插件上下文 ==========

@dataclass
class PluginContext:
    """插件执行上下文"""
    agent_id: str
    session_id: str
    workspace_dir: Optional[Path] = None
    config: Optional[dict] = None
    user_id: Optional[str] = None


# ========== 工具注册 ==========

@dataclass
class ToolEntry:
    """工具条目"""
    name: str
    description: str
    schema: dict
    handler: Callable[..., Awaitable[Any]]
    optional: bool = False
    enabled: bool = True


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}

    def register(
        self,
        name: str,
        description: str,
        schema: dict,
        handler: Callable[..., Awaitable[Any]],
        optional: bool = False,
    ) -> None:
        """注册工具"""
        self._tools[name] = ToolEntry(
            name=name,
            description=description,
            schema=schema,
            handler=handler,
            optional=optional,
        )

    def get(self, name: str) -> Optional[ToolEntry]:
        """获取工具"""
        return self._tools.get(name)

    def list(self, enabled_only: bool = False) -> List[ToolEntry]:
        """列出所有工具"""
        tools = list(self._tools.values())
        if enabled_only:
            tools = [t for t in tools if t.enabled]
        return tools

    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            return True
        return False


# ========== Hook 注册 ==========

class HookPhase(str, Enum):
    """Hook 阶段"""
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    PRE_COMMAND = "pre_command"
    POST_COMMAND = "post_command"
    PRE_AGENT_RUN = "pre_agent_run"
    POST_AGENT_RUN = "post_agent_run"
    SESSION_START = "session_start"
    SESSION_END = "session_end"


@dataclass
class HookContext:
    """Hook 上下文"""
    phase: HookPhase
    agent_id: str
    session_id: str
    data: dict = field(default_factory=dict)
    result: Any = None
    error: Optional[Exception] = None


@dataclass
class HookEntry:
    """Hook 条目"""
    name: str
    phase: HookPhase
    handler: Callable[[HookContext], Awaitable[HookContext]]
    priority: int = 0  # 数字越大越先执行
    enabled: bool = True


class HookRegistry:
    """Hook 注册表"""

    def __init__(self):
        self._hooks: Dict[str, List[HookEntry]] = {}  # phase -> hooks

    def register(
        self,
        name: str,
        phase: str,
        handler: Callable[[HookContext], Awaitable[HookContext]],
        priority: int = 0,
    ) -> None:
        """注册 Hook"""
        phase_key = phase if isinstance(phase, str) else phase.value

        if phase_key not in self._hooks:
            self._hooks[phase_key] = []

        self._hooks[phase_key].append(HookEntry(
            name=name,
            phase=HookPhase(phase_key),
            handler=handler,
            priority=priority,
        ))

        # 按优先级排序
        self._hooks[phase_key].sort(key=lambda h: h.priority, reverse=True)

    def get(self, phase: str) -> List[HookEntry]:
        """获取指定阶段的 Hook"""
        return self._hooks.get(phase, [])

    def list(self) -> Dict[str, List[HookEntry]]:
        """列出所有 Hook"""
        return self._hooks.copy()


# ========== 命令注册 ==========

@dataclass
class CommandEntry:
    """命令条目"""
    name: str
    description: str
    aliases: List[str]
    handler: Callable[..., Awaitable[Any]]
    enabled: bool = True


class CommandRegistry:
    """命令注册表"""

    def __init__(self):
        self._commands: Dict[str, CommandEntry] = {}
        self._aliases: Dict[str, str] = {}  # alias -> command name

    def register(
        self,
        name: str,
        description: str,
        aliases: Optional[List[str]] = None,
        handler: Callable[..., Awaitable[Any]] = None,
    ) -> None:
        """注册命令"""
        self._commands[name] = CommandEntry(
            name=name,
            description=description,
            aliases=aliases or [],
            handler=handler,
        )

        # 注册别名
        for alias in (aliases or []):
            self._aliases[alias] = name

    def get(self, name: str) -> Optional[CommandEntry]:
        """获取命令（支持别名）"""
        if name in self._commands:
            return self._commands[name]
        if name in self._aliases:
            return self._commands.get(self._aliases[name])
        return None

    def list(self, enabled_only: bool = False) -> List[CommandEntry]:
        """列出所有命令"""
        commands = list(self._commands.values())
        if enabled_only:
            commands = [c for c in commands if c.enabled]
        return commands
