"""Router - Route dispatcher"""

from typing import Any, Dict, Callable

from mul_agent.brain.handlers import (
    CreateUserHandler,
    BashHandler,
    HeartHandler,
    MemoryHandler,
    ChatHandler,
    ResponseHandler,
    TokenUsageHandler,
    CreateTeamHandler,
    NetworkDelegateHandler,
    NetworkSendHandler,
    NetworkCheckHandler,
    NetworkBroadcastHandler,
    NetworkHandoverHandler,
)
from mul_agent.common.error_handler import (
    StandardErrorCodes,
    create_error_response,
    create_error_response_from_exception,
)
from mul_agent.common.response import create_success_response


class Router:
    """路由分发器"""

    ROUTES: Dict[str, Callable] = {
        "create_user": CreateUserHandler,
        "bash": BashHandler,
        "heart": HeartHandler,
        "memory": MemoryHandler,
        "chat": ChatHandler,
        "response": ResponseHandler,
        "token_usage": TokenUsageHandler,
        "create_team": CreateTeamHandler,
        # Agent 网络相关路由
        "network_delegate": NetworkDelegateHandler,
        "network_send": NetworkSendHandler,
        "network_check": NetworkCheckHandler,
        "network_broadcast": NetworkBroadcastHandler,
        "network_handover": NetworkHandoverHandler,
    }

    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.handlers = {
            name: handler(config_manager)
            for name, handler in self.ROUTES.items()
        }

    def dispatch(self, route: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """根据路由名分发到对应处理器"""
        if route not in self.handlers:
            return create_error_response(
                error_code=StandardErrorCodes.ROUTE_NOT_FOUND,
                message=f"Unknown route: {route}",
                route=route,
                details={"available_routes": list(self.ROUTES.keys())}
            )

        handler = self.handlers[route]
        try:
            # Special handling for "response" route - allow empty params
            if route == "response" and not params:
                return create_success_response(
                    data={"message": "", "type": "direct_response"},
                    route=route
                )

            result = handler.handle(params)
            # 标准化响应格式
            if isinstance(result, dict):
                if result.get("status") == "error":
                    # Handler 已经返回错误，标准化格式
                    return create_error_response(
                        error_code=self._get_error_code(result.get("error_code", 1002)),
                        message=result.get("message", "Handler error"),
                        route=route,
                        details=result.get("details")
                    )
                return create_success_response(
                    data=result,
                    route=route
                )
            else:
                return create_success_response(
                    data={"output": result},
                    route=route
                )
        except Exception as e:
            return create_error_response_from_exception(
                exception=e,
                default_error_code=StandardErrorCodes.HANDLER_ERROR,
                route=route
            )

    def _get_error_code(self, code: int) -> StandardErrorCodes:
        """根据错误码获取标准错误码"""
        error_code_map = {
            1000: StandardErrorCodes.ROUTER_ERROR,
            1001: StandardErrorCodes.INVALID_PARAMS,
            1002: StandardErrorCodes.HANDLER_ERROR,
            1003: StandardErrorCodes.COMMAND_FORBIDDEN,
            1004: StandardErrorCodes.MISSING_PARAMS,
            1005: StandardErrorCodes.UNKNOWN_ACTION,
            1006: StandardErrorCodes.COMMAND_EXECUTION_FAILED,
            2000: StandardErrorCodes.CHAT_ERROR,
            2001: StandardErrorCodes.UNKNOWN_CHAT_ACTION,
            2002: StandardErrorCodes.AGENT_NOT_FOUND,
            2003: StandardErrorCodes.CONVERSATION_NOT_FOUND,
            3001: StandardErrorCodes.AGENT_ID_MISSING,
            3002: StandardErrorCodes.UNKNOWN_TOKEN_ACTION,
        }
        return error_code_map.get(code, StandardErrorCodes.UNKNOWN_ERROR)

    def list_routes(self) -> list:
        """列出所有可用路由"""
        return [
            {
                "name": name,
                "handler": handler.__class__.__name__
            }
            for name, handler in self.handlers.items()
        ]
