"""Stream Output Manager - 流式输出管理器

参考 Claude Code 的设计：
1. 实时推送执行状态
2. 支持多种事件类型（开始、执行中、完成、错误）
3. 服务端发送事件 (SSE) 支持
"""

import json
import time
import asyncio
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import threading


class StreamEventType(Enum):
    """流式事件类型"""
    # 会话级别
    SESSION_START = "session_start"
    SESSION_END = "session_end"

    # 输入/输出
    INPUT_RECEIVED = "input_received"
    PLANNING = "planning"

    # 思考相关
    THOUGHT = "thought"
    THINKING_START = "thinking_start"
    THINKING_DELTA = "thinking_delta"
    THINKING_END = "thinking_end"

    # 执行相关
    EXECUTION_START = "execution_start"
    EXECUTION_PROGRESS = "execution_progress"
    EXECUTION_COMPLETE = "execution_complete"
    EXECUTION_ERROR = "execution_error"

    # 工具调用
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOOL_CALL_START = "tool_call_start"
    TOOL_CALL_END = "tool_call_end"
    TOOL_OUTPUT = "tool_output"

    # 自主执行
    AUTONOMOUS_START = "autonomous_start"
    AUTONOMOUS_STEP = "autonomous_step"
    AUTONOMOUS_REFLECT = "autonomous_reflect"
    AUTONOMOUS_COMPLETE = "autonomous_complete"

    # 响应
    RESPONSE_START = "response_start"
    RESPONSE_TOKEN = "response_token"
    RESPONSE_END = "response_end"

    # 完成/错误
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class StreamEvent:
    """流式事件"""
    type: StreamEventType
    timestamp: float
    agent_id: str
    session_id: str
    data: Dict[str, Any]
    sequence: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "data": self.data,
            "sequence": self.sequence
        }

    def to_sse(self) -> str:
        """转换为 SSE 格式"""
        return f"data: {json.dumps(self.to_dict(), ensure_ascii=False)}\n\n"


