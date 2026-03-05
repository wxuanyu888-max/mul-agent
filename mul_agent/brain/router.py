"""Router - Route dispatcher"""

from typing import Any, Dict, Callable

from mul_agent.brain.handlers import (
    CreateUserHandler,
    BashHandler,
    HeartHandler,
    MemoryHandler,
    ChatHandler,
    ResponseHandler,
)


class Router:
    """路由分发器"""

    ROUTES: Dict[str, Callable] = {
        "create_user": CreateUserHandler,
        "bash": BashHandler,
        "heart": HeartHandler,
        "memory": MemoryHandler,
        "chat": ChatHandler,
        "response": ResponseHandler,
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
            return {
                "status": "error",
                "error_code": 1000,
                "message": f"Unknown route: {route}",
                "available_routes": list(self.ROUTES.keys())
            }

        handler = self.handlers[route]
        try:
            result = handler.handle(params)
            return {
                "status": "success",
                "route": route,
                "result": result
            }
        except Exception as e:
            return {
                "status": "error",
                "error_code": 1000,
                "message": str(e),
                "route": route
            }

    def list_routes(self) -> list:
        """列出所有可用路由"""
        return [
            {
                "name": name,
                "handler": handler.__class__.__name__
            }
            for name, handler in self.handlers.items()
        ]
