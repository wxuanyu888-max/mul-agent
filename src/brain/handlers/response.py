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

        # Fallback: 如果 message 为空，返回默认响应
        if not message or not message.strip():
            return {
                "message": "我已收到您的请求，但无法生成具体响应。请提供更多详细信息或尝试其他请求方式。",
                "type": "direct_response"
            }

        return {"message": message, "type": "direct_response"}
