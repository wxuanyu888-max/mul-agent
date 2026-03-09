"""Bash Handler - Bash 命令执行处理器"""
from typing import Any, Dict

from .base import BaseHandler


class BashHandler(BaseHandler):
    """Bash 命令执行处理器"""

    DANGEROUS_PATTERNS = ["rm -rf", "sudo", "dd", "mkfs", "chmod 777", "> /dev/", ">> /etc/"]

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}
        command = params.get("command", "")
        timeout = params.get("timeout", 30)
        cwd = params.get("cwd")

        if not command or not command.strip():
            return {"status": "error", "error_code": 1004, "message": "Missing: command"}

        command_lower = command.lower()
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern.lower() in command_lower:
                return {"status": "error", "error_code": 1003, "message": f"Command contains forbidden pattern: {pattern}"}

        from mul_agent.tools.bash_executor import BashExecutor
        executor = BashExecutor(timeout=timeout, cwd=cwd)

        # 使用传入的 agent_id 或默认的 wangyue
        agent_id = self.get_agent_id(params)
        agent_config = self.config_manager.load(agent_id, "user")

        # 修复：tools.bash 可能是布尔值或字典
        bash_config = agent_config.get("tools", {}).get("bash")
        if isinstance(bash_config, dict):
            allowed = bash_config.get("allowed_commands", ["*"])
            forbidden = bash_config.get("forbidden_commands", [])
        else:
            # 如果是 True/布尔值，使用默认配置
            allowed = ["*"]
            forbidden = self.DANGEROUS_PATTERNS

        if not executor.is_safe(command, allowed, forbidden):
            return {"status": "error", "error_code": 1003, "message": f"Command not allowed: {command}"}

        result = executor.execute(command)
        exit_code = result.get("exit_code", -1)

        if exit_code != 0:
            return {"status": "error", "error_code": 1006, "message": f"Exit code {exit_code}", "exit_code": exit_code, "stdout": result.get("stdout", ""), "stderr": result.get("stderr", "")}

        return {"status": "success", "stdout": result.get("stdout", ""), "stderr": result.get("stderr", ""), "exit_code": exit_code}
