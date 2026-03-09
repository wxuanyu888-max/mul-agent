"""Code Understanding Handler - 代码理解处理器"""

from typing import Any, Dict
from pathlib import Path

from .base import BaseHandler
from mul_agent.brain.code_understanding import code_understanding


class CodeUnderstandingHandler(BaseHandler):
    """代码理解处理器

    使用场景:
    - 分析代码结构
    - 查找符号定义和使用
    - 生成依赖图
    - 代码语义理解
    """

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}

        action = params.get("action", "analyze")
        path = params.get("path", ".")

        # 安全性检查
        if not self._is_path_safe(path):
            return {"status": "error", "error_code": 1003, "message": f"Path not allowed: {path}"}

        path_obj = Path(path)
        if not path_obj.exists():
            return {"status": "error", "error_code": 1004, "message": f"Path not found: {path}"}

        if action == "analyze":
            return code_understanding.analyze(path)
        elif action == "dependencies":
            return code_understanding.get_dependencies(path)
        elif action == "find_symbol":
            symbol = params.get("symbol")
            if not symbol:
                return {"status": "error", "error_code": 1004, "message": "Missing: symbol"}
            return code_understanding.find_symbol(symbol, path)
        elif action == "find_usages":
            symbol = params.get("symbol")
            if not symbol:
                return {"status": "error", "error_code": 1004, "message": "Missing: symbol"}
            return code_understanding.find_usages(symbol, path)
        else:
            return {"status": "error", "error_code": 1005, "message": f"Unknown action: {action}"}

    def _is_path_safe(self, path: str) -> bool:
        """检查路径是否安全"""
        forbidden = ["/etc/", "/proc/", "/sys/", ".git/objects/"]
        for f in forbidden:
            if f in path:
                return False
        return True
