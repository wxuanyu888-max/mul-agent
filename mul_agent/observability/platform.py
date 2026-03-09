"""Agent Observability Platform - Agent 可观测性平台

参考 Claude Code 的设计：
1. 结构化日志记录
2. 性能指标收集
3. 分布式追踪
4. 调试和回放工具
"""

import json
import time
import uuid
import threading
import queue
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import hashlib


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SpanType(Enum):
    """追踪 Span 类型"""
    LLM_CALL = "llm_call"
    TOOL_EXECUTION = "tool_execution"
    ROUTE_DISPATCH = "route_dispatch"
    MEMORY_OPERATION = "memory_operation"
    AGENT_COMMUNICATION = "agent_communication"
    SKILL_EXECUTION = "skill_execution"
    CUSTOM = "custom"


@dataclass
class LogEntry:
    """日志条目"""
    id: str
    timestamp: float
    level: LogLevel
    agent_id: str
    session_id: str
    message: str
    context: Dict[str, Any] = field(default_factory=dict)
    trace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "level": self.level.value,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "message": self.message,
            "context": self.context,
            "trace_id": self.trace_id,
            "datetime": datetime.fromtimestamp(self.timestamp).isoformat()
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass
class Span:
    """追踪 Span"""
    trace_id: str
    span_id: str
    name: str
    span_type: SpanType
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "running"  # running, success, error
    agent_id: str = ""
    session_id: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    parent_span_id: Optional[str] = None

    def finish(self, status: str = "success", error: str = None):
        """结束 Span"""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        self.status = status
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "name": self.name,
            "type": self.span_type.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "tags": self.tags,
            "metrics": self.metrics,
            "error": self.error,
            "parent_span_id": self.parent_span_id
        }


@dataclass
class MetricPoint:
    """指标数据点"""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)


