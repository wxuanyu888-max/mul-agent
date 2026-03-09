"""Bash Executor - Shell command execution"""

import subprocess
import time
import shlex
from typing import Any, Dict, List, Optional


class BashExecutor:
    """Bash命令执行器"""

    def __init__(self, timeout: int = 30, cwd: Optional[str] = None):
        self.timeout = timeout
        self.cwd = cwd

    def execute(self, command: str) -> Dict[str, Any]:
        """执行命令"""
        start_time = time.time()

        try:
            # Use shell=True for complex commands, but sanitize
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.cwd,
                text=True
            )

            try:
                stdout, stderr = process.communicate(timeout=self.timeout)
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                exit_code = -1
                stderr = f"Command timed out after {self.timeout} seconds"

            duration = time.time() - start_time

            return {
                "stdout": stdout,
                "stderr": stderr,
                "exit_code": exit_code,
                "duration": duration,
                "success": exit_code == 0
            }

        except Exception as e:
            duration = time.time() - start_time
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "duration": duration,
                "success": False
            }

    def is_safe(self, command: str, allowed: List[str], forbidden: List[str]) -> bool:
        """检查命令是否安全"""
        # Check forbidden patterns FIRST - always check this regardless of allowed
        command_lower = command.lower()
        for pattern in forbidden:
            if pattern.lower() in command_lower:
                return False

        # If wildcard is allowed, permit all (after forbidden check)
        if "*" in allowed:
            return True

        # Check if command starts with any allowed command
        command_parts = shlex.split(command) if not command.startswith("(") else [command]
        if command_parts:
            base_cmd = command_parts[0]
            # Also check for pipes and redirects
            for allow in allowed:
                if allow == "*":
                    return True
                if base_cmd == allow or command.startswith(allow):
                    return True

        # If specific commands allowed, only those are permitted
        if allowed and allowed != ["*"]:
            return False

        return True


class SafeBashExecutor(BashExecutor):
    """更安全的Bash执行器 - 默认禁止危险操作"""

    DEFAULT_FORBIDDEN = [
        "rm -rf",
        "sudo",
        "dd",
        "mkfs",
        "fdisk",
        "> /dev/sd",
        "chmod 777",
        "wget | sh",
        "curl | sh",
        "fork(",
        ":(){:|:&};:",  # Fork bomb
        "chown -R",
        "chmod -R",
    ]

    def is_safe(self, command: str, allowed: Optional[List[str]] = None,
                 forbidden: Optional[List[str]] = None) -> bool:
        """检查命令是否安全"""
        if allowed is None:
            allowed = ["*"]
        if forbidden is None:
            forbidden = self.DEFAULT_FORBIDDEN

        return super().is_safe(command, allowed, forbidden)
