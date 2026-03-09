"""Session State Persistence - 会话状态持久化

参考 Claude Code 的设计：
1. 会话结束时自动保存状态
2. 新会话时可以加载上次上下文
3. 支持检查工作点恢复
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
import threading


@dataclass
class SessionState:
    """会话状态"""
    session_id: str
    agent_id: str
    start_time: float
    end_time: Optional[float] = None
    current_task: Optional[str] = None
    plan: Optional[List[Dict[str, Any]]] = None
    history: Optional[List[Dict[str, Any]]] = None
    working_directory: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "current_task": self.current_task,
            "plan": self.plan,
            "history": self.history,
            "working_directory": self.working_directory,
            "variables": self.variables,
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionState":
        """从字典创建"""
        return cls(
            session_id=data.get("session_id", ""),
            agent_id=data.get("agent_id", ""),
            start_time=data.get("start_time", time.time()),
            end_time=data.get("end_time"),
            current_task=data.get("current_task"),
            plan=data.get("plan"),
            history=data.get("history"),
            working_directory=data.get("working_directory"),
            variables=data.get("variables"),
            metadata=data.get("metadata", {})
        )


class SessionStateManager:
    """会话状态管理器 - 单例模式"""

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
        self._state_dir = Path("storage/sessions")
        self._state_dir.mkdir(parents=True, exist_ok=True)
        self._active_sessions: Dict[str, SessionState] = {}
        self._lock = threading.RLock()

    def save_state(self, state: SessionState) -> bool:
        """保存会话状态

        Args:
            state: 会话状态

        Returns:
            bool: 是否保存成功
        """
        try:
            with self._lock:
                # 生成安全的文件名
                safe_session_id = self._safe_filename(state.session_id)
                state_file = self._state_dir / f"{safe_session_id}.json"

                # 序列化状态
                data = state.to_dict()
                data["saved_at"] = time.time()

                # 写入文件
                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # 记录活跃会话
                self._active_sessions[state.session_id] = state

                return True
        except Exception as e:
            print(f"Save session state error: {e}")
            return False

    def load_state(self, session_id: str) -> Optional[SessionState]:
        """加载会话状态

        Args:
            session_id: 会话 ID

        Returns:
            SessionState: 会话状态，如果不存在则返回 None
        """
        try:
            # 先从内存缓存加载
            if session_id in self._active_sessions:
                return self._active_sessions[session_id]

            # 从文件加载
            safe_session_id = self._safe_filename(session_id)
            state_file = self._state_dir / f"{safe_session_id}.json"

            if not state_file.exists():
                return None

            with open(state_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            state = SessionState.from_dict(data)

            # 缓存到内存
            self._active_sessions[session_id] = state

            return state
        except Exception as e:
            print(f"Load session state error: {e}")
            return None

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """列出最近的会话

        Args:
            limit: 限制数量

        Returns:
            List[Dict]: 会话列表
        """
        sessions = []

        # 遍历状态目录
        for state_file in self._state_dir.glob("*.json"):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                sessions.append({
                    "session_id": data.get("session_id", ""),
                    "agent_id": data.get("agent_id", ""),
                    "start_time": data.get("start_time", 0),
                    "end_time": data.get("end_time"),
                    "current_task": data.get("current_task", ""),
                    "saved_at": data.get("saved_at", 0)
                })
            except Exception:
                continue

        # 按保存时间排序
        sessions.sort(key=lambda x: x.get("saved_at", 0), reverse=True)

        return sessions[:limit]

    def delete_session(self, session_id: str) -> bool:
        """删除会话状态

        Args:
            session_id: 会话 ID

        Returns:
            bool: 是否删除成功
        """
        try:
            with self._lock:
                safe_session_id = self._safe_filename(session_id)
                state_file = self._state_dir / f"{safe_session_id}.json"

                if state_file.exists():
                    state_file.unlink()

                # 从内存缓存移除
                self._active_sessions.pop(session_id, None)

                return True
        except Exception as e:
            print(f"Delete session state error: {e}")
            return False

    def clear_old_sessions(self, days: int = 7) -> int:
        """清理旧的会话状态

        Args:
            days: 保留天数

        Returns:
            int: 清理的会话数量
        """
        cleaned = 0
        cutoff_time = time.time() - (days * 24 * 60 * 60)

        for state_file in self._state_dir.glob("*.json"):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                saved_at = data.get("saved_at", 0)
                if saved_at < cutoff_time:
                    state_file.unlink()
                    cleaned += 1
            except Exception:
                continue

        return cleaned

    def create_state(
        self,
        session_id: str,
        agent_id: str,
        **kwargs
    ) -> SessionState:
        """创建新的会话状态

        Args:
            session_id: 会话 ID
            agent_id: Agent ID
            **kwargs: 其他参数

        Returns:
            SessionState: 创建的会话状态
        """
        state = SessionState(
            session_id=session_id,
            agent_id=agent_id,
            start_time=time.time(),
            current_task=kwargs.get("current_task"),
            plan=kwargs.get("plan"),
            history=kwargs.get("history", [])[-50:],  # 只保留最近 50 条
            working_directory=kwargs.get("working_directory"),
            variables=kwargs.get("variables"),
            metadata=kwargs.get("metadata")
        )

        return state

    def update_state(
        self,
        session_id: str,
        **kwargs
    ) -> bool:
        """更新会话状态

        Args:
            session_id: 会话 ID
            **kwargs: 要更新的参数

        Returns:
            bool: 是否更新成功
        """
        state = self.load_state(session_id)
        if not state:
            return False

        # 更新参数
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)

        return self.save_state(state)

    def _safe_filename(self, session_id: str) -> str:
        """生成安全的文件名"""
        # 移除特殊字符，只保留字母、数字、下划线、连字符
        import re
        safe = re.sub(r'[^a-zA-Z0-9_-]', '_', session_id)
        # 限制长度
        return safe[:64]


# 便捷函数
def save_session_state(session_id: str, agent_id: str, **kwargs) -> bool:
    """便捷函数：保存会话状态"""
    manager = SessionStateManager()
    state = manager.create_state(session_id, agent_id, **kwargs)
    return manager.save_state(state)


def load_session_state(session_id: str) -> Optional[Dict[str, Any]]:
    """便捷函数：加载会话状态"""
    manager = SessionStateManager()
    state = manager.load_state(session_id)
    return state.to_dict() if state else None


def resume_last_session(agent_id: str) -> Optional[Dict[str, Any]]:
    """恢复最近的会话"""
    manager = SessionStateManager()
    sessions = manager.list_sessions(limit=1)

    if not sessions:
        return None

    last_session = sessions[0]
    state = manager.load_state(last_session["session_id"])

    if state and state.agent_id == agent_id:
        return state.to_dict()

    return None


# 全局实例
session_state_manager = SessionStateManager()
