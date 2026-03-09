"""Execution Visualizer - 执行过程可视化

生成执行轨迹图、决策树、工具调用链的可视化
"""

import json
import time
from typing import Any, Dict, List, Optional
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class ExecutionEvent:
    """执行事件"""
    timestamp: float
    event_type: str  # 'route_start', 'route_complete', 'tool_call', 'decision', 'error'
    route: Optional[str] = None
    params: Optional[Dict] = None
    result: Optional[Dict] = None
    error: Optional[str] = None
    duration: Optional[float] = None
    metadata: Dict = field(default_factory=dict)


class ExecutionTracer:
    """执行轨迹记录器"""

    def __init__(self):
        self.events: List[ExecutionEvent] = []
        self.sessions: Dict[str, List[ExecutionEvent]] = {}
        self.current_session: Optional[str] = None

    def start_session(self, session_id: str = None) -> str:
        """开始新会话"""
        if session_id is None:
            session_id = str(int(time.time()))
        self.current_session = session_id
        self.sessions[session_id] = []
        return session_id

    def record(self, event_type: str, **kwargs) -> ExecutionEvent:
        """记录事件"""
        event = ExecutionEvent(
            timestamp=time.time(),
            event_type=event_type,
            **kwargs
        )
        self.events.append(event)
        if self.current_session and self.current_session in self.sessions:
            self.sessions[self.current_session].append(event)
        return event

    def get_session_events(self, session_id: str) -> List[ExecutionEvent]:
        """获取会话事件"""
        return self.sessions.get(session_id, [])

    def get_timeline(self, session_id: str = None) -> List[Dict]:
        """获取时间线"""
        events = self.get_session_events(session_id) if session_id else self.events
        return [
            {
                "timestamp": e.timestamp,
                "type": e.event_type,
                "route": e.route,
                "duration": e.duration,
                "error": e.error
            }
            for e in events
        ]


