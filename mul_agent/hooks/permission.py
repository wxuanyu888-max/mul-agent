"""Permission Hook - 权限钩子"""

from typing import Dict, List, Optional, Set
from .base import BaseHook


class PermissionHook(BaseHook):
    """权限钩子 - 控制工具和命令的访问权限"""

    hook_id = "permission_hook"
    hook_name = "Permission Hook"
    hook_description = "控制工具和命令访问权限的钩子"
    hook_version = "1.0.0"
    hook_tags = ["permission", "security"]
    priority = 10  # 高优先级，先于其他钩子执行

    def __init__(self, config_manager=None, agent_id: str = None):
        super().__init__(config_manager, agent_id)
        self._allowed_tools: Set[str] = set()
        self._denied_tools: Set[str] = set()
        self._allowed_commands: Set[str] = set()
        self._denied_commands: Set[str] = set()

    def _initialize(self) -> None:
        """初始化权限配置"""
        if self.config_manager:
            try:
                config = self.config_manager.get_config()
                permissions = config.get("permissions", {})

                # 加载工具权限
                self._allowed_tools = set(permissions.get("allowed_tools", []))
                self._denied_tools = set(permissions.get("denied_tools", []))

                # 加载命令权限
                self._allowed_commands = set(permissions.get("allowed_commands", []))
                self._denied_commands = set(permissions.get("denied_commands", []))
            except Exception:
                pass

    def allow_tool(self, route: str) -> bool:
        """检查工具是否被允许

        Args:
            route: 工具路由

        Returns:
            bool: 是否允许使用
        """
        if route in self._denied_tools:
            return False
        if self._allowed_tools and route not in self._allowed_tools:
            return False
        return True

    def allow_command(self, command: str) -> bool:
        """检查命令是否被允许

        Args:
            command: 命令名称

        Returns:
            bool: 是否允许使用
        """
        if command in self._denied_commands:
            return False
        if self._allowed_commands and command not in self._allowed_commands:
            return False
        return True

    def pre_tool_use(self, route: str, params: dict) -> dict:
        """工具使用前权限检查"""
        if not self.allow_tool(route):
            raise PermissionError(f"Tool not allowed: {route}")
        return params

    def pre_command(self, command: str, args: str) -> tuple:
        """命令执行前权限检查"""
        if not self.allow_command(command):
            raise PermissionError(f"Command not allowed: {command}")
        return command, args

    def add_allowed_tool(self, route: str) -> None:
        """添加允许的工具"""
        self._allowed_tools.add(route)

    def remove_allowed_tool(self, route: str) -> None:
        """移除允许的工具"""
        self._allowed_tools.discard(route)

    def add_denied_tool(self, route: str) -> None:
        """添加禁止的工具"""
        self._denied_tools.add(route)

    def remove_denied_tool(self, route: str) -> None:
        """移除禁止的工具"""
        self._denied_tools.discard(route)

    def add_allowed_command(self, command: str) -> None:
        """添加允许的命令"""
        self._allowed_commands.add(command)

    def remove_allowed_command(self, command: str) -> None:
        """移除允许的命令"""
        self._allowed_commands.discard(command)

    def add_denied_command(self, command: str) -> None:
        """添加禁止的命令"""
        self._denied_commands.add(command)

    def remove_denied_command(self, command: str) -> None:
        """移除禁止的命令"""
        self._denied_commands.discard(command)

    def get_permissions(self) -> Dict:
        """获取当前权限配置

        Returns:
            Dict: 权限配置字典
        """
        return {
            "allowed_tools": list(self._allowed_tools),
            "denied_tools": list(self._denied_tools),
            "allowed_commands": list(self._allowed_commands),
            "denied_commands": list(self._denied_commands),
        }


__all__ = ["PermissionHook"]
