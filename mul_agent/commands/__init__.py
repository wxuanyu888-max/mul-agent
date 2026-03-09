"""Commands Module - 命令系统

命令是用户可以通过 CLI 或对话触发的操作。
支持：
- 内置命令（如 help, status, list 等）
- 动态注册命令
- 命令别名
- 命令帮助
- 对话管理命令（history, undo, summary, clear, resume）
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
    PermissionCommand,
    SearchCommand,
    CodeIndexCommand,
    CheckpointCommand,
)
from mul_agent.commands.dialog import (
    HistoryCommand,
    UndoCommand,
    SummaryCommand,
    ClearCommand,
    ResumeCommand,
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
    "PermissionCommand",
    "SearchCommand",
    "CodeIndexCommand",
    "CheckpointCommand",
    # 对话管理命令
    "HistoryCommand",
    "UndoCommand",
    "SummaryCommand",
    "ClearCommand",
    "ResumeCommand",
]
