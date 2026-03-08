"""Hooks Module - 钩子系统

钩子是在特定事件触发时执行的回调函数。
支持：
- PreToolUse: 工具执行前的拦截和验证
- PostToolUse: 工具执行后的处理和日志
- SessionStart: 会话开始时的初始化
- SessionEnd: 会话结束时的清理
"""

from mul_agent.hooks.base import BaseHook, HookEvent, HookPriority
from mul_agent.hooks.manager import HookManager
from mul_agent.hooks.builtin import (
    PreToolUseHook,
    PostToolUseHook,
    SessionStartHook,
    SessionEndHook,
    LogInvocationHook,
    FormatOutputHook,
)

__all__ = [
    "BaseHook",
    "HookEvent",
    "HookPriority",
    "HookManager",
    "PreToolUseHook",
    "PostToolUseHook",
    "SessionStartHook",
    "SessionEndHook",
    "LogInvocationHook",
    "FormatOutputHook",
]