class ObservabilityStorage:
    """可观测性存储"""

    def __init__(self, storage_dir: str = "storage/observability"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.logs_dir = self.storage_dir / "logs"
        self.traces_dir = self.storage_dir / "traces"
        self.metrics_dir = self.storage_dir / "metrics"

        for d in [self.logs_dir, self.traces_dir, self.metrics_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def write_log(self, entry: LogEntry):
        """写入日志"""
        date_str = datetime.fromtimestamp(entry.timestamp).strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{date_str}.jsonl"

        with open(log_file, "a", encoding="utf-8") as f:
            f.write(entry.to_json() + "\n")

    def write_trace(self, span: Span):
        """写入追踪"""
        trace_file = self.traces_dir / f"{span.trace_id}.json"

        # 读取现有追踪或创建新的
        trace_data = {"trace_id": span.trace_id, "spans": []}
        if trace_file.exists():
            with open(trace_file, "r", encoding="utf-8") as f:
                trace_data = json.load(f)

        trace_data["spans"].append(span.to_dict())

        with open(trace_file, "w", encoding="utf-8") as f:
            json.dump(trace_data, f, ensure_ascii=False, indent=2)

    def write_metric(self, metric: MetricPoint):
        """写入指标"""
        date_str = datetime.fromtimestamp(metric.timestamp).strftime("%Y-%m-%d")
        metric_file = self.metrics_dir / f"{metric.name}_{date_str}.jsonl"

        with open(metric_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "name": metric.name,
                "value": metric.value,
                "timestamp": metric.timestamp,
                "tags": metric.tags
            }, ensure_ascii=False) + "\n")

    def get_logs(self, agent_id: str = None, session_id: str = None,
                 level: LogLevel = None, limit: int = 100) -> List[LogEntry]:
        """获取日志"""
        logs = []

        for log_file in sorted(self.logs_dir.glob("*.jsonl"), reverse=True):
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if agent_id and data.get("agent_id") != agent_id:
                            continue
                        if session_id and data.get("session_id") != session_id:
                            continue
                        if level and data.get("level") != level.value:
                            continue

                        logs.append(LogEntry(
                            id=data.get("id"),
                            timestamp=data.get("timestamp"),
                            level=LogLevel(data.get("level")),
                            agent_id=data.get("agent_id"),
                            session_id=data.get("session_id"),
                            message=data.get("message"),
                            context=data.get("context", {}),
                            trace_id=data.get("trace_id")
                        ))

                        if len(logs) >= limit:
                            return logs
                    except Exception:
                        continue

        return logs

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """获取追踪"""
        trace_file = self.traces_dir / f"{trace_id}.json"
        if not trace_file.exists():
            return None

        with open(trace_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_metrics(self, metric_name: str, hours: int = 24) -> List[MetricPoint]:
        """获取指标"""
        metrics = []
        cutoff_time = time.time() - (hours * 3600)

        for metric_file in self.metrics_dir.glob(f"{metric_name}_*.jsonl"):
            with open(metric_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        if data.get("timestamp", 0) >= cutoff_time:
                            metrics.append(MetricPoint(
                                name=data.get("name"),
                                value=data.get("value"),
                                timestamp=data.get("timestamp"),
                                tags=data.get("tags", {})
                            ))
                    except Exception:
                        continue

        return sorted(metrics, key=lambda m: m.timestamp)


class AgentObservabilityPlatform:
    """Agent 可观测性平台"""

    def __init__(self, agent_id: str, session_id: str = None):
        self.agent_id = agent_id
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.storage = ObservabilityStorage()

        self._current_trace_id: Optional[str] = None
        self._active_spans: Dict[str, Span] = {}
        self._lock = threading.Lock()

        # 异步日志队列
        self._log_queue: queue.Queue = queue.Queue()
        self._log_thread = self._start_log_thread()

        # 指标收集
        self._metrics: Dict[str, List[float]] = {}

        # 回调
        self._on_error_callbacks: List[Callable] = []

    def _start_log_thread(self) -> threading.Thread:
        """启动日志处理线程"""
        def process_logs():
            while True:
                try:
                    entry = self._log_queue.get(timeout=1)
                    if entry is None:
                        break
                    self.storage.write_log(entry)
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"Log thread error: {e}")

        thread = threading.Thread(target=process_logs, daemon=True)
        thread.start()
        return thread

    def log(self, level: LogLevel, message: str, **context):
        """记录日志

        Args:
            level: 日志级别
            message: 日志消息
            **context: 上下文信息
        """
        entry = LogEntry(
            id=str(uuid.uuid4())[:12],
            timestamp=time.time(),
            level=level,
            agent_id=self.agent_id,
            session_id=self.session_id,
            message=message,
            context=context,
            trace_id=self._current_trace_id
        )

        self._log_queue.put(entry)

        # 错误日志触发回调
        if level in (LogLevel.ERROR, LogLevel.CRITICAL):
            for callback in self._on_error_callbacks:
                try:
                    callback(entry)
                except Exception as e:
                    print(f"Error callback error: {e}")

    def debug(self, message: str, **context):
        """Debug 日志"""
        self.log(LogLevel.DEBUG, message, **context)

    def info(self, message: str, **context):
        """Info 日志"""
        self.log(LogLevel.INFO, message, **context)

    def warning(self, message: str, **context):
        """Warning 日志"""
        self.log(LogLevel.WARNING, message, **context)

    def error(self, message: str, **context):
        """Error 日志"""
        self.log(LogLevel.ERROR, message, **context)

    def critical(self, message: str, **context):
        """Critical 日志"""
        self.log(LogLevel.CRITICAL, message, **context)

    def on_error(self, callback: Callable[[LogEntry], None]):
        """注册错误回调"""
        self._on_error_callbacks.append(callback)

    # ==================== 追踪方法 ====================

    def start_trace(self) -> str:
        """开始一个新的追踪"""
        self._current_trace_id = str(uuid.uuid4())
        return self._current_trace_id

    def end_trace(self):
        """结束当前追踪"""
        self._current_trace_id = None

    def start_span(self, name: str, span_type: SpanType = SpanType.CUSTOM,
                   parent_span_id: str = None, **tags) -> Span:
        """开始一个 Span

        Args:
            name: Span 名称
            span_type: Span 类型
            parent_span_id: 父 Span ID
            **tags: 标签

        Returns:
            Span: 创建的 Span
        """
        span = Span(
            trace_id=self._current_trace_id or str(uuid.uuid4()),
            span_id=str(uuid.uuid4())[:12],
            name=name,
            span_type=span_type,
            start_time=time.time(),
            agent_id=self.agent_id,
            session_id=self.session_id,
            tags=tags,
            parent_span_id=parent_span_id
        )

        with self._lock:
            self._active_spans[span.span_id] = span

        return span

    def end_span(self, span: Span, status: str = "success", error: str = None):
        """结束一个 Span

        Args:
            span: Span 对象
            status: 状态
            error: 错误信息
        """
        span.finish(status, error)

        with self._lock:
            self._active_spans.pop(span.span_id, None)

        # 写入存储
        self.storage.write_trace(span)

        # 记录指标
        if span.duration_ms is not None:
            self.record_metric(
                f"{span.span_type.value}_duration_ms",
                span.duration_ms,
                span_id=span.span_id,
                op_name=span.name
            )

    # ==================== 指标方法 ====================

    def record_metric(self, name: str, value: float, **tags):
        """记录指标

        Args:
            name: 指标名称
            value: 指标值
            **tags: 标签
        """
        metric = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            tags={**tags, "agent_id": self.agent_id}
        )

        self.storage.write_metric(metric)

        # 本地聚合
        if name not in self._metrics:
            self._metrics[name] = []
        self._metrics[name].append(value)

        # 限制大小
        if len(self._metrics[name]) > 1000:
            self._metrics[name] = self._metrics[name][-500:]

    def get_metric_stats(self, metric_name: str) -> Dict[str, float]:
        """获取指标统计

        Args:
            metric_name: 指标名称

        Returns:
            Dict: 统计信息
        """
        values = self._metrics.get(metric_name, [])
        if not values:
            return {}

        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "p50": sorted(values)[len(values) // 2] if values else 0,
            "p95": sorted(values)[int(len(values) * 0.95)] if values else 0,
            "p99": sorted(values)[int(len(values) * 0.99)] if values else 0,
        }

    # ==================== 查询方法 ====================

    def get_recent_logs(self, limit: int = 100, level: LogLevel = None) -> List[Dict[str, Any]]:
        """获取最近的日志"""
        logs = self.storage.get_logs(
            agent_id=self.agent_id,
            session_id=self.session_id,
            level=level,
            limit=limit
        )
        return [log.to_dict() for log in logs]

    def get_trace_detail(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """获取追踪详情"""
        return self.storage.get_trace(trace_id)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """获取仪表板数据"""
        key_metrics = [
            "llm_call_duration_ms",
            "tool_execution_duration_ms",
            "route_dispatch_duration_ms"
        ]

        dashboard = {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "metrics": {}
        }

        for metric_name in key_metrics:
            dashboard["metrics"][metric_name] = self.get_metric_stats(metric_name)

        # 最近错误
        recent_errors = self.get_recent_logs(limit=20, level=LogLevel.ERROR)
        dashboard["recent_errors"] = recent_errors

        # 活动追踪
        with self._lock:
            dashboard["active_spans"] = [
                span.to_dict() for span in self._active_spans.values()
            ]

        return dashboard

    def shutdown(self):
        """关闭可观测性平台"""
        # 等待日志队列处理完成
        self._log_queue.put(None)
        self._log_thread.join(timeout=5)

        # 结束所有活动的 Span
        with self._lock:
            for span in list(self._active_spans.values()):
                span.finish("interrupted")
                self.storage.write_trace(span)
            self._active_spans.clear()


# 全局实例
_observability_platforms: Dict[str, AgentObservabilityPlatform] = {}


def get_observability_platform(agent_id: str, session_id: str = None) -> AgentObservabilityPlatform:
    """获取可观测性平台实例"""
    key = f"{agent_id}:{session_id or 'default'}"
    if key not in _observability_platforms:
        _observability_platforms[key] = AgentObservabilityPlatform(agent_id, session_id)
    return _observability_platforms[key]


def log_to_observability(agent_id: str, level: str, message: str, **context):
    """便捷日志函数"""
    platform = get_observability_platform(agent_id)
    log_method = getattr(platform, level.lower(), platform.info)
    log_method(message, **context)


# 装饰器
def observability_span(span_type: SpanType = SpanType.CUSTOM, name: str = None):
    """追踪 Span 装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 尝试获取 self.agent_id 和 self.session_id
            self_obj = args[0] if args else None
            agent_id = getattr(self_obj, 'agent_id', 'unknown')
            session_id = getattr(self_obj, 'state', {}).get('session_id', 'unknown') if hasattr(self_obj, 'state') else 'unknown'

            platform = get_observability_platform(agent_id, session_id)

            span_name = name or func.__name__
            span = platform.start_span(span_name, span_type)

            try:
                result = func(*args, **kwargs)
                platform.end_span(span, status="success")
                return result
            except Exception as e:
                platform.end_span(span, status="error", error=str(e))
                raise

        return wrapper
    return decorator
