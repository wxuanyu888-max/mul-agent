"""Command Manager - 命令管理器"""

import inspect
from typing import Any, Dict, List, Optional, Type

from .base import BaseCommand, CommandResult, CommandStatus, CommandMetadata


class CommandManager:
    """命令管理器

    负责注册、管理和执行命令
    """

    def __init__(self, config_manager=None, agent_id: str = None):
        """初始化命令管理器

        Args:
            config_manager: 配置管理器
            agent_id: Agent ID
        """
        self.config_manager = config_manager
        self.agent_id = agent_id or "default"
        self._commands: Dict[str, BaseCommand] = {}  # command_id -> instance
        self._command_names: Dict[str, str] = {}  # command_name -> command_id
        self._command_aliases: Dict[str, str] = {}  # alias -> command_id
        self._load_builtin_commands()

    def _load_builtin_commands(self) -> None:
        """加载内置命令"""
        try:
            from . import builtin
            # 自动注册 builtin 模块中的所有 Command 类
            for name, obj in inspect.getmembers(builtin):
                if (inspect.isclass(obj) and
                    issubclass(obj, BaseCommand) and
                    obj != BaseCommand and
                    hasattr(obj, 'command_id')):
                    self.register_command(obj)
        except ImportError:
            pass  # builtin 模块可能不存在

    def register_command(self, command_class: Type[BaseCommand], instance: Optional[BaseCommand] = None) -> Optional[str]:
        """注册命令

        Args:
            command_class: 命令类
            instance: 可选的命令实例，如果不提供则创建新实例

        Returns:
            Optional[str]: 命令 ID，如果注册失败返回 None
        """
        try:
            # 创建或使用了提供的实例
            command_instance = instance if instance is not None else command_class(
                config_manager=self.config_manager,
                agent_id=self.agent_id
            )

            # 初始化命令
            if not command_instance.initialize():
                print(f"Failed to initialize command: {command_class.command_id}")
                return None

            # 检查是否已存在
            if command_instance.command_id in self._commands:
                print(f"Command already registered: {command_instance.command_id}")
                return command_instance.command_id

            # 注册命令实例
            self._commands[command_instance.command_id] = command_instance
            self._command_names[command_instance.command_name] = command_instance.command_id

            # 注册别名
            for alias in command_instance.command_aliases:
                self._command_aliases[alias] = command_instance.command_id

            return command_instance.command_id

        except Exception as e:
            print(f"Error registering command {command_class.command_id}: {e}")
            return None

    def unregister_command(self, command_id: str) -> bool:
        """注销命令

        Args:
            command_id: 命令 ID

        Returns:
            bool: 是否注销成功
        """
        if command_id not in self._commands:
            return False

        command = self._commands[command_id]

        # 从名称映射中移除
        if command.command_name in self._command_names:
            del self._command_names[command.command_name]

        # 从别名映射中移除
        for alias in command.command_aliases:
            if alias in self._command_aliases:
                del self._command_aliases[alias]

        # 删除命令实例
        del self._commands[command_id]
        return True

    def get_command(self, command_id: str) -> Optional[BaseCommand]:
        """获取命令

        Args:
            command_id: 命令 ID

        Returns:
            Optional[BaseCommand]: 命令实例，如果不存在返回 None
        """
        return self._commands.get(command_id)

    def get_command_by_name(self, name: str) -> Optional[BaseCommand]:
        """根据名称获取命令

        Args:
            name: 命令名称或别名

        Returns:
            Optional[BaseCommand]: 命令实例，如果不存在返回 None
        """
        # 先查找名称
        command_id = self._command_names.get(name)
        if command_id:
            return self._commands.get(command_id)

        # 再查找别名
        command_id = self._command_aliases.get(name)
        if command_id:
            return self._commands.get(command_id)

        return None

    def list_commands(self) -> List[Dict[str, Any]]:
        """列出所有已注册的命令

        Returns:
            List[Dict]: 命令元数据列表
        """
        return [cmd.get_metadata().__dict__ for cmd in self._commands.values()]

    def execute(self, command_name: str, args: str = "") -> CommandResult:
        """执行命令

        Args:
            command_name: 命令名称
            args: 命令参数

        Returns:
            CommandResult: 命令执行结果
        """
        command = self.get_command_by_name(command_name)

        if not command:
            return CommandResult(
                status=CommandStatus.NOT_FOUND,
                message=f"Command not found: {command_name}"
            )

        if not command.enabled:
            return CommandResult(
                status=CommandStatus.ERROR,
                message=f"Command is disabled: {command_name}"
            )

        try:
            result = command.execute(args)
            return result
        except Exception as e:
            return CommandResult(
                status=CommandStatus.ERROR,
                error=str(e),
                message=f"Error executing command: {e}"
            )

    def execute_from_input(self, input_text: str) -> CommandResult:
        """从输入文本执行命令

        支持格式：
        - /command args
        - !command args
        - command args

        Args:
            input_text: 输入文本

        Returns:
            CommandResult: 命令执行结果
        """
        input_text = input_text.strip()

        if not input_text:
            return CommandResult(
                status=CommandStatus.INVALID_ARGS,
                message="Empty command input"
            )

        # 解析命令和参数
        parts = input_text.split(None, 1)
        command_name = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        # 移除前缀 / 或 !
        if command_name.startswith("/") or command_name.startswith("!"):
            command_name = command_name[1:]

        return self.execute(command_name, args)

    def get_help(self, command_name: Optional[str] = None) -> str:
        """获取帮助信息

        Args:
            command_name: 可选的命令名称，如果不提供则返回所有命令列表

        Returns:
            str: 帮助信息
        """
        if command_name:
            command = self.get_command_by_name(command_name)
            if command:
                return command.get_help()
            return f"Command not found: {command_name}"

        # 返回所有命令列表
        lines = ["Available commands:", ""]
        for cmd in self._commands.values():
            if cmd.enabled:
                lines.append(f"  /{cmd.command_name} - {cmd.command_description}")
        return "\n".join(lines)

    # =========================================================================
    # 管理方法
    # =========================================================================

    def enable_command(self, command_id: str) -> bool:
        """启用命令

        Args:
            command_id: 命令 ID

        Returns:
            bool: 是否成功启用
        """
        command = self.get_command(command_id)
        if command:
            command.enabled = True
            return True
        return False

    def disable_command(self, command_id: str) -> bool:
        """禁用命令

        Args:
            command_id: 命令 ID

        Returns:
            bool: 是否成功禁用
        """
        command = self.get_command(command_id)
        if command:
            command.enabled = False
            return True
        return False

    def reload_all(self) -> None:
        """重新加载所有命令"""
        # 清空所有命令
        self._commands.clear()
        self._command_names.clear()
        self._command_aliases.clear()

        # 重新加载内置命令
        self._load_builtin_commands()

    def to_dict(self) -> Dict[str, Any]:
        """将命令管理器转换为字典

        Returns:
            Dict: 命令管理器字典
        """
        return {
            "agent_id": self.agent_id,
            "commands_count": len(self._commands),
            "commands": self.list_commands(),
            "command_names": self._command_names.copy(),
            "command_aliases": self._command_aliases.copy(),
        }

    def __str__(self) -> str:
        """字符串表示"""
        return f"CommandManager(agent_id={self.agent_id}, commands={len(self._commands)})"

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"<CommandManager(agent_id='{self.agent_id}', commands={len(self._commands)})>"
