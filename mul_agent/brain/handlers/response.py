"""Response Handler - 直接响应处理器"""
from typing import Any, Dict

from .base import BaseHandler


class ResponseHandler(BaseHandler):
    """直接响应处理器 - 用于 LLM 直接返回响应的情况"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """直接返回响应"""
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}
        message = params.get("message", "")
        return {"message": message, "type": "direct_response"}
