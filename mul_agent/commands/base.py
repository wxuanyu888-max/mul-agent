"""Base Command - 命令基类"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional


class CommandStatus(Enum):
    """命令执行状态"""
    SUCCESS = "success"
    ERROR = "error"
    NOT_FOUND = "not_found"
    INVALID_ARGS = "invalid_args"


@dataclass
class CommandResult:
    """命令执行结果"""
    status: CommandStatus
    data: Any = None
    message: str = ""
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "status": self.status.value,
            "data": self.data,
            "message": self.message,
            "error": self.error,
        }


@dataclass
class CommandMetadata:
    """命令元数据"""
    command_id: str = ""
    command_name: str = ""
    command_description: str = ""
    command_usage: str = ""
    command_aliases: List[str] = None
    command_examples: List[str] = None
    enabled: bool = True

    def __post_init__(self):
        if self.command_aliases is None:
            self.command_aliases = []
        if self.command_examples is None:
            self.command_examples = []


class BaseCommand(ABC):
    """所有命令的基类"""

    # 命令元数据（类级别默认值）
    command_id: str = "base_command"
    command_name: str = "base"
    command_description: str = "Base command"
    command_usage: str = "/base [args]"
    command_aliases: List[str] = []
    command_examples: List[str] = []

    # 实例级别配置
    enabled: bool = True

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

    def _initialize(self) -> None:
        """命令初始化逻辑（由子类覆盖）"""
        pass

    def get_metadata(self) -> CommandMetadata:
        """获取命令元数据

        Returns:
            CommandMetadata: 命令元数据
        """
        return CommandMetadata(
            command_id=self.command_id,
            command_name=self.command_name,
            command_description=self.command_description,
            command_usage=self.command_usage,
            command_aliases=self.command_aliases.copy(),
            command_examples=self.command_examples.copy(),
            enabled=self.enabled,
        )

    @abstractmethod
    def execute(self, args: str = "") -> CommandResult:
        """执行命令

        Args:
            args: 命令参数字符串

        Returns:
            CommandResult: 命令执行结果
        """
        pass

    def parse_args(self, args: str) -> Dict[str, Any]:
        """解析命令参数

        Args:
            args: 命令参数字符串

        Returns:
            Dict: 解析后的参数
        """
        # 简单的空格分割，子类可以覆盖此方法实现更复杂的解析
        if not args.strip():
            return {}

        parts = args.strip().split()
        result = {}

        i = 0
        while i < len(parts):
            if parts[i].startswith("--"):
                key = parts[i][2:]
                if i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                    result[key] = parts[i + 1]
                    i += 2
                else:
                    result[key] = True
                    i += 1
            elif parts[i].startswith("-") and len(parts[i]) == 2:
                key = parts[i][1:]
                if i + 1 < len(parts) and not parts[i + 1].startswith("-"):
                    result[key] = parts[i + 1]
                    i += 2
                else:
                    result[key] = True
                    i += 1
            else:
                # 位置参数
                if "args" not in result:
                    result["args"] = []
                result["args"].append(parts[i])
                i += 1

        return result

    def get_help(self) -> str:
        """获取命令帮助信息

        Returns:
            str: 帮助信息
        """
        lines = [
            f"Command: {self.command_name}",
            f"Description: {self.command_description}",
            f"Usage: {self.command_usage}",
        ]

        if self.command_aliases:
            lines.append(f"Aliases: {', '.join(self.command_aliases)}")

        if self.command_examples:
            lines.append("Examples:")
            for example in self.command_examples:
                lines.append(f"  {example}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """将命令转换为字典

        Returns:
            Dict: 命令字典
        """
        return {
            **self.get_metadata().__dict__,
            "config_manager": self.config_manager.__class__.__name__ if self.config_manager else None,
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"{self.command_name} v1.0.0"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"<{self.__class__.__name__}(id={self.command_id}, name={self.command_name})>"