class StreamManager:
    """流式管理器 - 单例模式"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._subscribers: Dict[str, List[Callable[[StreamEvent], None]]] = {}
        self._event_queues: Dict[str, List[StreamEvent]] = {}
        self._sequence_counters: Dict[str, int] = {}
        self._state_dir = Path("storage/stream_states")
        self._state_dir.mkdir(parents=True, exist_ok=True)
        # 异步支持
        self._async_subscribers: Dict[str, List[Callable]] = {}
        # 批量发射缓冲
        self._buffer_lock = threading.Lock()

    def subscribe(self, session_id: str, callback: Callable[[StreamEvent], None]):
        """订阅会话的流式事件

        Args:
            session_id: 会话 ID
            callback: 事件回调函数
        """
        if session_id not in self._subscribers:
            self._subscribers[session_id] = []
            self._event_queues[session_id] = []
            self._sequence_counters[session_id] = 0

        self._subscribers[session_id].append(callback)

    async def subscribe_async(self, session_id: str, callback: Callable):
        """异步订阅会话的流式事件

        Args:
            session_id: 会话 ID
            callback: 异步回调函数
        """
        if session_id not in self._async_subscribers:
            self._async_subscribers[session_id] = []

        self._async_subscribers[session_id].append(callback)

    def unsubscribe(self, session_id: str, callback: Callable[[StreamEvent], None]):
        """取消订阅"""
        if session_id in self._subscribers:
            self._subscribers[session_id].remove(callback)

    def emit(self, event: StreamEventType, agent_id: str, session_id: str, data: Dict[str, Any]):
        """发射事件

        Args:
            event: 事件类型
            agent_id: Agent ID
            session_id: 会话 ID
            data: 事件数据
        """
        event_obj = StreamEvent(
            type=event,
            timestamp=time.time(),
            agent_id=agent_id,
            session_id=session_id,
            data=data,
            sequence=self._sequence_counters.get(session_id, 0)
        )

        self._sequence_counters[session_id] = event_obj.sequence + 1

        # 写入文件（用于 SSE 轮询）
        self._write_to_file(session_id, event_obj)

        # 通知订阅者
        if session_id in self._subscribers:
            for callback in self._subscribers[session_id]:
                try:
                    callback(event_obj)
                except Exception as e:
                    print(f"Stream callback error: {e}")

        # 异步通知订阅者
        if session_id in self._async_subscribers:
            asyncio.create_task(self._notify_async_subscribers(session_id, event_obj))

    async def _notify_async_subscribers(self, session_id: str, event: StreamEvent):
        """通知异步订阅者"""
        for callback in self._async_subscribers.get(session_id, []):
            try:
                await callback(event)
            except Exception as e:
                print(f"Async stream callback error: {e}")

    def emit_batch(self, session_id: str, events: List[tuple]):
        """批量发射事件

        Args:
            session_id: 会话 ID
            events: 事件列表，每个元素为 (event_type, data) 元组
        """
        with self._buffer_lock:
            for event_type, data in events:
                self.emit(event_type, self._get_agent_id(session_id), session_id, data)

    def _get_agent_id(self, session_id: str) -> str:
        """从会话 ID 获取 Agent ID（简化实现）"""
        return "agent"

    def _write_to_file(self, session_id: str, event: StreamEvent):
        """将事件写入文件"""
        try:
            # 清理旧的 session_id（避免文件名过长）
            safe_session_id = session_id.replace("-", "_")[:32]
            state_file = self._state_dir / f"{safe_session_id}.jsonl"

            with open(state_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Stream write error: {e}")

    def get_events(self, session_id: str, since_sequence: int = 0) -> List[StreamEvent]:
        """获取会话的事件（用于轮询）

        Args:
            session_id: 会话 ID
            since_sequence: 起始序列号

        Returns:
            事件列表
        """
        events = self._event_queues.get(session_id, [])
        return [e for e in events if e.sequence > since_sequence]

    def get_latest_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取最新状态（用于快速查询）

        Args:
            session_id: 会话 ID

        Returns:
            最新状态
        """
        events = self.get_events(session_id)
        if not events:
            return None

        # 返回最后一个事件的状态
        return events[-1].to_dict()

    def clear_session(self, session_id: str):
        """清除会话状态"""
        self._subscribers.pop(session_id, None)
        self._event_queues.pop(session_id, None)
        self._sequence_counters.pop(session_id, None)

        # 删除文件
        safe_session_id = session_id.replace("-", "_")[:32]
        state_file = self._state_dir / f"{safe_session_id}.jsonl"
        if state_file.exists():
            state_file.unlink()


# 便捷函数
def stream_emit(event: StreamEventType, agent_id: str, session_id: str, data: Dict[str, Any]):
    """便捷函数：发射流式事件"""
    manager = StreamManager()
    manager.emit(event, agent_id, session_id, data)


# 与 Brain 状态更新集成
class StreamStateUpdater:
    """流式状态更新器 - 与 Brain 的_update_state 集成"""

    def __init__(self, stream_manager: StreamManager = None):
        self.stream_manager = stream_manager or StreamManager()

    def update(
        self,
        agent_id: str,
        session_id: str,
        status: str,
        action: str = None,
        route: str = None,
        details: dict = None,
        elapsed_ms: int = 0
    ):
        """更新状态并发射事件"""
        event_type = self._status_to_event(status)

        data = {
            "status": status,
            "current_action": action,
            "route": route,
            "elapsed_ms": elapsed_ms,
            "details": details or {}
        }

        self.stream_manager.emit(event_type, agent_id, session_id, data)

    def _status_to_event(self, status: str) -> StreamEventType:
        """将状态字符串转换为事件类型"""
        mapping = {
            "received": StreamEventType.INPUT_RECEIVED,
            "planning": StreamEventType.PLANNING,
            "deciding": StreamEventType.THOUGHT,
            "thinking": StreamEventType.THOUGHT,
            "executing": StreamEventType.EXECUTION_START,
            "iteration": StreamEventType.EXECUTION_PROGRESS,
            "completed": StreamEventType.COMPLETE,
            "error": StreamEventType.EXECUTION_ERROR,
            "autonomous_mode": StreamEventType.PLANNING,
            "autonomous_start": StreamEventType.SESSION_START,
        }
        return mapping.get(status, StreamEventType.EXECUTION_PROGRESS)


