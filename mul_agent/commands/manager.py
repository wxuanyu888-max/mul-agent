"""Command Manager - 命令管理器"""

import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Callable
import re

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from mul_agent.commands.base import BaseCommand, CommandContext, CommandResult, CommandStatus


class CommandManager:
    """命令管理器

    负责：
    - 注册命令
    - 执行命令
    - 命令帮助
    - 从配置文件加载命令
    """

    def __init__(self, config_manager=None, agent_id: str = None):
        """初始化命令管理器

        Args:
            config_manager: 配置管理器
            agent_id: Agent ID
        """
        self.config_manager = config_manager
        self.agent_id = agent_id or "wangyue"

        # 已注册的命令
        self._commands: Dict[str, BaseCommand] = {}

        # 命令别名映射
        self._aliases: Dict[str, str] = {}

        # 命令元数据缓存
        self._command_metadata: Dict[str, Dict[str, Any]] = {}

        # 加载内置命令和配置文件命令
        self._load_builtin_commands()
        self._load_command_configs()

    def _load_builtin_commands(self) -> None:
        """加载内置命令"""
        builtin_commands = [
            "mul_agent.commands.builtin.HelpCommand",
            "mul_agent.commands.builtin.StatusCommand",
            "mul_agent.commands.builtin.ListCommand",
            "mul_agent.commands.builtin.SkillCommand",
            "mul_agent.commands.builtin.HookCommand",
            "mul_agent.commands.builtin.MemoryCommand",
            "mul_agent.commands.builtin.BashCommand",
        ]

        for command_path in builtin_commands:
            try:
                module_path, class_name = command_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                command_class = getattr(module, class_name)
                self.register_command(command_class)
            except Exception as e:
                print(f"Error loading builtin command {command_path}: {e}")

    def _load_command_configs(self) -> None:
        """从配置加载命令"""
        try:
            # 从 soul.md 或 user.md 中加载命令配置
            soul_config = self.config_manager.load(self.agent_id, "soul")
            commands_config = soul_config.get("commands", [])

            for command_data in commands_config:
                command_id = command_data.get("id")
                enabled = command_data.get("enabled", True)

                if not enabled:
                    continue

                # 尝试加载动态命令
                module_path = command_data.get("module_path")
                if module_path:
                    try:
                        module = importlib.import_module(module_path)
                        class_name = command_data.get("class_name", "DynamicCommand")
                        command_class = getattr(module, class_name)
                        self.register_command(command_class)
                    except Exception as e:
                        print(f"Error loading dynamic command {module_path}: {e}")
        except Exception as e:
            print(f"Error loading command configs: {e}")

    def register_command(
        self,
        command_class: Type[BaseCommand],
        instance: BaseCommand = None,
        aliases: List[str] = None
    ) -> str:
        """注册命令

        Args:
            command_class: 命令类
            instance: 命令实例（如果为 None 则自动创建）
            aliases: 命令别名

        Returns:
            str: 命令 ID
        """
        if instance is None:
            instance = command_class(
                config_manager=self.config_manager,
                agent_id=self.agent_id
            )

        # 初始化命令
        if not instance.initialize():
            raise ValueError(f"Failed to initialize command {instance.command_id}")

        # 注册命令
        self._commands[instance.command_name] = instance
        self._command_metadata[instance.command_name] = instance.get_metadata()

        # 注册别名
        all_aliases = aliases or instance.command_aliases
        for alias in all_aliases:
            self._aliases[alias] = instance.command_name

        return instance.command_name

    def unregister_command(self, command_name: str) -> bool:
        """注销命令"""
        if command_name in self._commands:
            del self._commands[command_name]
        if command_name in self._command_metadata:
            del self._command_metadata[command_name]

        # 清理别名
        aliases_to_remove = [
            alias for alias, cmd in self._aliases.items()
            if cmd == command_name
        ]
        for alias in aliases_to_remove:
            del self._aliases[alias]

        return True

    def execute(self, command_name: str, args_str: str = "") -> CommandResult:
        """执行命令

        Args:
            command_name: 命令名称
            args_str: 参数字符串

        Returns:
            CommandResult: 执行结果
        """
        # 解析别名
        actual_command = self._aliases.get(command_name, command_name)

        # 查找命令
        command = self._commands.get(actual_command)
        if not command:
            return CommandResult.not_found(command_name)

        if not command.enabled:
            return CommandResult.error(
                message=f"Command is disabled: {command_name}",
                error="Command is disabled"
            )

        # 解析参数
        args, kwargs = command.parse_args(args_str)

        # 创建上下文
        context = CommandContext(
            command=actual_command,
            args=args,
            kwargs=kwargs,
            agent_id=self.agent_id,
            user_input=f"{command_name} {args_str}"
        )

        # 执行命令
        try:
            result = command.execute(context)
            return result
        except Exception as e:
            return CommandResult.error(
                message=f"Error executing command: {command_name}",
                error=str(e)
            )

    def execute_from_input(self, user_input: str) -> CommandResult:
        """从用户输入执行命令

        Args:
            user_input: 用户输入（如 "help skill"）

        Returns:
            CommandResult: 执行结果
        """
        user_input = user_input.strip()

        # 检测命令前缀
        command_prefixes = ["/", "!"]
        command_name = user_input

        for prefix in command_prefixes:
            if user_input.startswith(prefix):
                command_name = user_input[len(prefix):].strip()
                break

        # 分割命令和参数
        parts = command_name.split(None, 1)
        cmd = parts[0] if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        return self.execute(cmd, args)

    def get_command(self, command_name: str) -> Optional[BaseCommand]:
        """获取命令实例"""
        actual_command = self._aliases.get(command_name, command_name)
        return self._commands.get(actual_command)

    def list_commands(self, include_hidden: bool = False) -> List[Dict[str, Any]]:
        """列出所有命令

        Args:
            include_hidden: 是否包含隐藏命令

        Returns:
            List[Dict]: 命令元数据列表
        """
        commands = []
        for name, metadata in self._command_metadata.items():
            if not include_hidden and metadata.get("hidden", False):
                continue
            commands.append(metadata)
        return sorted(commands, key=lambda x: x.get("command_name", ""))

    def search_commands(self, query: str) -> List[Dict[str, Any]]:
        """搜索命令

        Args:
            query: 搜索关键词

        Returns:
            List[Dict]: 匹配的命令元数据
        """
        results = []
        query_lower = query.lower()

        for name, metadata in self._command_metadata.items():
            score = 0

            if query_lower in name.lower():
                score += 10
            if query_lower in metadata.get("command_description", "").lower():
                score += 5

            if score > 0:
                results.append({**metadata, "relevance_score": score})

        return sorted(results, key=lambda x: x.get("relevance_score", 0), reverse=True)

    def get_help(self, command_name: str = None) -> str:
        """获取帮助信息

        Args:
            command_name: 命令名称（可选，如果为 None 则返回所有命令的帮助）

        Returns:
            str: 帮助信息
        """
        if command_name:
            command = self.get_command(command_name)
            if command:
                return command.get_help()
            return f"Command not found: {command_name}"

        # 返回所有命令的帮助
        help_text = ["Available commands:\n"]

        commands = self.list_commands()
        for cmd in commands:
            aliases = cmd.get("command_aliases", [])
            alias_str = f" ({', '.join(aliases)})" if aliases else ""
            help_text.append(f"  {cmd['command_name']}{alias_str}")
            help_text.append(f"    {cmd['command_description']}")

        help_text.append("\nUse '/help <command>' for more details")

        return "\n".join(help_text)

    def enable_command(self, command_name: str) -> bool:
        """启用命令"""
        command = self.get_command(command_name)
        if command:
            command.enabled = True
            self._command_metadata[command_name]["enabled"] = True
            return True
        return False

    def disable_command(self, command_name: str) -> bool:
        """禁用命令"""
        command = self.get_command(command_name)
        if command:
            command.enabled = False
            self._command_metadata[command_name]["enabled"] = False
            return True
        return False

    def add_command_function(
        self,
        command_name: str,
        callback: Callable[[CommandContext], CommandResult],
        description: str = "",
        usage: str = "",
        aliases: List[str] = None
    ) -> str:
        """添加函数命令

        Args:
            command_name: 命令名称
            callback: 回调函数
            description: 描述
            usage: 用法
            aliases: 别名

        Returns:
            str: 命令 ID
        """
        from mul_agent.commands.base import BaseCommand

        # 创建动态命令类
        class FunctionCommand(BaseCommand):
            def __init__(self, callback, name, description, usage, aliases):
                self.callback = callback
                self._name = name
                self._description = description
                self._usage = usage
                self._aliases = aliases
                self._command_id = f"function_{name}"
                super().__init__()

            command_id = property(lambda self: self._command_id)
            command_name = property(lambda self: self._name)
            command_description = property(lambda self: self._description)
            command_usage = property(lambda self: self._usage)
            command_aliases = property(lambda self: self._aliases or [])

            def _initialize(self):
                pass

            def execute(self, context):
                return self.callback(context)

        return self.register_command(FunctionCommand, None, aliases)

    def to_dict(self) -> Dict[str, Any]:
        """将命令管理器状态转换为字典"""
        return {
            "agent_id": self.agent_id,
            "commands_count": len(self._commands),
            "commands": self.list_commands(),
            "aliases": self._aliases,
        }
