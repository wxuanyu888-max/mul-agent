"""Dialog Commands - 对话管理命令

实现 Claude Code 风格的对话管理命令：
- /history - 查看会话历史
- /undo - 撤销上一步操作
- /summary - 生成会话摘要
- /clear - 清除当前会话
- /resume - 恢复之前的会话
- /delegate - 委派任务给团队（Commander 模式）
"""

from mul_agent.commands.base import BaseCommand, CommandResult, CommandContext
from typing import Dict, Any, List
from pathlib import Path
import json
from datetime import datetime


class HistoryCommand(BaseCommand):
    """查看会话历史"""

    metadata = {
        "name": "history",
        "description": "查看当前会话的对话历史",
        "usage": "/history [limit]",
        "examples": [
            "/history",
            "/history 10",
        ],
        "aliases": ["/h", "/log"]
    }

    def _initialize(self) -> None:
        """初始化命令"""
        self.command_id = "history"
        self.command_name = "history"
        self.command_description = self.metadata["description"]
        self.command_usage = self.metadata["usage"]
        self.command_examples = self.metadata["examples"]
        self.command_aliases = self.metadata["aliases"]

    def execute(self, context: CommandContext) -> CommandResult:
        """执行历史查看命令"""
        limit = 20
        if context.args and len(context.args) > 0:
            try:
                limit = int(context.args[0])
            except ValueError:
                pass

        # 获取会话历史
        history = context.state.get("history", [])

        # 截取最近的记录
        recent_history = history[-limit:] if len(history) > limit else history

        if not recent_history:
            return CommandResult.success(
                data={"history": []},
                message="当前会话暂无历史记录"
            )

        # 格式化输出
        output_lines = [f"## 会话历史 (最近 {len(recent_history)} 条)\n"]
        for i, item in enumerate(recent_history, 1):
            role = item.get("role", "unknown")
            content = str(item.get("content", ""))[:200]
            timestamp = item.get("timestamp", "")
            output_lines.append(f"**{i}.** [{role}] {content}...")
            if timestamp:
                output_lines[-1] += f" _({timestamp})_"
            output_lines.append("")

        return CommandResult.success(
            data={"history": recent_history, "count": len(recent_history)},
            message="\n".join(output_lines)
        )


class UndoCommand(BaseCommand):
    """撤销上一步操作"""

    metadata = {
        "name": "undo",
        "description": "撤销上一步执行的操作",
        "usage": "/undo [target]",
        "examples": [
            "/undo",
            "/undo last",
            "/undo 2",  # 撤销最近 2 步
        ],
        "aliases": ["/revert"]
    }

    def _initialize(self) -> None:
        """初始化命令"""
        self.command_id = "undo"
        self.command_name = "undo"
        self.command_description = self.metadata["description"]
        self.command_usage = self.metadata["usage"]
        self.command_examples = self.metadata["examples"]
        self.command_aliases = self.metadata["aliases"]

    def execute(self, context: CommandContext) -> CommandResult:
        """执行撤销命令"""
        # 获取执行历史
        exec_history = context.state.get("exec_history", [])

        if not exec_history:
            return CommandResult.error("没有可撤销的操作")

        # 默认撤销最后一步
        steps_to_undo = 1
        if context.args and len(context.args) > 0:
            arg = context.args[0]
            if arg.isdigit():
                steps_to_undo = int(arg)
            elif arg == "last":
                steps_to_undo = 1

        # 检查是否有足够的历史
        if steps_to_undo > len(exec_history):
            return CommandResult.error(f"只有 {len(exec_history)} 步操作，无法撤销 {steps_to_undo} 步")

        # 获取要撤销的操作
        operations_to_undo = exec_history[-steps_to_undo:]

        # 构建撤销信息
        undo_info = []
        for op in reversed(operations_to_undo):
            route = op.get("route", "unknown")
            action = op.get("action", "")
            undo_info.append(f"- {route}: {action[:100]}")

        # 注意：实际的撤销逻辑需要在 Brain 层面实现
        # 这里只返回要撤销的操作信息
        return CommandResult.success(
            data={
                "operations_to_undo": operations_to_undo,
                "count": len(operations_to_undo)
            },
            message=f"## 准备撤销以下操作:\n\n" + "\n".join(undo_info) + "\n\n⚠️ 注意：实际撤销操作需要 Brain 支持"
        )