# 全局实例
stream_manager = StreamManager()
stream_updater = StreamStateUpdater(stream_manager)


class ThinkingBudget:
    """思考预算管理 - 控制扩展思考模式的 Token 使用"""

    def __init__(self, max_tokens: int = 32000):
        """初始化思考预算

        Args:
            max_tokens: 最大思考 token 数，默认 32000（参考 Claude Code 的 31999）
        """
        self.max_tokens = max_tokens
        self.used_tokens = 0
        self.session_id: str = None
        self.agent_id: str = None

    def can_spend(self, estimated: int) -> bool:
        """判断是否可以花费指定的 token

        Args:
            estimated: 预估需要花费的 token 数

        Returns:
            bool: 是否可以花费
        """
        return self.used_tokens + estimated <= self.max_tokens

    def spend(self, tokens: int) -> bool:
        """花费 token

        Args:
            tokens: 要花费的 token 数

        Returns:
            bool: 是否花费成功
        """
        if self.can_spend(tokens):
            self.used_tokens += tokens
            return True
        return False

    def reset(self):
        """重置预算"""
        self.used_tokens = 0

    def get_remaining(self) -> int:
        """获取剩余预算"""
        return max(0, self.max_tokens - self.used_tokens)

    def get_usage_percent(self) -> float:
        """获取使用百分比"""
        return (self.used_tokens / self.max_tokens) * 100 if self.max_tokens > 0 else 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "max_tokens": self.max_tokens,
            "used_tokens": self.used_tokens,
            "remaining_tokens": self.get_remaining(),
            "usage_percent": round(self.get_usage_percent(), 2)
        }


class ExtendedThinkingMode:
    """扩展思考模式 - 支持深度推理和思考过程输出"""

    def __init__(self, budget: ThinkingBudget = None, stream_manager: StreamManager = None):
        """初始化扩展思考模式

        Args:
            budget: 思考预算
            stream_manager: 流式管理器
        """
        self.budget = budget or ThinkingBudget()
        self.stream_manager = stream_manager or StreamManager()
        self._thinking_history: List[Dict[str, Any]] = []

    async def start_thinking(self, session_id: str, agent_id: str, prompt: str):
        """开始思考

        Args:
            session_id: 会话 ID
            agent_id: Agent ID
            prompt: 思考的问题
        """
        self.budget.session_id = session_id
        self.budget.agent_id = agent_id

        # 发射思考开始事件
        self.stream_manager.emit(
            StreamEventType.THINKING_START,
            agent_id=agent_id,
            session_id=session_id,
            data={"prompt": prompt[:200], "budget": self.budget.to_dict()}
        )

    async def thinking_delta(self, session_id: str, agent_id: str, thought: str, tokens_used: int = 0):
        """思考增量输出

        Args:
            session_id: 会话 ID
            agent_id: Agent ID
            thought: 思考内容片段
            tokens_used: 使用的 token 数
        """
        self.budget.spend(tokens_used)

        # 记录思考历史
        self._thinking_history.append({
            "thought": thought,
            "tokens": tokens_used,
            "timestamp": time.time()
        })

        # 发射思考增量事件
        self.stream_manager.emit(
            StreamEventType.THINKING_DELTA,
            agent_id=agent_id,
            session_id=session_id,
            data={
                "thought": thought[:500],  # 限制长度
                "tokens_used": tokens_used,
                "budget_remaining": self.budget.get_remaining()
            }
        )

    async def end_thinking(self, session_id: str, agent_id: str, conclusion: str):
        """结束思考

        Args:
            session_id: 会话 ID
            agent_id: Agent ID
            conclusion: 思考结论
        """
        # 发射思考结束事件
        self.stream_manager.emit(
            StreamEventType.THINKING_END,
            agent_id=agent_id,
            session_id=session_id,
            data={
                "conclusion": conclusion[:1000],
                "total_tokens": self.budget.used_tokens,
                "thinking_steps": len(self._thinking_history)
            }
        )

    def get_thinking_history(self) -> List[Dict[str, Any]]:
        """获取思考历史"""
        return self._thinking_history.copy()

    def clear_history(self):
        """清除思考历史"""
        self._thinking_history.clear()
