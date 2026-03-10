"""Built-in Hooks - 内置钩子"""

from .base import BaseHook


class LogHook(BaseHook):
    """日志钩子 - 记录工具调用和会话事件"""

    hook_id = "log_hook"
    hook_name = "Log Hook"
    hook_description = "记录工具调用和会话事件的日志钩子"
    hook_version = "1.0.0"
    hook_tags = ["logging", "debug"]
    priority = 1

    def pre_tool_use(self, route: str, params: dict) -> dict:
        """记录工具调用前的参数"""
        print(f"[LOG HOOK] Pre tool use: {route}, params: {params}")
        return params

    def post_tool_use(self, route: str, params: dict, result: dict) -> dict:
        """记录工具调用后的结果"""
        print(f"[LOG HOOK] Post tool use: {route}, result: {result}")
        return result

    def session_start(self, context: dict) -> dict:
        """记录会话开始"""
        print(f"[LOG HOOK] Session started: {self.agent_id}")
        return context

    def session_end(self, context: dict) -> dict:
        """记录会话结束"""
        print(f"[LOG HOOK] Session ended: {self.agent_id}")
        return context


class ValidationHook(BaseHook):
    """验证钩子 - 验证工具和命令参数"""

    hook_id = "validation_hook"
    hook_name = "Validation Hook"
    hook_description = "验证工具和命令参数的钩子"
    hook_version = "1.0.0"
    hook_tags = ["validation", "security"]
    priority = 8

    def pre_tool_use(self, route: str, params: dict) -> dict:
        """验证工具参数"""
        # 这里可以添加参数验证逻辑
        if not route:
            raise ValueError("Tool route cannot be empty")
        return params

    def pre_command(self, command: str, args: str) -> tuple:
        """验证命令参数"""
        if not command:
            raise ValueError("Command cannot be empty")
        return command, args


__all__ = ["LogHook", "ValidationHook"]