class SummaryCommand(BaseCommand):
    """生成会话摘要"""

    metadata = {
        "name": "summary",
        "description": "生成当前会话的摘要总结",
        "usage": "/summary",
        "examples": ["/summary"],
        "aliases": ["/sum", "/recap"]
    }

    def _initialize(self) -> None:
        """初始化命令"""
        self.command_id = "summary"
        self.command_name = "summary"
        self.command_description = self.metadata["description"]
        self.command_usage = self.metadata["usage"]
        self.command_examples = self.metadata["examples"]
        self.command_aliases = self.metadata["aliases"]

    def execute(self, context: CommandContext) -> CommandResult:
        """执行摘要命令"""
        # 获取会话历史
        history = context.state.get("history", [])

        if not history:
            return CommandResult.success(
                data={"summary": "会话为空"},
                message="当前会话暂无内容"
            )

        # 提取关键信息
        user_inputs = [h for h in history if h.get("role") == "user"]
        assistant_responses = [h for h in history if h.get("role") == "assistant"]

        # 识别执行的操作
        exec_history = context.state.get("exec_history", [])
        routes_executed = {}
        for op in exec_history:
            route = op.get("route", "unknown")
            routes_executed[route] = routes_executed.get(route, 0) + 1

        # 构建摘要
        summary_lines = [
            "## 会话摘要\n",
            f"**会话开始**: {history[0].get('timestamp', 'N/A') if history else 'N/A'}",
            f"**对话轮次**: {len(history)} 轮",
            f"**用户输入**: {len(user_inputs)} 次",
            f"**助手响应**: {len(assistant_responses)} 次",
            "",
            "### 执行的操作\n",
        ]

        if routes_executed:
            for route, count in routes_executed.items():
                summary_lines.append(f"- `{route}`: {count} 次")
        else:
            summary_lines.append("暂无执行操作")

        summary_lines.append("")
        summary_lines.append("### 最近对话\n")

        # 显示最近 3 轮对话
        recent_pairs = list(zip(history[-6:-1:2], history[-5::2]))[:3]
        for i, (user_msg, asst_msg) in enumerate(recent_pairs, 1):
            user_content = str(user_msg.get("content", ""))[:100]
            asst_content = str(asst_msg.get("content", ""))[:100]
            summary_lines.append(f"**{i}. 用户**: {user_content}...")
            summary_lines.append(f"**助手**: {asst_content}...")
            summary_lines.append("")

        return CommandResult.success(
            data={
                "summary": "\n".join(summary_lines),
                "total_turns": len(history),
                "routes_executed": routes_executed
            },
            message="\n".join(summary_lines)
        )


class ClearCommand(BaseCommand):
    """清除当前会话"""

    metadata = {
        "name": "clear",
        "description": "清除当前会话的所有历史记录",
        "usage": "/clear [confirm]",
        "examples": [
            "/clear",
            "/clear yes",
        ],
        "aliases": ["/reset", "/clean"]
    }

    def _initialize(self) -> None:
        """初始化命令"""
        self.command_id = "clear"
        self.command_name = "clear"
        self.command_description = self.metadata["description"]
        self.command_usage = self.metadata["usage"]
        self.command_examples = self.metadata["examples"]
        self.command_aliases = self.metadata["aliases"]

    def execute(self, context: CommandContext) -> CommandResult:
        """执行清除命令"""
        # 检查是否确认
        confirm = context.args and len(context.args) > 0 and context.args[0].lower() in ["yes", "y", "confirm"]

        if not confirm:
            return CommandResult.success(
                data={"requires_confirmation": True},
                message="⚠️ 确定要清除当前会话吗？所有历史记录将被删除。\n\n使用 `/clear yes` 确认清除。"
            )

        # 清除会话历史
        # 注意：实际的清除逻辑需要在 Brain 层面实现
        return CommandResult.success(
            data={"cleared": True},
            message="✅ 会话已清除（需要 Brain 支持实际清除操作）"
        )


