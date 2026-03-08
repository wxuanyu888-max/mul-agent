"""Built-in Commands - 内置命令"""

from typing import Any, Dict
from mul_agent.commands.base import BaseCommand, CommandContext, CommandResult, CommandStatus
from mul_agent.skills.manager import SkillManager
from mul_agent.hooks.manager import HookManager


class HelpCommand(BaseCommand):
    """帮助命令"""

    command_id = "help"
    command_name = "help"
    command_description = "Show help information"
    command_usage = "help [command]"
    command_aliases = ["h", "?", "援助"]
    command_examples = [
        "help - Show all commands",
        "help skill - Show help for 'skill' command",
    ]

    def _initialize(self) -> None:
        """初始化"""
        self.command_manager = None  # Will be set by manager

    def execute(self, context: CommandContext) -> CommandResult:
        """执行帮助命令"""
        command_name = context.get_arg(0)

        if command_name:
            # 显示特定命令的帮助
            from mul_agent.commands.manager import CommandManager
            cmd_mgr = CommandManager(self.config_manager, self.agent_id)
            help_text = cmd_mgr.get_help(command_name)
            return CommandResult.success(message=help_text)
        else:
            # 显示所有命令
            from mul_agent.commands.manager import CommandManager
            cmd_mgr = CommandManager(self.config_manager, self.agent_id)
            help_text = cmd_mgr.get_help()
            return CommandResult.success(message=help_text)


class StatusCommand(BaseCommand):
    """状态命令"""

    command_id = "status"
    command_name = "status"
    command_description = "Show agent status"
    command_usage = "status"
    command_aliases = ["st", "状态"]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行状态命令"""
        status_data = {
            "agent_id": self.agent_id,
            "status": "active",
        }

        # 尝试获取技能数量
        try:
            skill_mgr = SkillManager(self.config_manager, self.agent_id)
            status_data["skills_count"] = len(skill_mgr.list_skills())
        except Exception:
            status_data["skills_count"] = 0

        # 尝试获取钩子数量
        try:
            hook_mgr = HookManager(self.config_manager, self.agent_id)
            status_data["hooks_count"] = len(hook_mgr.list_hooks())
        except Exception:
            status_data["hooks_count"] = 0

        return CommandResult.success(
            message=f"Agent {self.agent_id} is active",
            data=status_data
        )


class ListCommand(BaseCommand):
    """列表命令"""

    command_id = "list"
    command_name = "list"
    command_description = "List items (skills, hooks, commands, etc.)"
    command_usage = "list <type>"
    command_aliases = ["ls", "列表"]
    command_examples = [
        "list skills - List all skills",
        "list hooks - List all hooks",
        "list commands - List all commands",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行列表命令"""
        list_type = context.get_arg(0, "commands")

        if list_type in ("skills", "skill"):
            skill_mgr = SkillManager(self.config_manager, self.agent_id)
            skills = skill_mgr.list_skills()
            return CommandResult.success(
                message=f"Found {len(skills)} skills",
                data={"skills": skills}
            )

        elif list_type in ("hooks", "hook"):
            hook_mgr = HookManager(self.config_manager, self.agent_id)
            hooks = hook_mgr.list_hooks()
            return CommandResult.success(
                message=f"Found {len(hooks)} hooks",
                data={"hooks": hooks}
            )

        elif list_type in ("commands", "command"):
            from mul_agent.commands.manager import CommandManager
            cmd_mgr = CommandManager(self.config_manager, self.agent_id)
            commands = cmd_mgr.list_commands()
            return CommandResult.success(
                message=f"Found {len(commands)} commands",
                data={"commands": commands}
            )

        else:
            return CommandResult.error(
                message=f"Unknown list type: {list_type}",
                usage="Usage: list <skills|hooks|commands>"
            )


