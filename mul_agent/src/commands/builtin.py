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


class TddCommand(BaseCommand):
    """TDD 命令 - 启动测试驱动开发工作流"""

    command_id = "tdd"
    command_name = "tdd"
    command_description = "Start Test-Driven Development workflow"
    command_usage = "tdd <task>"
    command_aliases = ["tdd", "测试驱动"]
    command_examples = [
        "tdd add user login feature - Add user login feature with TDD",
        "/tdd fix bug in calculator - Fix bug using TDD approach",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行 TDD 命令"""
        task = " ".join(context.args) if context.args else context.get_arg(0, "")

        if not task:
            return CommandResult.error(
                message="Task description required",
                usage="tdd <task description>"
            )

        # TDD 工作流：
        # 1. 分析任务
        # 2. 编写测试
        # 3. 运行测试（失败）
        # 4. 实现代码
        # 5. 运行测试（通过）
        # 6. 重构

        result = {
            "workflow": "TDD",
            "task": task,
            "steps": [
                {"step": 1, "action": "Analyze task requirements"},
                {"step": 2, "action": "Write failing tests first"},
                {"step": 3, "action": "Run tests to verify failure"},
                {"step": 4, "action": "Implement minimal code to pass"},
                {"step": 5, "action": "Run tests to verify success"},
                {"step": 6, "action": "Refactor while keeping tests green"},
            ],
            "status": "ready_to_start"
        }

        return CommandResult.success(
            message=f"Starting TDD workflow for: {task}",
            data=result
        )


class CodeReviewCommand(BaseCommand):
    """代码审查命令"""

    command_id = "code_review"
    command_name = "code-review"
    command_description = "Perform code review"
    command_usage = "code-review [file]"
    command_aliases = ["/review", "审查"]
    command_examples = [
        "code-review - Review recent changes",
        "code-review src/main.py - Review specific file",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行代码审查命令"""
        file_path = context.get_arg(0, "")

        review_scope = {
            "file": file_path if file_path else "recent_changes",
            "checklist": [
                "Code style and formatting",
                "Error handling",
                "Security vulnerabilities",
                "Performance considerations",
                "Test coverage",
                "Documentation",
            ]
        }

        return CommandResult.success(
            message=f"Starting code review for: {file_path or 'recent changes'}",
            data=review_scope
        )


class BuildFixCommand(BaseCommand):
    """构建修复命令"""

    command_id = "build_fix"
    command_name = "build-fix"
    command_description = "Fix build errors"
    command_usage = "build-fix"
    command_aliases = ["/build", "修复构建"]
    command_examples = [
        "build-fix - Analyze and fix build errors",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行构建修复命令"""
        workflow = {
            "steps": [
                {"step": 1, "action": "Run build command"},
                {"step": 2, "action": "Parse error messages"},
                {"step": 3, "action": "Categorize errors (type, syntax, import)"},
                {"step": 4, "action": "Fix errors incrementally"},
                {"step": 5, "action": "Verify build succeeds"},
            ],
            "status": "ready_to_start"
        }

        return CommandResult.success(
            message="Starting build fix workflow",
            data=workflow
        )


class VerifyCommand(BaseCommand):
    """验证命令 - 完整验证循环"""

    command_id = "verify"
    command_name = "verify"
    command_description = "Run verification loop"
    command_usage = "verify"
    command_aliases = ["/check", "验证"]
    command_examples = [
        "verify - Run full verification",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行验证命令"""
        verification = {
            "checks": [
                {"name": "Build", "status": "pending"},
                {"name": "Lint", "status": "pending"},
                {"name": "Type Check", "status": "pending"},
                {"name": "Unit Tests", "status": "pending"},
                {"name": "Integration Tests", "status": "pending"},
                {"name": "Security Scan", "status": "pending"},
            ],
            "status": "ready_to_start"
        }

        return CommandResult.success(
            message="Starting verification loop",
            data=verification
        )


class TestCoverageCommand(BaseCommand):
    """测试覆盖率命令"""

    command_id = "test_coverage"
    command_name = "test-coverage"
    command_description = "Check test coverage"
    command_usage = "test-coverage"
    command_aliases = ["/coverage", "覆盖率"]
    command_examples = [
        "test-coverage - Show coverage report",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行测试覆盖率命令"""
        coverage = {
            "target": "80%",
            "status": "checking",
            "report": {
                "overall": "pending",
                "by_module": {}
            }
        }

        return CommandResult.success(
            message="Checking test coverage",
            data=coverage
        )


class SecurityScanCommand(BaseCommand):
    """安全扫描命令"""

    command_id = "security_scan"
    command_name = "security-scan"
    command_description = "Perform security scan"
    command_usage = "security-scan"
    command_aliases = ["/security", "安全检查"]
    command_examples = [
        "security-scan - Scan for vulnerabilities",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行安全扫描命令"""
        scan = {
            "checks": [
                "Hardcoded secrets",
                "SQL injection vulnerabilities",
                "XSS vulnerabilities",
                "CSRF protection",
                "Authentication/authorization",
                "Input validation",
                "Rate limiting",
            ],
            "status": "ready_to_start"
        }

        return CommandResult.success(
            message="Starting security scan",
            data=scan
        )


class PlanCommand(BaseCommand):
    """计划命令 - 创建实施计划"""

    command_id = "plan"
    command_name = "plan"
    command_description = "Create implementation plan"
    command_usage = "plan <task>"
    command_aliases = ["/plan", "计划"]
    command_examples = [
        "plan add user authentication - Create plan for adding user auth",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行计划命令"""
        task = " ".join(context.args) if context.args else context.get_arg(0, "")

        if not task:
            return CommandResult.error(
                message="Task description required",
                usage="plan <task description>"
            )

        plan = {
            "task": task,
            "status": "analyzing",
            "requires_confirmation": True,
            "next_step": "Waiting for user confirmation to generate detailed plan"
        }

        return CommandResult.success(
            message=f"Creating plan for: {task}",
            data=plan
        )


class E2eCommand(BaseCommand):
    """E2E 测试命令"""

    command_id = "e2e"
    command_name = "e2e"
    command_description = "Run end-to-end tests"
    command_usage = "e2e [test_name]"
    command_aliases = ["/e2e", "端到端测试"]
    command_examples = [
        "e2e - Run all E2E tests",
        "e2e login_spec - Run specific test",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行 E2E 测试命令"""
        test_name = context.get_arg(0, "all")

        e2e = {
            "test": test_name,
            "framework": "Playwright",
            "status": "ready_to_run",
            "artifacts": {
                "screenshots": True,
                "videos": True,
                "traces": True
            }
        }

        return CommandResult.success(
            message=f"Running E2E tests: {test_name}",
            data=e2e
        )


class PermissionCommand(BaseCommand):
    """权限管理命令"""

    command_id = "permission"
    command_name = "permission"
    command_description = "Manage permission settings"
    command_usage = "permission [list|approve|deny|clear]"
    command_aliases = ["/perm", "权限"]
    command_examples = [
        "permission list - List all permission settings",
        "permission approve <pattern> - Add auto-approve pattern",
        "permission deny <pattern> - Add auto-deny pattern",
        "permission clear - Clear session confirmations",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行权限管理命令"""
        from mul_agent.hooks.permission import get_permission_manager

        action = context.get_arg(0, "list").lower()
        manager = get_permission_manager()

        if action == "list":
            config = manager.get_config()
            output_lines = ["## 权限配置\n"]

            auto_approve = config.get("auto_approve", [])
            if auto_approve:
                output_lines.append("**自动批准**:")
                for pattern in auto_approve[:10]:
                    output_lines.append(f"  - `{pattern}`")
                if len(auto_approve) > 10:
                    output_lines.append(f"  ... 还有 {len(auto_approve) - 10} 个")
                output_lines.append("")

            auto_deny = config.get("auto_deny", [])
            if auto_deny:
                output_lines.append("**自动拒绝**:")
                for pattern in auto_deny[:10]:
                    output_lines.append(f"  - `{pattern}`")
                if len(auto_deny) > 10:
                    output_lines.append(f"  ... 还有 {len(auto_deny) - 10} 个")
                output_lines.append("")

            remembered = config.get("remembered_choices", {})
            if remembered:
                output_lines.append(f"**记住的选择**: {len(remembered)} 个")
                output_lines.append("")

            output_lines.append(f"会话确认数：{config.get('session_confirmations_count', 0)}")

            return CommandResult.success(
                message="\n".join(output_lines),
                data=config
            )

        elif action == "approve":
            pattern = context.get_arg(1)
            if not pattern:
                return CommandResult.error(
                    message="Pattern required",
                    usage="permission approve <pattern>"
                )
            manager.add_auto_approve(pattern)
            return CommandResult.success(
                message=f"已添加自动批准模式：`{pattern}`"
            )

        elif action == "deny":
            pattern = context.get_arg(1)
            if not pattern:
                return CommandResult.error(
                    message="Pattern required",
                    usage="permission deny <pattern>"
                )
            manager.add_auto_deny(pattern)
            return CommandResult.success(
                message=f"已添加自动拒绝模式：`{pattern}`"
            )

        elif action == "clear":
            manager.clear_session_confirmations()
            return CommandResult.success(
                message="已清除会话期间的确认记录"
            )

        else:
            return CommandResult.error(
                message=f"Unknown action: {action}",
                usage="permission [list|approve|deny|clear]"
            )


import json as json_module


class MCPCommand(BaseCommand):
    """MCP 服务器管理命令"""

    command_id = "mcp"
    command_name = "mcp"
    command_description = "Manage MCP servers and tools"
    command_usage = "mcp [list|connect|disconnect|status|tools]"
    command_aliases = ["/mcp", "MCP"]
    command_examples = [
        "mcp list - List all MCP servers",
        "mcp connect filesystem - Connect to filesystem MCP server",
        "mcp status - Show MCP server status",
        "mcp tools - List all available MCP tools",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行 MCP 管理命令"""
        from mul_agent.mcp.client import (
            get_mcp_client,
            BUILTIN_MCP_SERVERS,
            MCPServerConfig
        )
        import asyncio

        action = context.get_arg(0, "list").lower()
        client = get_mcp_client()

        if action == "list":
            # 列出所有可用的 MCP 服务器
            output_lines = ["## 可用的 MCP 服务器\n"]
            output_lines.append("**内置服务器**:\n")
            for name, config in BUILTIN_MCP_SERVERS.items():
                output_lines.append(f"- `{name}`: {config.command} {' '.join(config.args)}")

            output_lines.append("\n**已连接的服务器**:\n")
            for name, server in client.servers.items():
                status = server.status.value
                tools_count = len(server.tools)
                output_lines.append(f"- `{name}`: {status} ({tools_count} tools)")

            return CommandResult.success(
                message="\n".join(output_lines),
                data={
                    "builtin_servers": list(BUILTIN_MCP_SERVERS.keys()),
                    "connected_servers": list(client.servers.keys())
                }
            )

        elif action == "connect":
            # 连接到指定 MCP 服务器
            server_name = context.get_arg(1)
            if not server_name:
                return CommandResult.error(
                    message="Server name required",
                    usage="mcp connect <server_name>"
                )

            # 检查是否是内置服务器
            if server_name in BUILTIN_MCP_SERVERS:
                config = BUILTIN_MCP_SERVERS[server_name]
                client.add_server(config)

                # 异步连接
                async def connect():
                    return await client.connect_server(server_name)

                # 运行异步连接
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    success = loop.run_until_complete(connect())
                    loop.close()

                    if success:
                        return CommandResult.success(
                            message=f"已连接到 MCP 服务器：`{server_name}`"
                        )
                    else:
                        return CommandResult.error(
                            message=f"连接失败：{server_name}"
                        )
                except Exception as e:
                    return CommandResult.error(
                        message=f"连接错误：{str(e)}"
                    )
            else:
                return CommandResult.error(
                    message=f"Unknown server: {server_name}. Use 'mcp list' to see available servers."
                )

        elif action == "disconnect":
            # 断开指定服务器连接
            server_name = context.get_arg(1)
            if not server_name:
                return CommandResult.error(
                    message="Server name required",
                    usage="mcp disconnect <server_name>"
                )

            async def disconnect():
                return await client.disconnect_server(server_name)

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                success = loop.run_until_complete(disconnect())
                loop.close()

                if success:
                    return CommandResult.success(
                        message=f"已断开 MCP 服务器：`{server_name}`"
                    )
                else:
                    return CommandResult.error(
                        message=f"Server not found: {server_name}"
                    )
            except Exception as e:
                return CommandResult.error(
                    message=f"断开连接错误：{str(e)}"
                )

        elif action == "status":
            # 显示服务器状态
            status = client.get_server_status()
            output_lines = ["## MCP 服务器状态\n"]
            for name, info in status.items():
                output_lines.append(f"### {name}")
                output_lines.append(f"- 状态：{info['status']}")
                output_lines.append(f"- 工具数：{info['tools_count']}")
                output_lines.append(f"- 传输：{info['transport']}")
                output_lines.append(f"- 连接：{info['url']}\n")

            if not status:
                output_lines.append("暂无已连接的 MCP 服务器")

            return CommandResult.success(
                message="\n".join(output_lines),
                data={"servers": status}
            )

        elif action == "tools":
            # 列出所有可用的 MCP 工具
            tools = client.list_tools()
            output_lines = ["## 可用的 MCP 工具\n"]

            for tool in tools:
                output_lines.append(f"### {tool.name} (来自：{tool.server_name})")
                output_lines.append(f"{tool.description}\n")
                if tool.input_schema:
                    schema_str = json_module.dumps(tool.input_schema)
                    output_lines.append(f"**Schema**: `{schema_str[:200]}...`\n")

            if not tools:
                output_lines.append("暂无可用的 MCP 工具。\n")
                output_lines.append("使用 `mcp connect <server>` 连接服务器以获取工具。")

            return CommandResult.success(
                message="\n".join(output_lines),
                data={"tools": [t.to_dict() for t in tools]}
            )

        else:
            return CommandResult.error(
                message=f"Unknown action: {action}",
                usage="mcp [list|connect|disconnect|status|tools]"
            )


class SearchCommand(BaseCommand):
    """代码搜索命令"""

    command_id = "search"
    command_name = "search"
    command_description = "Search codebase for symbols and text"
    command_usage = "search <query> [--limit N] [--file FILE] [--lang LANG]"
    command_aliases = ["/search", "搜索", "grep"]
    command_examples = [
        "search MyClass - Search for MyClass symbol",
        "search --limit 10 def my_function - Search with limit",
        "search --file *.py import - Search only in .py files",
        "search --lang python class - Search Python classes",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行搜索命令"""
        from mul_agent.tools.search import get_code_index, search_code, SymbolType

        # 解析参数
        args = context.args
        query_parts = []
        limit = 20
        file_filter = None
        language_filter = None
        symbol_type_filter = None

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--limit" and i + 1 < len(args):
                try:
                    limit = int(args[i + 1])
                    i += 2
                    continue
                except ValueError:
                    pass
            elif arg == "--file" and i + 1 < len(args):
                file_filter = args[i + 1]
                i += 2
                continue
            elif arg == "--lang" and i + 1 < len(args):
                language_filter = args[i + 1]
                i += 2
                continue
            elif arg == "--type" and i + 1 < len(args):
                try:
                    symbol_type_filter = [SymbolType(args[i + 1])]
                    i += 2
                    continue
                except ValueError:
                    pass
            else:
                query_parts.append(arg)
                i += 1

        query = " ".join(query_parts)

        if not query:
            return CommandResult.error(
                message="Search query required",
                usage="search <query> [--limit N] [--file FILE] [--lang LANG]"
            )

        # 执行搜索
        index = get_code_index()
        results = index.search(
            query,
            limit=limit,
            file_filter=file_filter,
            language_filter=language_filter,
            symbol_type_filter=symbol_type_filter
        )

        if not results:
            return CommandResult.success(
                message=f"没有找到匹配 '{query}' 的结果",
                data={"query": query, "count": 0}
            )

        # 格式化输出
        output_lines = [f"## 搜索结果：'{query}' (共 {len(results)} 条)\n"]

        for idx, result in enumerate(results, 1):
            symbol = result.symbol
            if symbol:
                output_lines.append(f"**{idx}.** `{symbol.name}` ({symbol.type.value})")
                output_lines.append(f"   文件：`{symbol.file_path}` 第 {symbol.line_number} 行")
            else:
                output_lines.append(f"**{idx}.** `{result.content[:50]}...`")
                output_lines.append(f"   文件：`{result.file_path}` 第 {result.line_number} 行")

            if result.context:
                # 显示上下文
                context_lines = result.context.split("\n")
                for ctx_line in context_lines[:3]:
                    if ctx_line.strip():
                        output_lines.append(f"   `{ctx_line.strip()}`")

            output_lines.append("")

        # 获取统计信息
        stats = index.get_stats()

        output_lines.append(f"\n**索引统计**: {stats['total_symbols']} 个符号，{stats['indexed_files']} 个文件")

        return CommandResult.success(
            message="\n".join(output_lines),
            data={
                "query": query,
                "count": len(results),
                "results": [r.to_dict() for r in results],
                "stats": stats
            }
        )


class CodeIndexCommand(BaseCommand):
    """代码索引管理命令"""

    command_id = "code-index"
    command_name = "code-index"
    command_description = "Manage code search index"
    command_usage = "code-index [build|stats|clear]"
    command_aliases = ["/index", "索引"]
    command_examples = [
        "code-index build - Build code index",
        "code-index stats - Show index statistics",
        "code-index clear - Clear code index",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行索引管理命令"""
        from mul_agent.tools.search import get_code_index

        action = context.get_arg(0, "stats").lower()
        index = get_code_index()

        if action == "build":
            # 构建索引
            incremental = "--full" not in context.args
            with_message = "增量" if incremental else "完全"

            # 返回进度信息
            return CommandResult.success(
                message=f"正在构建{with_message}代码索引...\n\n稍后使用 `code-index stats` 查看结果。",
                data={"action": "build", "incremental": incremental}
            )

        elif action == "stats":
            # 显示统计
            stats = index.get_stats()

            output_lines = ["## 代码索引统计\n"]
            output_lines.append(f"- **总符号数**: {stats['total_symbols']}")
            output_lines.append(f"- **唯一符号**: {stats['unique_symbols']}")
            output_lines.append(f"- **索引文件**: {stats['indexed_files']}")

            if stats.get("symbol_by_type"):
                output_lines.append("\n**符号类型分布**:")
                for type_name, count in sorted(stats["symbol_by_type"].items()):
                    output_lines.append(f"  - {type_name}: {count}")

            return CommandResult.success(
                message="\n".join(output_lines),
                data=stats
            )

        elif action == "clear":
            # 清除索引
            index.clear()
            return CommandResult.success(
                message="已清除代码索引"
            )

        else:
            return CommandResult.error(
                message=f"Unknown action: {action}",
                usage="code-index [build|stats|clear]"
            )


class LearnCommand(BaseCommand):
    """技能学习管理命令"""

    command_id = "learn"
    command_name = "learn"
    command_description = "Manage skill learning and evolution"
    command_usage = "learn [status|list|export|import]"
    command_aliases = ["/learn", "学习"]
    command_examples = [
        "learn status - Show skill evolution status",
        "learn list - List all learned skills",
        "learn export skills.json - Export learned skills",
        "learn import skills.json - Import learned skills",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行学习管理命令"""
        action = context.get_arg(0, "status").lower()

        if action == "status":
            # 显示技能进化状态
            from mul_agent.skills.evolution import get_skill_evolution_system
            system = get_skill_evolution_system()
            stats = system.get_stats()

            output_lines = ["## 技能进化状态\n"]
            output_lines.append(f"- **总模式数**: {stats['total_patterns']}")
            output_lines.append(f"- **已学习技能**: {stats['learned_patterns']}")
            output_lines.append(f"- **提取的模式**: {stats['extracted_patterns']}")
            output_lines.append(f"- **平均置信度**: {stats['avg_confidence']}")
            output_lines.append(f"- **平均成功率**: {stats['avg_success_rate']}")
            output_lines.append(f"- **执行历史数**: {stats['execution_history_size']}")

            return CommandResult.success(
                message="\n".join(output_lines),
                data=stats
            )

        elif action == "list":
            # 列出已学习的技能
            from mul_agent.skills.evolution import get_skill_evolution_system
            system = get_skill_evolution_system()
            min_confidence = 0.5

            if "--all" in context.args:
                min_confidence = 0

            patterns = system.list_patterns(min_confidence=min_confidence)

            if not patterns:
                return CommandResult.success(
                    message="暂无已学习的技能",
                    data={"patterns": []}
                )

            output_lines = [f"## 已学习的技能 (共 {len(patterns)} 个)\n"]

            for i, p in enumerate(patterns[:20], 1):  # 只显示前 20 个
                output_lines.append(f"### {i}. {p['name']}")
                output_lines.append(f"- **置信度**: {p['confidence']:.2f}")
                output_lines.append(f"- **成功率**: {p['success_rate']:.2f}")
                output_lines.append(f"- **使用次数**: {p['usage_count']}")
                output_lines.append(f"- **触发词**: {', '.join(p['trigger_keywords'][:5])}")
                output_lines.append(f"- **路由**: {p['route']}")
                output_lines.append("")

            if len(patterns) > 20:
                output_lines.append(f"... 还有 {len(patterns) - 20} 个技能")

            return CommandResult.success(
                message="\n".join(output_lines),
                data={"patterns": patterns, "count": len(patterns)}
            )

        elif action == "export":
            # 导出技能
            from mul_agent.skills.evolution import get_skill_evolution_system
            system = get_skill_evolution_system()

            filepath = context.get_arg(1, "storage/skill_evolution/exported_skills.json")
            system.export_patterns(filepath)

            return CommandResult.success(
                message=f"已导出技能到：`{filepath}`"
            )

        elif action == "import":
            # 导入技能
            from mul_agent.skills.evolution import get_skill_evolution_system
            system = get_skill_evolution_system()

            filepath = context.get_arg(1)
            if not filepath:
                return CommandResult.error(
                    message="File path required",
                    usage="learn import <filepath>"
                )

            try:
                system.import_patterns(filepath)
                return CommandResult.success(
                    message=f"已从 `{filepath}` 导入技能"
                )
            except Exception as e:
                return CommandResult.error(
                    message=f"导入失败：{str(e)}"
                )

        else:
            return CommandResult.error(
                message=f"Unknown action: {action}",
                usage="learn [status|list|export|import]"
            )


class CheckpointCommand(BaseCommand):
    """检查点管理命令"""

    command_id = "checkpoint"
    command_name = "checkpoint"
    command_description = "Manage session checkpoints"
    command_usage = "checkpoint [create|list|restore|delete|diff]"
    command_aliases = ["/checkpoint", "检查点", "存档"]
    command_examples = [
        "checkpoint create '完成用户认证' - Create checkpoint with description",
        "checkpoint list - List all checkpoints",
        "checkpoint restore abc123 - Restore to checkpoint",
        "checkpoint delete abc123 - Delete checkpoint",
        "checkpoint diff abc123 - Show checkpoint changes",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行检查点管理命令"""
        from mul_agent.brain.checkpoint import checkpoint_manager

        action = context.get_arg(0, "list").lower()

        if action == "create":
            # 创建检查点
            description = context.get_arg(1)
            if not description:
                # 使用当前任务作为描述
                description = context.state.get("current_task", "手动检查点")

            checkpoint = checkpoint_manager.create_checkpoint(
                session_id=context.state.get("session_id", ""),
                agent_id=self.agent_id,
                description=description,
                working_directory=context.state.get("working_directory"),
                metadata={
                    "history_length": len(context.state.get("history", []))
                }
            )

            return CommandResult.success(
                message=f"已创建检查点：`{checkpoint.checkpoint_id}`\n\n描述：{description}",
                data={"checkpoint": checkpoint.to_dict()}
            )

        elif action == "list":
            # 列出检查点
            limit = 20
            for arg in context.args:
                if arg.isdigit():
                    limit = int(arg)
                    break

            checkpoints = checkpoint_manager.list_checkpoints(
                agent_id=self.agent_id,
                limit=limit
            )

            if not checkpoints:
                return CommandResult.success(
                    message="暂无检查点",
                    data={"checkpoints": []}
                )

            output_lines = [f"## 检查点列表 (共 {len(checkpoints)} 个)\n"]

            for cp in checkpoints[:limit]:
                time_str = time.strftime(
                    "%Y-%m-%d %H:%M:%S",
                    time.localtime(cp.timestamp)
                )
                output_lines.append(f"### `{cp.checkpoint_id}`")
                output_lines.append(f"- **描述**: {cp.description}")
                output_lines.append(f"- **时间**: {time_str}")
                if cp.working_directory:
                    output_lines.append(f"- **目录**: {cp.working_directory}")
                if cp.git_commit:
                    output_lines.append(f"- **Git**: `{cp.git_commit}`")
                if cp.files_changed:
                    output_lines.append(f"- **变更文件**: {len(cp.files_changed)} 个")
                output_lines.append("")

            if len(checkpoints) > limit:
                output_lines.append(f"... 还有 {len(checkpoints) - limit} 个检查点")

            return CommandResult.success(
                message="\n".join(output_lines),
                data={"checkpoints": [cp.to_dict() for cp in checkpoints]}
            )

        elif action == "restore":
            # 恢复检查点
            checkpoint_id = context.get_arg(1)
            if not checkpoint_id:
                return CommandResult.error(
                    message="Checkpoint ID required",
                    usage="checkpoint restore <checkpoint_id>"
                )

            restore_info = checkpoint_manager.restore_checkpoint(checkpoint_id)

            if not restore_info:
                return CommandResult.error(
                    message=f"Checkpoint not found: {checkpoint_id}"
                )

            output_lines = ["## 恢复检查点\n"]
            output_lines.append(f"- **检查点**: `{checkpoint_id}`")
            output_lines.append(f"- **描述**: {restore_info.get('description', '')}")
            output_lines.append(f"- **会话**: {restore_info.get('session_id', '')}")

            if restore_info.get("working_directory"):
                output_lines.append(f"- **工作目录**: {restore_info['working_directory']}")

            if restore_info.get("git_commit"):
                output_lines.append(f"- **Git Commit**: `{restore_info['git_commit']}`")
                if restore_info.get("restore_command"):
                    output_lines.append(f"- **恢复命令**: `{restore_info['restore_command']}`")

            output_lines.append("\n⚠️ 注意：实际恢复操作需要手动执行上述命令")

            return CommandResult.success(
                message="\n".join(output_lines),
                data={"restore_info": restore_info}
            )

        elif action == "delete":
            # 删除检查点
            checkpoint_id = context.get_arg(1)
            if not checkpoint_id:
                return CommandResult.error(
                    message="Checkpoint ID required",
                    usage="checkpoint delete <checkpoint_id>"
                )

            success = checkpoint_manager.delete_checkpoint(checkpoint_id)

            if success:
                return CommandResult.success(
                    message=f"已删除检查点：`{checkpoint_id}`"
                )
            else:
                return CommandResult.error(
                    message=f"Checkpoint not found: {checkpoint_id}"
                )

        elif action == "diff":
            # 显示检查点变更
            checkpoint_id = context.get_arg(1)
            if not checkpoint_id:
                return CommandResult.error(
                    message="Checkpoint ID required",
                    usage="checkpoint diff <checkpoint_id>"
                )

            diff_info = checkpoint_manager.get_checkpoint_diff(checkpoint_id)

            if not diff_info:
                return CommandResult.error(
                    message=f"Checkpoint not found: {checkpoint_id}"
                )

            output_lines = [f"## 检查点变更：`{checkpoint_id}`\n"]
            output_lines.append(f"- **变更文件数**: {diff_info.get('file_count', 0)}")

            if diff_info.get("files_changed"):
                output_lines.append("\n**变更文件列表**:\n")
                for f in diff_info["files_changed"][:20]:
                    output_lines.append(f"  - `{f}`")
                if len(diff_info["files_changed"]) > 20:
                    output_lines.append(f"  ... 还有 {len(diff_info['files_changed']) - 20} 个")

            if diff_info.get("git_diff_command"):
                output_lines.append(f"\n**查看 Git 差异**: `{diff_info['git_diff_command']}`")

            return CommandResult.success(
                message="\n".join(output_lines),
                data=diff_info
            )

        elif action == "stats":
            # 显示统计
            stats = checkpoint_manager.get_stats()

            output_lines = ["## 检查点统计\n"]
            output_lines.append(f"- **总检查点数**: {stats['total_checkpoints']}")

            if stats.get("by_agent"):
                output_lines.append("\n**按 Agent 分布**:\n")
                for agent_id, count in sorted(stats["by_agent"].items()):
                    output_lines.append(f"  - `{agent_id}`: {count}")

            return CommandResult.success(
                message="\n".join(output_lines),
                data=stats
            )

        else:
            return CommandResult.error(
                message=f"Unknown action: {action}",
                usage="checkpoint [create|list|restore|delete|diff|stats]"
            )


import time as time_module


class ObserveCommand(BaseCommand):
    """可观测性仪表板命令"""

    command_id = "observe"
    command_name = "observe"
    command_description = "View agent observability dashboard"
    command_usage = "observe [dashboard|logs|traces|metrics]"
    command_aliases = ["/observe", "观测"]
    command_examples = [
        "observe dashboard - Show observability dashboard",
        "observe logs --level error - Show error logs",
        "observe traces - Show recent traces",
        "observe metrics - Show metric statistics",
    ]

    def _initialize(self) -> None:
        """初始化"""
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        """执行观测命令"""
        action = context.get_arg(0, "dashboard").lower()

        if action == "dashboard":
            # 显示仪表板
            from mul_agent.observability.platform import get_observability_platform
            platform = get_observability_platform(self.agent_id)
            data = platform.get_dashboard_data()

            output_lines = ["## Agent 可观测性仪表板\n"]
            output_lines.append(f"**Agent**: {data['agent_id']}")
            output_lines.append(f"**Session**: {data['session_id']}\n")

            # 指标统计
            output_lines.append("### 性能指标\n")
            metrics_data = data.get('metrics', {})
            for metric_name, stats in metrics_data.items():
                if stats and isinstance(stats, dict) and stats.get('count', 0) > 0:
                    output_lines.append(f"**{metric_name}**:")
                    output_lines.append(f"  - 平均：{stats.get('avg', 0):.2f}ms")
                    output_lines.append(f"  - P95: {stats.get('p95', 0):.2f}ms")
                    output_lines.append(f"  - P99: {stats.get('p99', 0):.2f}ms")
                    output_lines.append("")

            # 最近错误
            if data.get('recent_errors'):
                output_lines.append("### 最近错误\n")
                for err in data['recent_errors'][:5]:
                    output_lines.append(f"- {err.get('message', 'Unknown error')}")
                    output_lines.append(f"  时间：{err.get('datetime', 'N/A')}")
                output_lines.append("")

            # 活动 Span
            if data.get('active_spans'):
                output_lines.append("### 活动追踪\n")
                for span in data['active_spans'][:5]:
                    output_lines.append(f"- {span.get('name', 'unknown')} ({span.get('type', 'unknown')})")
                    output_lines.append(f"  状态：{span.get('status', 'unknown')}")

            if not output_lines[-1].strip():
                output_lines.append("\n暂无数据。执行一些操作后再来查看。")

            return CommandResult.success(
                message="\n".join(output_lines),
                data=data
            )

        elif action == "logs":
            # 查看日志
            from mul_agent.observability.platform import get_observability_platform, LogLevel
            platform = get_observability_platform(self.agent_id)

            level = None
            if "--level" in context.args:
                level_idx = context.args.index("--level") + 1
                if level_idx < len(context.args):
                    level_str = context.args[level_idx].lower()
                    for l in LogLevel:
                        if l.value == level_str:
                            level = l
                            break

            limit = 50
            if "--limit" in context.args:
                limit_idx = context.args.index("--limit") + 1
                if limit_idx < len(context.args):
                    try:
                        limit = int(context.args[limit_idx])
                    except ValueError:
                        pass

            logs = platform.get_recent_logs(limit=limit, level=level)

            if not logs:
                return CommandResult.success(
                    message="暂无日志记录",
                    data={"logs": []}
                )

            output_lines = [f"## 最近日志 (共 {len(logs)} 条)\n"]

            level_emoji = {"debug": "🔍", "info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🔥"}

            for log in logs[:20]:
                emoji = level_emoji.get(log.get("level"), "📝")
                output_lines.append(f"{emoji} [{log.get('level', 'info').upper()}] {log.get('message', '')}")
                output_lines.append(f"   时间：{log.get('datetime', 'N/A')}")
                output_lines.append("")

            if len(logs) > 20:
                output_lines.append(f"... 还有 {len(logs) - 20} 条日志")

            return CommandResult.success(
                message="\n".join(output_lines),
                data={"logs": logs, "count": len(logs)}
            )

        elif action == "traces":
            # 查看追踪
            output_lines = ["## 最近追踪\n"]
            output_lines.append("追踪功能正在开发中...")
            return CommandResult.success(
                message="\n".join(output_lines),
                data={"message": "Traces feature coming soon"}
            )

        elif action == "metrics":
            # 查看指标
            from mul_agent.observability.platform import get_observability_platform
            platform = get_observability_platform(self.agent_id)

            key_metrics = [
                "llm_call_duration_ms",
                "tool_execution_duration_ms",
                "route_dispatch_duration_ms"
            ]

            output_lines = ["## 性能指标统计\n"]

            for metric_name in key_metrics:
                stats = platform.get_metric_stats(metric_name)
                if stats and stats.get('count', 0) > 0:
                    output_lines.append(f"### {metric_name}")
                    output_lines.append(f"- 调用次数：{stats.get('count', 0)}")
                    output_lines.append(f"- 平均值：{stats.get('avg', 0):.2f}ms")
                    output_lines.append(f"- 最小值：{stats.get('min', 0):.2f}ms")
                    output_lines.append(f"- 最大值：{stats.get('max', 0):.2f}ms")
                    output_lines.append(f"- P50: {stats.get('p50', 0):.2f}ms")
                    output_lines.append(f"- P95: {stats.get('p95', 0):.2f}ms")
                    output_lines.append(f"- P99: {stats.get('p99', 0):.2f}ms\n")
                else:
                    output_lines.append(f"### {metric_name}")
                    output_lines.append("暂无数据\n")

            return CommandResult.success(
                message="\n".join(output_lines),
                data={"metrics": {m: platform.get_metric_stats(m) for m in key_metrics}}
            )

        else:
            return CommandResult.error(
                message=f"Unknown action: {action}",
                usage="observe [dashboard|logs|traces|metrics]"
            )
