"""Built-in Hooks - 内置钩子"""

from typing import Any, Dict, Optional
from mul_agent.hooks.base import (
    BaseHook,
    HookContext,
    HookEvent,
    HookPriority,
    PreToolUseHook,
    PostToolUseHook,
    SessionStartHook,
    SessionEndHook,
)


class LogInvocationHook(PostToolUseHook):
    """日志记录钩子 - 记录工具调用"""

    hook_id = "log_invocation"
    hook_name = "Log Invocation"
    hook_version = "1.0.0"
    hook_description = "Log tool invocations for debugging and auditing"
    events = [HookEvent.POST_TOOL_USE]
    priority = HookPriority.LOW

    def _initialize(self) -> None:
        """初始化"""
        self.log_count = 0

    def on_post_tool_use(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """记录工具调用"""
        tool_name = context.get("tool_name", "unknown")
        result = context.get("result", {})

        self.log_count += 1

        # 记录日志（可以输出到文件或其他地方）
        status = result.get("status", "unknown") if isinstance(result, dict) else "success"
        print(f"[LOG] Tool: {tool_name}, Status: {status}, Count: {self.log_count}")

        return None


class FormatOutputHook(PostToolUseHook):
    """格式化输出钩子 - 格式化结果输出"""

    hook_id = "format_output"
    hook_name = "Format Output"
    hook_version = "1.0.0"
    hook_description = "Format tool output for better readability"
    events = [HookEvent.POST_TOOL_USE]
    priority = HookPriority.NORMAL

    def _initialize(self) -> None:
        """初始化"""
        self.format_config = {
            "indent": 2,
            "ensure_ascii": False,
            "max_string_length": 1000
        }

    def on_post_tool_use(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """格式化输出"""
        result = context.get("result")

        if isinstance(result, dict):
            # 可以在这里添加格式化逻辑
            pass
        elif isinstance(result, str):
            # 截断过长的字符串
            if len(result) > self.format_config["max_string_length"]:
                truncated = result[:self.format_config["max_string_length"]] + "..."
                context.set("result", truncated)

        return None


class SafetyCheckHook(PreToolUseHook):
    """安全检查钩子 - 阻止危险操作"""

    hook_id = "safety_check"
    hook_name = "Safety Check"
    hook_version = "1.0.0"
    hook_description = "Block dangerous commands and operations"
    events = [HookEvent.PRE_TOOL_USE]
    priority = HookPriority.HIGH

    def _initialize(self) -> None:
        """初始化"""
        self.forbidden_commands = [
            "rm -rf /",
            "rm -rf /*",
            "sudo rm -rf",
            "dd if=/dev/zero",
            ":(){:|:&};:",
            "mkfs",
            "fdisk",
        ]

        self.forbidden_patterns = [
            r"rm\s+-rf\s+/",
            r"sudo\s+rm\s+-rf",
            r"dd\s+if=/dev/zero",
        ]

    def on_pre_tool_use(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """安全检查"""
        tool_name = context.get("tool_name", "")
        params = context.get("params", {})

        if tool_name == "bash":
            command = params.get("command", "")
            return self._check_command(command)

        return None

    def _check_command(self, command: str) -> Optional[Dict[str, Any]]:
        """检查命令是否危险"""
        import re

        # 检查禁止的命令
        for forbidden in self.forbidden_commands:
            if forbidden in command:
                return {
                    "blocked": True,
                    "error": f"Command blocked for safety: {command}"
                }

        # 检查禁止的模式
        for pattern in self.forbidden_patterns:
            if re.search(pattern, command):
                return {
                    "blocked": True,
                    "error": f"Command blocked for safety (pattern match): {command}"
                }

        return None


class SessionStateHook(SessionStartHook, SessionEndHook):
    """会话状态钩子 - 管理会话状态"""

    hook_id = "session_state"
    hook_name = "Session State"
    hook_version = "1.0.0"
    hook_description = "Manage session state and cleanup"
    events = [HookEvent.SESSION_START, HookEvent.SESSION_END]

    def _initialize(self) -> None:
        """初始化"""
        self.session_data = {}

    def on_session_start(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """会话开始"""
        self.session_data = {
            "started_at": context.timestamp,
            "tool_calls": 0,
            "errors": 0
        }
        print(f"[SESSION] Started at {context.timestamp}")
        return None

    def on_session_end(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """会话结束"""
        if self.session_data:
            duration = context.timestamp - self.session_data.get("started_at", context.timestamp)
            print(f"[SESSION] Ended. Duration: {duration:.2f}s")
            print(f"[SESSION] Tool calls: {self.session_data.get('tool_calls', 0)}")
            print(f"[SESSION] Errors: {self.session_data.get('errors', 0)}")
        return None


class RateLimitHook(PreToolUseHook):
    """限流钩子 - 限制工具调用频率"""

    hook_id = "rate_limit"
    hook_name = "Rate Limit"
    hook_version = "1.0.0"
    hook_description = "Rate limit tool invocations"
    events = [HookEvent.PRE_TOOL_USE]
    priority = HookPriority.HIGH

    def _initialize(self) -> None:
        """初始化"""
        import time
        self._calls = {}  # tool_name -> [timestamps]
        self._limits = {
            "*": 100,  # 默认每分钟 100 次
            "bash": 60,
            "chat": 30,
        }
        self._window = 60  # 1 分钟窗口

    def on_pre_tool_use(self, context: HookContext) -> Optional[Dict[str, Any]]:
        """限流检查"""
        import time

        tool_name = context.get("tool_name", "unknown")
        current_time = time.time()

        # 获取限制
        limit = self._limits.get(tool_name, self._limits.get("*"))

        # 清理过期记录
        if tool_name in self._calls:
            self._calls[tool_name] = [
                t for t in self._calls[tool_name]
                if current_time - t < self._window
            ]
        else:
            self._calls[tool_name] = []

        # 检查是否超限
        if len(self._calls[tool_name]) >= limit:
            return {
                "blocked": True,
                "error": f"Rate limit exceeded for {tool_name}"
            }

        # 记录调用
        self._calls[tool_name].append(current_time)

        return None