class SkillCommand(BaseCommand):
    """技能管理命令"""

    command_id = "skill"
    command_name = "skill"
    command_description = "Manage skills"
    command_usage = "skill <action> [options]"
    command_aliases = ["sk", "技能"]
    command_examples = [
        "skill list - List all skills",
        "skill info bash_executor - Show skill info",
        "skill enable bash_executor - Enable a skill",
        "skill disable bash_executor - Disable a skill",
        "skill execute bash_executor command=ls -la - Execute a skill",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行技能管理命令"""
        action = context.get_arg(0, "list")
        skill_mgr = SkillManager(self.config_manager, self.agent_id)

        if action == "list":
            skills = skill_mgr.list_skills()
            return CommandResult.success(
                message=f"Found {len(skills)} skills",
                data={"skills": skills}
            )

        elif action == "info":
            skill_id = context.get_arg(1)
            if not skill_id:
                return CommandResult.error(message="Skill ID required", usage="skill info <skill_id>")

            skill = skill_mgr.get_skill(skill_id)
            if skill:
                return CommandResult.success(data=skill.get_metadata())
            return CommandResult.error(message=f"Skill not found: {skill_id}")

        elif action == "enable":
            skill_id = context.get_arg(1)
            if skill_mgr.enable_skill(skill_id):
                return CommandResult.success(message=f"Enabled skill: {skill_id}")
            return CommandResult.error(message=f"Failed to enable skill: {skill_id}")

        elif action == "disable":
            skill_id = context.get_arg(1)
            if skill_mgr.disable_skill(skill_id):
                return CommandResult.success(message=f"Disabled skill: {skill_id}")
            return CommandResult.error(message=f"Failed to disable skill: {skill_id}")

        elif action == "execute":
            skill_id = context.get_arg(1)
            if not skill_id:
                return CommandResult.error(message="Skill ID required", usage="skill execute <skill_id> [params]")

            # 解析参数
            kwargs = context.kwargs
            try:
                result = skill_mgr.execute_skill(skill_id, **kwargs)
                return CommandResult.success(data=result)
            except Exception as e:
                return CommandResult.error(message=str(e))

        else:
            return CommandResult.error(
                message=f"Unknown action: {action}",
                usage="Usage: skill <list|info|enable|disable|execute>"
            )


class HookCommand(BaseCommand):
    """钩子管理命令"""

    command_id = "hook"
    command_name = "hook"
    command_description = "Manage hooks"
    command_usage = "hook <action> [options]"
    command_aliases = ["hk", "钩子"]
    command_examples = [
        "hook list - List all hooks",
        "hook info log_invocation - Show hook info",
        "hook enable log_invocation - Enable a hook",
        "hook disable log_invocation - Disable a hook",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行钩子管理命令"""
        action = context.get_arg(0, "list")
        hook_mgr = HookManager(self.config_manager, self.agent_id)

        if action == "list":
            hooks = hook_mgr.list_hooks()
            return CommandResult.success(
                message=f"Found {len(hooks)} hooks",
                data={"hooks": hooks}
            )

        elif action == "info":
            hook_id = context.get_arg(1)
            if not hook_id:
                return CommandResult.error(message="Hook ID required", usage="hook info <hook_id>")

            hooks = hook_mgr.list_hooks()
            for hook in hooks:
                if hook.get("hook_id") == hook_id:
                    return CommandResult.success(data=hook)
            return CommandResult.error(message=f"Hook not found: {hook_id}")

        elif action == "enable":
            hook_id = context.get_arg(1)
            if hook_mgr.enable_hook(hook_id):
                return CommandResult.success(message=f"Enabled hook: {hook_id}")
            return CommandResult.error(message=f"Failed to enable hook: {hook_id}")

        elif action == "disable":
            hook_id = context.get_arg(1)
            if hook_mgr.disable_hook(hook_id):
                return CommandResult.success(message=f"Disabled hook: {hook_id}")
            return CommandResult.error(message=f"Failed to disable hook: {hook_id}")

        else:
            return CommandResult.error(
                message=f"Unknown action: {action}",
                usage="Usage: hook <list|info|enable|disable>"
            )


class MemoryCommand(BaseCommand):
    """记忆管理命令"""

    command_id = "memory"
    command_name = "memory"
    command_description = "Manage memory"
    command_usage = "memory <action> [options]"
    command_aliases = ["mem", "记忆"]
    command_examples = [
        "memory list - List memory items",
        "memory search keyword - Search memory",
        "memory write some content - Write to memory",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行记忆管理命令"""
        from mul_agent.brain.handlers.memory import MemoryHandler

        action = context.get_arg(0, "list")
        handler = MemoryHandler(self.config_manager, self.agent_id)

        params = {"action": action}

        if action == "search":
            query = context.get_arg(1)
            if query:
                params["query"] = query
            else:
                return CommandResult.error(message="Query required", usage="memory search <query>")

        elif action == "write":
            content = context.get_arg(1)
            if content:
                params["content"] = {"text": content}
            else:
                return CommandResult.error(message="Content required", usage="memory write <content>")

        result = handler.handle(params)
        return CommandResult.success(data=result)


class BashCommand(BaseCommand):
    """Bash 命令"""

    command_id = "bash"
    command_name = "bash"
    command_description = "Execute shell commands"
    command_usage = "bash <command>"
    command_aliases = ["$", "sh", "执行"]
    command_examples = [
        "bash ls -la - List files",
        "$ cat file.txt - View file content",
        "bash pwd - Show current directory",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行 bash 命令"""
        from mul_agent.brain.handlers.bash import BashHandler

        # 获取命令
        command = " ".join(context.args[1:]) if context.args else context.get_arg(0, "")

        if not command:
            return CommandResult.error(
                message="Command required",
                usage="bash <command>"
            )

        handler = BashHandler(self.config_manager, self.agent_id)
        result = handler.handle({"command": command})

        if result.get("returncode") == 0:
            return CommandResult.success(
                message=result.get("stdout", ""),
                data=result
            )
        else:
            return CommandResult.error(
                message=result.get("stderr", "Command failed"),
                error=result.get("stderr", "Unknown error")
            )
