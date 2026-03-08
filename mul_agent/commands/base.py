"""Base Command - 命令基类"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import time


class CommandStatus(str, Enum):
    """命令执行状态"""

    SUCCESS = "success"
    ERROR = "error"
    NOT_FOUND = "not_found"
    FORBIDDEN = "forbidden"


@dataclass
class CommandContext:
    """命令上下文

    Attributes:
        command: 命令名称
        args: 位置参数
        kwargs: 关键字参数
        agent_id: Agent ID
        user_input: 原始用户输入
        timestamp: 时间戳
    """
    command: str
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    agent_id: str = "default"
    user_input: str = ""
    timestamp: float = field(default_factory=time.time)

    def get_arg(self, index: int, default: Any = None) -> Any:
        """获取位置参数"""
        return self.args[index] if index < len(self.args) else default

    def get_kwarg(self, key: str, default: Any = None) -> Any:
        """获取关键字参数"""
        return self.kwargs.get(key, default)

    def has_arg(self, index: int) -> bool:
        """检查是否有位置参数"""
        return index < len(self.args)


@dataclass
class CommandResult:
    """命令执行结果

    Attributes:
        status: 执行状态
        message: 结果消息
        data: 结果数据
        error: 错误信息
        usage: 用法提示
    """
    status: CommandStatus = CommandStatus.SUCCESS
    message: str = ""
    data: Any = None
    error: str = None
    usage: str = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "status": self.status.value,
            "message": self.message,
        }
        if self.data is not None:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        if self.usage:
            result["usage"] = self.usage
        return result

    @classmethod
    def success(cls, message: str = "", data: Any = None) -> "CommandResult":
        """创建成功结果"""
        return cls(status=CommandStatus.SUCCESS, message=message, data=data)

    @classmethod
    def error(cls, message: str = "", error: str = None) -> "CommandResult":
        """创建错误结果"""
        return cls(status=CommandStatus.ERROR, message=message, error=error or message)

    @classmethod
    def not_found(cls, command: str) -> "CommandResult":
        """创建未找到结果"""
        return cls(
            status=CommandStatus.NOT_FOUND,
            message=f"Command not found: {command}",
            usage=f"Use 'help' to see available commands"
        )


class BaseCommand(ABC):
    """所有命令的基类"""

    # 命令元数据
    command_id: str = "base_command"
    command_name: str = "base"
    command_description: str = "Base command"
    command_usage: str = "base [options]"
    command_examples: List[str] = []
    command_aliases: List[str] = []

    # 命令配置
    enabled: bool = True
    requires_confirmation: bool = False
    hidden: bool = False  # 是否在帮助中隐藏

    def __init__(self, config_manager=None, agent_id: str = None):
        """初始化命令

        Args:
            config_manager: 配置管理器
            agent_id: Agent ID
        """
        self.config_manager = config_manager
        self.agent_id = agent_id or "default"
        self._initialized = False

    def initialize(self) -> bool:
        """初始化命令

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
            print(f"Error initializing command {self.command_id}: {e}")
            return False

    @abstractmethod
    def _initialize(self) -> None:
        """命令初始化逻辑（由子类实现）"""
        pass

    @abstractmethod
    def execute(self, context: CommandContext) -> CommandResult:
        """执行命令

        Args:
            context: 命令上下文

        Returns:
            CommandResult: 执行结果
        """
        pass

    def get_help(self) -> str:
        """获取帮助信息

        Returns:
            str: 帮助信息
        """
        help_text = [
            f"Command: {self.command_name}",
            f"Description: {self.command_description}",
            f"Usage: {self.command_usage}",
        ]

        if self.command_aliases:
            help_text.append(f"Aliases: {', '.join(self.command_aliases)}")

        if self.command_examples:
            help_text.append("\nExamples:")
            for example in self.command_examples:
                help_text.append(f"  {example}")

        return "\n".join(help_text)

    def get_metadata(self) -> Dict[str, Any]:
        """获取命令元数据

        Returns:
            Dict: 命令元数据
        """
        return {
            "command_id": self.command_id,
            "command_name": self.command_name,
            "command_description": self.command_description,
            "command_usage": self.command_usage,
            "command_aliases": self.command_aliases,
            "enabled": self.enabled,
            "hidden": self.hidden,
            "requires_confirmation": self.requires_confirmation,
        }

    def parse_args(self, args_str: str) -> tuple:
        """解析参数字符串

        Args:
            args_str: 参数字符串

        Returns:
            tuple: (args, kwargs)
        """
        import shlex

        try:
            parts = shlex.split(args_str)
        except ValueError:
            # Fallback to simple split
            parts = args_str.split()

        args = []
        kwargs = {}

        for part in parts:
            if "=" in part:
                key, value = part.split("=", 1)
                kwargs[key] = value
            else:
                args.append(part)

        return args, kwargs

    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.command_name}"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"<{self.__class__.__name__}(name={self.command_name})>"
