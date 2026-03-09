"""
Routing - 路由系统
"""

__all__ = ["Router", "Route", "Allowlist"]


class Route:
    """路由规则"""

    def __init__(self, pattern: str, handler: callable, priority: int = 0):
        self.pattern = pattern
        self.handler = handler
        self.priority = priority


class Allowlist:
    """允许列表"""

    def __init__(self):
        self._allowed: set[str] = set()

    def add(self, item: str) -> None:
        self._allowed.add(item)

    def remove(self, item: str) -> None:
        self._allowed.discard(item)

    def contains(self, item: str) -> bool:
        return item in self._allowed


class Router:
    """路由器"""

    def __init__(self):
        self._routes: list[Route] = []
        self.allowlist = Allowlist()

    def add_route(self, route: Route) -> None:
        self._routes.append(route)
        self._routes.sort(key=lambda r: r.priority, reverse=True)

    def match(self, input: str) -> callable | None:
        for route in self._routes:
            if route.pattern in input:
                return route.handler
        return None