class ExecutionVisualizer:
    """执行可视化器"""

    def __init__(self, tracer: ExecutionTracer = None):
        self.tracer = tracer or ExecutionTracer()

    def visualize_timeline(self, session_id: str = None) -> str:
        """可视化时间线"""
        events = self.tracer.get_session_events(session_id) if session_id else self.tracer.events

        if not events:
            return "No events recorded"

        lines = []
        lines.append("⏱️  执行时间线")
        lines.append("=" * 60)

        start_time = events[0].timestamp

        for i, event in enumerate(events):
            relative_time = event.timestamp - start_time

            icon = {
                'route_start': '🚀',
                'route_complete': '✅',
                'tool_call': '🔧',
                'decision': '🤔',
                'error': '❌',
            }.get(event.event_type, '•')

            status = ""
            if event.error:
                status = f" ❌ {event.error[:50]}"
            elif event.duration:
                status = f" ({event.duration:.2f}s)"

            lines.append(f"{icon} [{relative_time:6.2f}s] {event.event_type}")
            if event.route:
                lines.append(f"      └─→ {event.route}")
            if status:
                lines.append(f"      └─→{status}")

        return "\n".join(lines)

    def visualize_flow(self, session_id: str = None) -> str:
        """可视化执行流程图"""
        events = self.tracer.get_session_events(session_id) if session_id else self.tracer.events

        if not events:
            return "No events recorded"

        lines = []
        lines.append("📊 执行流程")
        lines.append("=" * 60)

        route_stack = []

        for event in events:
            if event.event_type == 'route_start':
                route_stack.append(event.route)
                indent = "  " * len(route_stack)
                lines.append(f"{indent}┌─→ {event.route}")
            elif event.event_type == 'route_complete':
                if route_stack:
                    route_stack.pop()
                indent = "  " * len(route_stack)
                lines.append(f"{indent}└─ (complete)")

        return "\n".join(lines)

    def visualize_tree(self, session_id: str = None) -> str:
        """可视化决策树"""
        events = self.tracer.get_session_events(session_id) if session_id else self.tracer.events

        if not events:
            return "No events recorded"

        lines = []
        lines.append("🌳 决策树")
        lines.append("=" * 60)

        # 构建树结构
        tree = {"root": {"children": [], "event": None}}
        stack = [("root", tree["root"])]

        for event in events:
            if event.event_type == 'route_start':
                node = {"event": event, "children": []}
                stack[-1][1]["children"].append(node)
                stack.append((event.route or "unknown", node))
            elif event.event_type == 'route_complete':
                if len(stack) > 1:
                    stack.pop()

        def print_tree(node, indent=0, prefix=""):
            result = []
            if node["event"]:
                event = node["event"]
                icon = "❌" if event.error else "✅" if event.event_type == 'route_complete' else "🚀"
                result.append(f"{prefix}{icon} {event.route or event.event_type}")
                if event.duration:
                    result[-1] += f" ({event.duration:.2f}s)"

            for i, child in enumerate(node["children"]):
                is_last = i == len(node["children"]) - 1
                child_prefix = prefix + ("    " if is_last else "│   ")
                result.extend(print_tree(child, indent + 1, prefix + ("└── " if is_last else "├── ")))

            return result

        lines.extend(print_tree(tree["root"]))
        return "\n".join(lines)

    def generate_summary(self, session_id: str = None) -> Dict[str, Any]:
        """生成执行摘要"""
        events = self.tracer.get_session_events(session_id) if session_id else self.tracer.events

        if not events:
            return {"status": "error", "message": "No events recorded"}

        start_time = events[0].timestamp
        end_time = events[-1].timestamp

        total_duration = end_time - start_time
        route_events = [e for e in events if e.event_type in ('route_start', 'route_complete')]
        error_events = [e for e in events if e.error]

        return {
            "session_id": session_id or "default",
            "total_events": len(events),
            "total_duration": total_duration,
            "route_count": len(route_events) // 2,  # start + complete pairs
            "error_count": len(error_events),
            "success_rate": 1 - (len(error_events) / max(len(route_events) // 2, 1)),
            "average_duration": sum(e.duration or 0 for e in route_events) / max(len(route_events), 1)
        }

    def export_html(self, session_id: str = None, output_path: str = None) -> str:
        """导出为 HTML 报告"""
        events = self.tracer.get_session_events(session_id) if session_id else self.tracer.events
        summary = self.generate_summary(session_id)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Execution Report - {summary['session_id']}</title>
    <style>
        body {{ font-family: monospace; background: #1e1e1e; color: #d4d4d4; padding: 20px; }}
        .header {{ border-bottom: 1px solid #444; padding-bottom: 10px; margin-bottom: 20px; }}
        .stat {{ display: inline-block; margin-right: 20px; }}
        .stat-value {{ color: #4ec9b0; font-size: 1.2em; }}
        .event {{ padding: 5px 10px; margin: 5px 0; border-radius: 4px; }}
        .event-start {{ background: #3c3c3c; }}
        .event-complete {{ background: #2d4a2d; }}
        .event-error {{ background: #4a2d2d; }}
        .timestamp {{ color: #808080; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>📊 Execution Report</h2>
        <div class="stats">
            <div class="stat">Events: <span class="stat-value">{summary['total_events']}</span></div>
            <div class="stat">Duration: <span class="stat-value">{summary['total_duration']:.2f}s</span></div>
            <div class="stat">Routes: <span class="stat-value">{summary['route_count']}</span></div>
            <div class="stat">Errors: <span class="stat-value">{summary['error_count']}</span></div>
            <div class="stat">Success Rate: <span class="stat-value">{summary['success_rate']*100:.1f}%</span></div>
        </div>
    </div>
    <div class="events">
"""

        for event in events:
            event_class = "event-error" if event.error else "event-complete" if event.event_type == "route_complete" else "event-start"
            html += f"""
        <div class="event {event_class}">
            <span class="timestamp">[{event.timestamp - events[0].timestamp:6.2f}s]</span>
            {event.event_type}
            {f"→ {event.route}" if event.route else ""}
            {f"({event.duration:.2f}s)" if event.duration else ""}
            {f"❌ {event.error}" if event.error else ""}
        </div>
"""

        html += """
    </div>
</body>
</html>
"""

        if output_path:
            Path(output_path).write_text(html, encoding='utf-8')
            return f"Exported to {output_path}"

        return html


# 全局实例
tracer = ExecutionTracer()
visualizer = ExecutionVisualizer(tracer)
