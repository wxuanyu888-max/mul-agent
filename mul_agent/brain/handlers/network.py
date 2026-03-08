"""Network Handlers - Agent 网络相关处理器"""
from typing import Any, Dict

from .base import BaseHandler


class NetworkDelegateHandler(BaseHandler):
    """任务委派处理器"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}
        to_agent = params.get("to_agent")
        task = params.get("task", {})
        if not to_agent:
            return {"status": "error", "error_code": 1004, "message": "Missing: to_agent"}
        return {"status": "success", "action": "delegate_task", "result": {"to_agent": to_agent, "task": task}}

    def _get_brain(self):
        return None


class NetworkSendHandler(BaseHandler):
    """消息发送处理器"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}
        to_agent = params.get("to_agent")
        content = params.get("content", {})
        if not to_agent:
            return {"status": "error", "error_code": 1004, "message": "Missing: to_agent"}
        return {"status": "success", "action": "send_message", "result": {"to_agent": to_agent, "content": content}}

    def _get_brain(self):
        return None


class NetworkCheckHandler(BaseHandler):
    """消息检查处理器"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}
        limit = params.get("limit", 10)
        msg_type = params.get("msg_type")
        return {"status": "success", "action": "check_messages", "result": {"limit": limit, "msg_type": msg_type}}

    def _get_brain(self):
        return None


class NetworkBroadcastHandler(BaseHandler):
    """广播消息处理器"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}
        content = params.get("content", {})
        exclude_agents = params.get("exclude_agents")
        return {"status": "success", "action": "broadcast_message", "result": {"content": content, "exclude_agents": exclude_agents}}

    def _get_brain(self):
        return None


class NetworkHandoverHandler(BaseHandler):
    """交接处理器"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}
        to_agent = params.get("to_agent")
        handover_data = params.get("handover_data", {})
        if not to_agent:
            return {"status": "error", "error_code": 1004, "message": "Missing: to_agent"}
        return {"status": "success", "action": "create_handover", "result": {"to_agent": to_agent, "handover_data": handover_data}}

    def _get_brain(self):
        return None
