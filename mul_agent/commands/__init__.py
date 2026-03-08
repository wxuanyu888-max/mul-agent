"""Commands Module - 命令系统

命令是用户可以通过 CLI 或对话触发的操作。
支持：
- 内置命令（如 help, status, list 等）
- 动态注册命令
- 命令别名
- 命令帮助
"""

from mul_agent.commands.base import BaseCommand, CommandContext, CommandResult
from mul_agent.commands.manager import CommandManager
from mul_agent.commands.builtin import (
    HelpCommand,
    StatusCommand,
    ListCommand,
    SkillCommand,
    HookCommand,
    MemoryCommand,
    BashCommand,
)

__all__ = [
    "BaseCommand",
    "CommandContext",
    "CommandResult",
    "CommandManager",
    "HelpCommand",
    "StatusCommand",
    "ListCommand",
    "SkillCommand",
    "HookCommand",
    "MemoryCommand",
    "BashCommand",
]
