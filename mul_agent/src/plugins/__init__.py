"""
Plugins - 内置插件模块
"""

__all__ = ["PluginRegistry", "BasePlugin"]


class BasePlugin:
    """插件基类"""

    plugin_id: str
    plugin_name: str

    async def activate(self) -> None:
        raise NotImplementedError

    async def deactivate(self) -> None:
        raise NotImplementedError


class PluginRegistry:
    """插件注册表"""

    def __init__(self):
        self._plugins: dict[str, BasePlugin] = {}

    def register(self, plugin: BasePlugin) -> None:
        self._plugins[plugin.plugin_id] = plugin

    def unregister(self, plugin_id: str) -> None:
        self._plugins.pop(plugin_id, None)

    def get(self, plugin_id: str) -> BasePlugin | None:
        return self._plugins.get(plugin_id)

    def list(self) -> list[str]:
        return list(self._plugins.keys())
