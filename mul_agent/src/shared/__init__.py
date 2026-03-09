"""
Shared - 共享模块
"""

__all__ = ["VERSION", "MulAgentError", "AgentError", "ToolError"]

VERSION = "2026.3.9"


class MulAgentError(Exception):
    """基础异常"""
    pass


class AgentError(MulAgentError):
    """Agent 异常"""
    pass


class ToolError(MulAgentError):
    """工具异常"""
    pass
