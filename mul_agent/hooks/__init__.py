"""Hooks System - 钩子系统

钩子系统允许在特定事件发生时执行自定义逻辑。
支持的事件类型：
- pre_tool_use: 工具使用前
- post_tool_use: 工具使用后
- session_start: 会话开始时
- session_end: 会话结束时
- pre_message: 消息处理前
- post_message: 消息处理后
"""

from .base import BaseHook, HookEvent
from .manager import HookManager

__all__ = [
    "BaseHook",
    "HookEvent",
    "HookManager",
]
