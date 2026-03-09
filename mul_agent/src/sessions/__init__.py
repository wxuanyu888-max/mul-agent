"""
Sessions - 会话管理
"""

__all__ = ["Session", "SessionManager"]


class Session:
    """会话类"""

    def __init__(self, session_id: str, agent_id: str, user_id: str | None = None):
        self.session_id = session_id
        self.agent_id = agent_id
        self.user_id = user_id
        self.messages: list[dict] = []

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})


class SessionManager:
    """会话管理器"""

    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create(self, agent_id: str, user_id: str | None = None) -> Session:
        import uuid
        session = Session(str(uuid.uuid4()), agent_id, user_id)
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def list(self) -> list[Session]:
        return list(self._sessions.values())
