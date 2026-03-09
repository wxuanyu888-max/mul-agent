"""Visualization Handler - 可视化处理器"""

from typing import Any, Dict

from .base import BaseHandler
from mul_agent.brain.visualizer import tracer, visualizer


class VisualizationHandler(BaseHandler):
    """可视化处理器

    使用场景:
    - 查看执行时间线
    - 生成执行流程图
    - 导出执行报告
    """

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}

        action = params.get("action", "timeline")
        session_id = params.get("session_id")

        if action == "start_session":
            session_id = tracer.start_session(params.get("session_id"))
            return {"status": "success", "session_id": session_id}

        elif action == "record":
            event_type = params.get("event_type", "custom")
            params_copy = {k: v for k, v in params.items() if k not in ("action", "event_type")}
            tracer.record(event_type, **params_copy)
            return {"status": "success", "message": "Event recorded"}

        elif action == "timeline":
            ascii_art = visualizer.visualize_timeline(session_id)
            return {"status": "success", "visualization": ascii_art}

        elif action == "flow":
            ascii_art = visualizer.visualize_flow(session_id)
            return {"status": "success", "visualization": ascii_art}

        elif action == "tree":
            ascii_art = visualizer.visualize_tree(session_id)
            return {"status": "success", "visualization": ascii_art}

        elif action == "summary":
            summary = visualizer.generate_summary(session_id)
            return {"status": "success", **summary}

        elif action == "export_html":
            output_path = params.get("output")
            result = visualizer.export_html(session_id, output_path)
            return {"status": "success", "result": result}

        else:
            return {"status": "error", "error_code": 1005, "message": f"Unknown action: {action}"}
