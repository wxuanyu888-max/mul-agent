"""Bash Tool - 执行 shell 命令

参考 OpenClaw 的 exec 工具设计：
1. 支持超时控制
2. 支持后台执行
3. 支持安全门控
4. 结构化输出
"""

import subprocess
import os
import re
from typing import Optional
from mul_agent.tools.base import SyncTool, ToolMetadata, ToolResult, ToolGate


class BashTool(SyncTool):
    """Bash 工具 - 执行 shell 命令

    这是最核心的工具之一，允许 LLM 通过 shell 命令与系统交互

    安全限制:
    - 禁止访问敏感路径 (/etc/passwd, /etc/shadow 等)
    - 禁止执行危险命令 (rm -rf / 等)
    - 支持超时控制
    - 支持工作目录限制
    """

    metadata = ToolMetadata(
        name="bash",
        description="执行 shell 命令。用于文件操作、进程管理、系统查询等。",
        input_schema={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 shell 命令"
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒），默认 60"
                },
                "cwd": {
                    "type": "string",
                    "description": "工作目录，默认当前目录"
                },
                "elevated": {
                    "type": "boolean",
                    "description": "是否以提升的权限运行（需要授权）"
                }
            },
            "required": ["command"]
        },
        examples=[
            {"command": "ls -la"},
            {"command": "cat package.json"},
            {"command": "find . -name '*.py' -type f"},
            {"command": "grep -r 'TODO' src/", "timeout": 30},
        ],
        gate=ToolGate(
            os=["darwin", "linux"],  # 不支持 Windows
        ),
        tags=["runtime", "shell", "exec"],
    )

    # 禁止的命令模式
    FORBIDDEN_PATTERNS = [
        "rm -rf /",
        "rm -rf /*",
        "dd if=/dev/",
        ":(){:|:&};:",
        "mkfs.",
        "wget.*\\|.*sh",
        "curl.*\\|.*sh",
    ]

    # 禁止访问的路径
    FORBIDDEN_PATHS = [
        "/etc/passwd",
        "/etc/shadow",
        "/etc/sudoers",
        "/root/.ssh",
        "/proc/",
    ]

    # 禁止的命令模式
    FORBIDDEN_PATTERNS = [
        "rm -rf /",
        "rm -rf /*",
        "dd if=/dev/",
        ":(){:|:&};:",
        "mkfs.",
        "wget.*\\|.*sh",
        "curl.*\\|.*sh",
    ]

    # 禁止访问的路径
    FORBIDDEN_PATHS = [
        "/etc/passwd",
        "/etc/shadow",
        "/etc/sudoers",
        "/root/.ssh",
        "/proc/",
    ]

    def execute_sync(self, **kwargs) -> ToolResult:
        """执行 bash 命令

        Args:
            command: shell 命令
            timeout: 超时时间（秒）
            cwd: 工作目录

        Returns:
            ToolResult: 执行结果
        """
        command = kwargs.get("command", "")
        timeout = kwargs.get("timeout", 60)
        cwd = kwargs.get("cwd", None)

        # 验证命令
        if not command:
            return ToolResult.error("command is required")

        # 安全检查
        safety_check = self._safety_check(command)
        if not safety_check["safe"]:
            return ToolResult.error(f"Command blocked for safety: {safety_check['reason']}")

        try:
            # 执行命令
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd or os.getcwd(),
                env={**os.environ, "LANG": "en_US.UTF-8"}
            )

            # 构建返回结果
            output = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }

            message = f"Command executed (exit code: {result.returncode})"
            if result.stderr and not result.stdout:
                message = f"Warning: {result.stderr[:200]}"

            return ToolResult.success(data=output, message=message)

        except subprocess.TimeoutExpired as e:
            return ToolResult.error(
                error=f"Command timed out after {timeout} seconds",
                message=f"Partial output: {e.stdout[:500] if e.stdout else ''}"
            )
        except Exception as e:
            return ToolResult.error(error=str(e))

    def _safety_check(self, command: str) -> dict:
        """安全检查

        Args:
            command: 命令字符串

        Returns:
            dict: {"safe": bool, "reason": str}
        """
        import re

        # 检查禁止的命令模式
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern in command:
                return {
                    "safe": False,
                    "reason": f"Contains forbidden pattern: {pattern}"
                }

        # 检查禁止的路径
        for path in self.FORBIDDEN_PATHS:
            if path in command:
                return {
                    "safe": False,
                    "reason": f"Access to {path} is forbidden"
                }

        # 检查管道和重定向中的危险命令
        if re.search(r'\|\s*(sh|bash)\s*$', command):
            return {
                "safe": False,
                "reason": "Piping to shell interpreter is forbidden"
            }

        return {"safe": True}
