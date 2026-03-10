"""
Mul-Agent Sessions Module - 会话模块

提供完整的会话管理功能:
- 创建、加载、更新、删除会话
- Token 计数与阈值管理
- 自动压缩提示
- 事件回调支持
"""

from .session_manager import (
    SessionManager,
    SessionContext,
    SessionMessage,
    SessionRole,
    TokenThreshold,
    CompressionHint,
    estimate_tokens,
)

__all__ = [
    "SessionManager",
    "SessionContext",
    "SessionMessage",
    "SessionRole",
    "TokenThreshold",
    "CompressionHint",
    "estimate_tokens",
]
