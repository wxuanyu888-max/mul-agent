"""
Gateway - 网关系统

提供 HTTP/WebSocket 网关功能
"""

__all__ = ["GatewayServer", "GatewayConfig"]


class GatewayConfig:
    """网关配置"""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765, mode: str = "local"):
        self.host = host
        self.port = port
        self.mode = mode


class GatewayServer:
    """网关服务器"""

    def __init__(self, config: GatewayConfig):
        self.config = config
        self._running = False

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def health_check(self) -> dict:
        return {"status": "healthy" if self._running else "stopped"}