class ResumeCommand(BaseCommand):
    """恢复之前的会话"""

    metadata = {
        "name": "resume",
        "description": "恢复之前中断的会话",
        "usage": "/resume [session_id]",
        "examples": [
            "/resume",  # 恢复最近的会话
            "/resume abc-123",  # 恢复指定会话
        ],
        "aliases": ["/continue", "/restore"]
    }

    def _initialize(self) -> None:
        """初始化命令"""
        self.command_id = "resume"
        self.command_name = "resume"
        self.command_description = self.metadata["description"]
        self.command_usage = self.metadata["usage"]
        self.command_examples = self.metadata["examples"]
        self.command_aliases = self.metadata["aliases"]

    def execute(self, context: CommandContext) -> CommandResult:
        """执行恢复命令"""
        session_id = None
        if context.args and len(context.args) > 0:
            session_id = context.args[0]

        # 获取保存的会话列表
        sessions_dir = Path("storage/sessions")
        if not sessions_dir.exists():
            return CommandResult.error("没有找到保存的会话")

        # 读取会话列表
        session_files = list(sessions_dir.glob("*.json"))
        if not session_files:
            return CommandResult.success(message="没有找到可恢复的会话")

        if session_id:
            # 恢复指定会话
            target_file = sessions_dir / f"{session_id}.json"
            if not target_file.exists():
                return CommandResult.error(f"会话 {session_id} 不存在")

            with open(target_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            return CommandResult.success(
                data={"session": session_data, "restored": True},
                message=f"✅ 已恢复会话 {session_id}\n\n会话包含 {len(session_data.get('history', []))} 条记录"
            )
        else:
            # 显示最近的会话列表
            session_info = []
            for sf in sorted(session_files, key=lambda x: x.stat().st_mtime, reverse=True)[:10]:
                try:
                    with open(sf, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    session_id = sf.stem
                    created = data.get("created_at", "N/A")
                    history_count = len(data.get("history", []))
                    session_info.append(f"- `{session_id}`: {history_count} 条记录 (创建时间：{created})")
                except Exception:
                    continue

            if not session_info:
                return CommandResult.error("无法读取会话文件")

            return CommandResult.success(
                data={"sessions": session_info},
                message="## 可恢复的会话\n\n" + "\n".join(session_info) + "\n\n使用 `/resume <session_id>` 恢复指定会话"
            )


# 导出所有对话管理命令
DIALOG_COMMANDS = [
    HistoryCommand,
    UndoCommand,
    SummaryCommand,
    ClearCommand,
    ResumeCommand,
]


class ContextCommand(BaseCommand):
    """显示当前上下文信息"""

    command_id = "context"
    command_name = "context"
    command_description = "Show current context information"
    command_usage = "context"
    command_aliases = ["/context", "上下文"]
    command_examples = ["/context - Show current context"]

    def _initialize(self) -> None:
        self.command_id = "context"
        self.command_name = "context"
        self.command_description = "Show current context information"
        self.command_usage = "context"
        self.command_aliases = ["/context", "上下文"]
        self.command_examples = ["/context - Show current context"]

    def execute(self, context: CommandContext) -> CommandResult:
        """执行上下文命令"""
        context_info = {
            "session_id": context.state.get("session_id", "unknown"),
            "agent_id": self.agent_id,
            "current_task": context.state.get("current_task"),
            "working_directory": context.state.get("working_directory"),
            "history_length": len(context.state.get("history", [])),
        }
        return CommandResult.success(
            data=context_info,
            message="## 当前上下文\n\n" + "\n".join(f"- **{k}**: {v}" for k, v in context_info.items())
        )


class TokenCommand(BaseCommand):
    """显示 Token 使用统计"""

    command_id = "token"
    command_name = "token"
    command_description = "Show token usage statistics"
    command_usage = "token"
    command_aliases = ["/token", "token 统计"]
    command_examples = ["/token - Show token usage"]

    def _initialize(self) -> None:
        self.command_id = "token"
        self.command_name = "token"
        self.command_description = "Show token usage statistics"
        self.command_usage = "token"
        self.command_aliases = ["/token", "token 统计"]
        self.command_examples = ["/token - Show token usage"]

    def execute(self, context: CommandContext) -> CommandResult:
        """执行 Token 命令"""
        try:
            from mul_agent.brain.token_usage import TokenUsageCenter
            token_center = TokenUsageCenter()
            stats = token_center.get_agent_stats(self.agent_id)
        except Exception:
            stats = {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0, "total_cost": 0.0}

        return CommandResult.success(
            data={"agent_id": self.agent_id, "statistics": stats},
            message=f"## Token 使用统计\n\n- Total: {stats.get('total_tokens', 0)}\n- Input: {stats.get('input_tokens', 0)}\n- Output: {stats.get('output_tokens', 0)}"
        )


class DelegateCommand(BaseCommand):
    """委派任务给团队 - Commander 模式"""

    command_id = "delegate"
    command_name = "delegate"
    command_description = "委派任务给团队成员（alice/bob/wangyue）"
    command_usage = "/delegate <任务描述>"
    command_aliases = ["/team", "/assign"]
    command_examples = [
        "/delegate 实现用户登录功能",
        "/team 设计一个微服务架构",
        "/assign alice 修复这个 bug",
    ]

    def _initialize(self) -> None:
        self.command_id = "delegate"
        self.command_name = "delegate"
        self.command_description = "委派任务给团队成员（alice/bob/wangyue）"
        self.command_usage = self.command_usage
        self.command_aliases = self.command_aliases
        self.command_examples = self.command_examples

    def execute(self, context: CommandContext) -> CommandResult:
        """执行委派命令"""
        if not context.args:
            return CommandResult.error("请提供任务描述\n\n用法：/delegate <任务描述>")

        # 合并所有参数作为任务描述
        task_description = " ".join(context.args)

        # 获取 Brain 实例并执行 Commander 模式
        try:
            # 注意：这里需要通过 context 获取 Brain 实例
            # 由于当前设计限制，返回提示信息
            return CommandResult.success(
                data={"task": task_description, "requires_brain": True},
                message=f"## 任务委派\n\n**任务**: {task_description}\n\n⚠️ 此命令需要 Brain 支持，将自动分析并委派给合适的团队成员。"
            )
        except Exception as e:
            return CommandResult.error(f"委派失败：{str(e)}")


# 导出所有对话管理命令
DIALOG_COMMANDS = [
    HistoryCommand,
    UndoCommand,
    SummaryCommand,
    ClearCommand,
    ResumeCommand,
    DelegateCommand,
]
