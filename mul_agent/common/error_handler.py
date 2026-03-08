"""Error Handler - 统一错误处理"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ErrorCode:
    """错误码定义"""
    code: int
    type: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "type": self.type,
            "message": self.message
        }


# 标准错误码定义
class StandardErrorCodes:
    """标准错误码"""

    # 通用错误 (1000-1099)
    SUCCESS = ErrorCode(0, "SUCCESS", "Success")
    UNKNOWN_ERROR = ErrorCode(1000, "UNKNOWN_ERROR", "Unknown error")
    INVALID_PARAMS = ErrorCode(1001, "INVALID_PARAMS", "Invalid parameters")
    HANDLER_ERROR = ErrorCode(1002, "HANDLER_ERROR", "Handler error")
    COMMAND_FORBIDDEN = ErrorCode(1003, "COMMAND_FORBIDDEN", "Command forbidden")
    MISSING_PARAMS = ErrorCode(1004, "MISSING_PARAMS", "Missing parameters")
    UNKNOWN_ACTION = ErrorCode(1005, "UNKNOWN_ACTION", "Unknown action")
    COMMAND_EXECUTION_FAILED = ErrorCode(1006, "COMMAND_EXECUTION_FAILED", "Command execution failed")

    # Router 错误
    ROUTER_ERROR = ErrorCode(1100, "ROUTER_ERROR", "Router error")
    ROUTE_NOT_FOUND = ErrorCode(1101, "ROUTE_NOT_FOUND", "Route not found")

    # Chat 错误 (2000-2099)
    CHAT_ERROR = ErrorCode(2000, "CHAT_ERROR", "Chat error")
    UNKNOWN_CHAT_ACTION = ErrorCode(2001, "UNKNOWN_CHAT_ACTION", "Unknown chat action")
    AGENT_NOT_FOUND = ErrorCode(2002, "AGENT_NOT_FOUND", "Agent not found")
    CONVERSATION_NOT_FOUND = ErrorCode(2003, "CONVERSATION_NOT_FOUND", "Conversation not found")

    # Token Usage 错误 (3000-3099)
    TOKEN_USAGE_ERROR = ErrorCode(3000, "TOKEN_USAGE_ERROR", "Token usage error")
    AGENT_ID_MISSING = ErrorCode(3001, "AGENT_ID_MISSING", "Agent ID missing")
    UNKNOWN_TOKEN_ACTION = ErrorCode(3002, "UNKNOWN_TOKEN_ACTION", "Unknown token action")

    # Memory 错误 (4000-4099)
    MEMORY_ERROR = ErrorCode(4000, "MEMORY_ERROR", "Memory error")
    MEMORY_NOT_FOUND = ErrorCode(4001, "MEMORY_NOT_FOUND", "Memory not found")
    MEMORY_WRITE_FAILED = ErrorCode(4002, "MEMORY_WRITE_FAILED", "Memory write failed")

    # Network 错误 (5000-5099)
    NETWORK_ERROR = ErrorCode(5000, "NETWORK_ERROR", "Network error")
    AGENT_NOT_REGISTERED = ErrorCode(5001, "AGENT_NOT_REGISTERED", "Agent not registered")
    MESSAGE_NOT_FOUND = ErrorCode(5002, "MESSAGE_NOT_FOUND", "Message not found")
    MESSAGE_SEND_FAILED = ErrorCode(5003, "MESSAGE_SEND_FAILED", "Message send failed")

    # Config 错误 (6000-6099)
    CONFIG_ERROR = ErrorCode(6000, "CONFIG_ERROR", "Config error")
    CONFIG_NOT_FOUND = ErrorCode(6001, "CONFIG_NOT_FOUND", "Config not found")
    CONFIG_SAVE_FAILED = ErrorCode(6002, "CONFIG_SAVE_FAILED", "Config save failed")
    CONFIG_INVALID = ErrorCode(6003, "CONFIG_INVALID", "Config invalid")

    # Team 错误 (7000-7099)
    TEAM_ERROR = ErrorCode(7000, "TEAM_ERROR", "Team error")
    TEAM_NOT_FOUND = ErrorCode(7001, "TEAM_NOT_FOUND", "Team not found")
    TEAM_ALREADY_EXISTS = ErrorCode(7002, "TEAM_ALREADY_EXISTS", "Team already exists")
    TEAM_NAME_RESERVED = ErrorCode(7003, "TEAM_NAME_RESERVED", "Team name reserved")


class AppError(Exception):
    """应用错误基类"""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str = None,
        details: Dict[str, Any] = None,
        route: str = None
    ):
        self.error_code = error_code
        self.message = message or error_code.message
        self.details = details
        self.route = route
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        response = {
            "status": "error",
            "error_code": self.error_code.code,
            "error_type": self.error_code.type,
            "message": self.message,
        }
        if self.route:
            response["route"] = self.route
        if self.details:
            response["details"] = self.details
        return response


def create_error_response(
    error_code: ErrorCode,
    message: str = None,
    details: Dict[str, Any] = None,
    route: str = None
) -> Dict[str, Any]:
    """创建错误响应

    Args:
        error_code: 错误码
        message: 错误消息（可选，覆盖默认消息）
        details: 详细错误信息
        route: 路由名称

    Returns:
        标准化错误响应字典
    """
    response = {
        "status": "error",
        "error_code": error_code.code,
        "error_type": error_code.type,
        "message": message or error_code.message,
    }
    if route:
        response["route"] = route
    if details:
        response["details"] = details
    return response


def create_error_response_from_exception(
    exception: Exception,
    default_error_code: ErrorCode = StandardErrorCodes.UNKNOWN_ERROR,
    route: str = None
) -> Dict[str, Any]:
    """从异常创建错误响应

    Args:
        exception: 异常对象
        default_error_code: 默认错误码
        route: 路由名称

    Returns:
        标准化错误响应字典
    """
    if isinstance(exception, AppError):
        return exception.to_dict()

    return create_error_response(
        error_code=default_error_code,
        message=str(exception),
        route=route
    )
