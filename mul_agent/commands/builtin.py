"""Built-in Commands - 内置命令"""

from .base import BaseCommand, CommandResult, CommandStatus


class HelpCommand(BaseCommand):
    """帮助命令"""

    command_id = "help"
    command_name = "help"
    command_description = "显示帮助信息"
    command_usage = "/help [command]"
    command_aliases = ["h", "?"]
    command_examples = [
        "/help - 显示所有命令",
        "/help bash - 显示 bash 命令的帮助",
    ]

    def __init__(self, command_manager=None, **kwargs):
        # 注意：这里需要特殊的初始化，因为 HelpCommand 需要访问其他命令
        super().__init__(**kwargs)
        self.command_manager = command_manager

    def execute(self, args: str = "") -> CommandResult:
        """执行帮助命令"""
        if not args.strip():
            # 显示所有命令列表
            if self.command_manager:
                help_text = self.command_manager.get_help()
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    data={"help": help_text},
                    message=help_text
                )
            return CommandResult(
                status=CommandStatus.SUCCESS,
                message="No commands available"
            )
        else:
            # 显示特定命令的帮助
            if self.command_manager:
                help_text = self.command_manager.get_help(args.strip())
                return CommandResult(
                    status=CommandStatus.SUCCESS,
                    data={"help": help_text},
                    message=help_text
                )
            return CommandResult(
                status=CommandStatus.NOT_FOUND,
                message=f"Command not found: {args}"
            )


class StatusCommand(BaseCommand):
    """状态命令"""

    command_id = "status"
    command_name = "status"
    command_description = "显示系统状态"
    command_usage = "/status"
    command_aliases = ["stat"]
    command_examples = [
        "/status - 显示系统状态",
    ]

    def execute(self, args: str = "") -> CommandResult:
        """执行状态命令"""
        status_info = {
            "agent_id": self.agent_id,
            "status": "running",
            "enabled": self.enabled,
        }

        return CommandResult(
            status=CommandStatus.SUCCESS,
            data=status_info,
            message=f"Agent {self.agent_id} is running"
        )


class EchoCommand(BaseCommand):
    """回显命令 - 用于测试"""

    command_id = "echo"
    command_name = "echo"
    command_description = "回显输入的内容"
    command_usage = "/echo <message>"
    command_aliases = []
    command_examples = [
        "/echo hello - 回显 hello",
    ]

    def execute(self, args: str = "") -> CommandResult:
        """执行回显命令"""
        return CommandResult(
            status=CommandStatus.SUCCESS,
            data={"echo": args},
            message=args
        )


class VersionCommand(BaseCommand):
    """版本命令"""

    command_id = "version"
    command_name = "version"
    command_description = "显示版本信息"
    command_usage = "/version"
    command_aliases = ["v", "ver"]
    command_examples = [
        "/version - 显示版本信息",
    ]

    def execute(self, args: str = "") -> CommandResult:
        """执行版本命令"""
        version_info = {
            "version": "1.0.0",
            "agent_id": self.agent_id,
        }

        return CommandResult(
            status=CommandStatus.SUCCESS,
            data=version_info,
            message="mul-agent version 1.0.0"
        )


__all__ = ["HelpCommand", "StatusCommand", "EchoCommand", "VersionCommand"]
