"""
Session Manager 测试
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from mul_agent.sessions.session_manager import (
    SessionManager,
    SessionMessage,
    TokenThreshold,
    estimate_tokens,
)


class TestEstimateTokens:
    """Token 估算测试"""

    def test_empty_string(self):
        assert estimate_tokens("") == 0
        assert estimate_tokens(None) == 0

    def test_english_text(self):
        # 英文约 4 字符/token
        text = "Hello World"
        tokens = estimate_tokens(text)
        assert tokens > 0

    def test_chinese_text(self):
        # 中文约 1.5 字符/token
        text = "你好世界"
        tokens = estimate_tokens(text)
        assert tokens > 0

    def test_mixed_text(self):
        text = "Hello 你好 World 世界"
        tokens = estimate_tokens(text)
        assert tokens > 0


class TestSessionManager:
    """SessionManager 测试"""

    @pytest.fixture
    def temp_storage(self):
        """临时存储目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def session_manager(self, temp_storage):
        """SessionManager 实例"""
        return SessionManager(storage_path=temp_storage)

    def test_create_session(self, session_manager):
        """测试创建会话"""
        session = session_manager.create_session(
            title="测试会话"
        )

        assert session.id is not None
        assert session.title == "测试会话"
        assert session.agent_id == "default"
        assert session.messages == []
        assert session.token_count == 0

    def test_create_session_with_custom_id(self, session_manager):
        """测试创建指定 ID 的会话"""
        session = session_manager.create_session(
            session_id="my-custom-id",
            title="自定义会话"
        )

        assert session.id == "my-custom-id"
        assert session.title == "自定义会话"

    def test_create_session_with_agent_id(self, session_manager):
        """测试创建指定 Agent ID 的会话"""
        session = session_manager.create_session(
            agent_id="test-agent",
            title="Agent 会话"
        )

        assert session.agent_id == "test-agent"

    def test_create_session_with_initial_messages(self, session_manager):
        """测试创建带初始消息的会话"""
        initial_messages = [
            SessionMessage(
                id="msg-1",
                role="user",
                content="你好",
                timestamp=datetime.now().timestamp()
            ),
            SessionMessage(
                id="msg-2",
                role="assistant",
                content="你好！有什么可以帮助你的？",
                timestamp=datetime.now().timestamp()
            )
        ]

        session = session_manager.create_session(
            initial_messages=initial_messages
        )

        assert len(session.messages) == 2
        assert session.messages[0].role == "user"
        assert session.messages[1].role == "assistant"
        assert session.token_count > 0

    def test_load_session(self, session_manager):
        """测试加载会话"""
        # 创建会话
        created = session_manager.create_session(
            session_id="load-test",
            title="加载测试"
        )

        # 重新加载
        loaded = session_manager.load_session("load-test")

        assert loaded.id == created.id
        assert loaded.title == created.title

    def test_load_session_not_found(self, session_manager):
        """测试加载不存在的会话"""
        session = session_manager.load_session("non-existent-session")
        assert session is not None
        assert session.messages == []

    def test_add_message(self, session_manager):
        """测试添加消息"""
        session_manager.create_session(session_id="msg-test")

        # 添加用户消息
        session = session_manager.add_message(
            "msg-test",
            role="user",
            content="第一条消息"
        )
        assert len(session.messages) == 1
        assert session.messages[0].content == "第一条消息"

        # 添加 Agent 回复
        session = session_manager.add_message(
            "msg-test",
            role="assistant",
            content="这是回复"
        )
        assert len(session.messages) == 2
        assert session.messages[1].role == "assistant"

    def test_add_message_with_metadata(self, session_manager):
        """测试添加带元数据的消息"""
        session_manager.create_session(session_id="meta-test")

        session = session_manager.add_message(
            "meta-test",
            role="user",
            content="测试消息",
            metadata={"source": "test", "priority": "high"}
        )

        assert session.messages[0].metadata == {"source": "test", "priority": "high"}

    def test_update_session_metadata(self, session_manager):
        """测试更新会话元数据"""
        session_manager.create_session(
            session_id="update-test",
            title="原始标题"
        )

        # 更新标题
        session = session_manager.update_session_metadata(
            "update-test",
            title="新标题"
        )
        assert session.title == "新标题"

        # 更新元数据
        session = session_manager.update_session_metadata(
            "update-test",
            metadata={"key": "value"}
        )
        assert session.metadata == {"key": "value"}

    def test_list_sessions(self, session_manager):
        """测试列出会话"""
        # 创建多个会话
        session_manager.create_session(session_id="session-1")
        session_manager.create_session(session_id="session-2")
        session_manager.create_session(session_id="session-3")

        sessions = session_manager.list_sessions()
        assert len(sessions) == 3

        session_ids = [s.id for s in sessions]
        assert "session-1" in session_ids
        assert "session-2" in session_ids
        assert "session-3" in session_ids

    def test_list_sessions_by_agent_id(self, session_manager):
        """测试按 Agent ID 过滤会话"""
        session_manager.create_session(
            session_id="agent1-session1",
            agent_id="agent1"
        )
        session_manager.create_session(
            session_id="agent1-session2",
            agent_id="agent1"
        )
        session_manager.create_session(
            session_id="agent2-session1",
            agent_id="agent2"
        )

        # 列出 agent1 的会话
        sessions = session_manager.list_sessions(agent_id="agent1")
        assert len(sessions) == 2
        assert all(s.agent_id == "agent1" for s in sessions)

        # 列出 agent2 的会话
        sessions = session_manager.list_sessions(agent_id="agent2")
        assert len(sessions) == 1

    def test_delete_session(self, session_manager):
        """测试删除会话"""
        session_manager.create_session(session_id="delete-test")

        # 验证会话存在
        sessions = session_manager.list_sessions()
        assert any(s.id == "delete-test" for s in sessions)

        # 删除会话
        session_manager.delete_session("delete-test")

        # 验证会话已删除
        sessions = session_manager.list_sessions()
        assert not any(s.id == "delete-test" for s in sessions)

    def test_delete_nonexistent_session(self, session_manager):
        """测试删除不存在的会话（应该不报错）"""
        session_manager.delete_session("non-existent")

    def test_session_cache(self, session_manager):
        """测试会话缓存"""
        # 创建会话
        session_manager.create_session(
            session_id="cache-test",
            title="缓存测试"
        )

        # 第一次加载（从文件）
        session1 = session_manager.load_session("cache-test")

        # 第二次加载（从缓存）
        session2 = session_manager.load_session("cache-test")

        assert session1.id == session2.id
        # 缓存应该返回同一个对象或相同内容

    def test_token_counting(self, session_manager):
        """测试 Token 计数"""
        session = session_manager.create_session(
            initial_messages=[
                SessionMessage(
                    id="msg-1",
                    role="user",
                    content="Hello 你好",
                    timestamp=datetime.now().timestamp()
                )
            ]
        )

        assert session.token_count > 0

        # 添加消息后 token 数应该增加
        session = session_manager.add_message(
            "cache-test",
            role="assistant",
            content="这是回复内容"
        )
        assert session.token_count > 0

    def test_compression_detection(self, session_manager):
        """测试压缩检测"""
        # 创建一个带有大量消息的会话
        session = session_manager.create_session(session_id="compress-test")

        # 添加大量消息直到超过阈值
        large_content = "这是一条很长的消息。" * 1000
        for i in range(20):
            session_manager.add_message(
                "compress-test",
                role="user" if i % 2 == 0 else "assistant",
                content=large_content
            )

        # 重新加载会话检查是否需要压缩
        session = session_manager.load_session("compress-test")
        assert session.needs_compression is True
        assert session.compression_reason != ""

    def test_compression_hint(self, session_manager):
        """测试获取压缩提示"""
        session = session_manager.create_session(session_id="hint-test")

        # 空会话不需要压缩
        hint = session_manager.get_compression_hint(session)
        assert hint.needs_compression is False

        # 添加大量消息
        large_content = "长消息。" * 500
        for i in range(30):
            session_manager.add_message(
                "hint-test",
                role="user" if i % 2 == 0 else "assistant",
                content=large_content
            )

        # 重新加载并检查提示
        session = session_manager.load_session("hint-test")
        hint = session_manager.get_compression_hint(session)
        assert hint.needs_compression is True
        assert hint.compression_type in ["session", "bootstrap"]
        assert hint.prompt is not None

    def test_persistence(self, temp_storage):
        """测试数据持久化"""
        # 创建管理器并添加数据
        manager1 = SessionManager(storage_path=temp_storage)
        manager1.create_session(
            session_id="persist-test",
            title="持久化测试",
            initial_messages=[
                SessionMessage(
                    id="msg-1",
                    role="user",
                    content="测试消息",
                    timestamp=datetime.now().timestamp()
                )
            ]
        )

        # 创建新的管理器实例（模拟重启）
        manager2 = SessionManager(storage_path=temp_storage)

        # 加载会话验证数据保留
        session = manager2.load_session("persist-test")
        assert session.title == "持久化测试"
        assert len(session.messages) == 1
        assert session.messages[0].content == "测试消息"

    def test_event_callbacks(self, session_manager):
        """测试事件回调"""
        created_sessions = []
        deleted_sessions = []

        @session_manager.on_session_created
        def on_created(ctx):
            created_sessions.append(ctx.id)

        @session_manager.on_session_deleted
        def on_deleted(session_id, agent_id):
            deleted_sessions.append(session_id)

        # 创建会话
        session_manager.create_session(session_id="event-test-1")
        session_manager.create_session(session_id="event-test-2")

        assert len(created_sessions) == 2
        assert "event-test-1" in created_sessions
        assert "event-test-2" in created_sessions

        # 删除会话
        session_manager.delete_session("event-test-1")
        assert len(deleted_sessions) == 1
        assert "event-test-1" in deleted_sessions

    def test_load_session_max_messages(self, session_manager):
        """测试分页加载消息"""
        # 创建有 10 条消息的会话
        session_manager.create_session(session_id="page-test")
        for i in range(10):
            session_manager.add_message(
                "page-test",
                role="user" if i % 2 == 0 else "assistant",
                content=f"消息 {i}"
            )

        # 限制加载 5 条
        session = session_manager.load_session("page-test", max_messages=5)
        assert len(session.messages) == 5
        # 应该是最后 5 条
        assert session.messages[0].content == "消息 5"
        assert session.messages[-1].content == "消息 9"


class TestTokenThreshold:
    """TokenThreshold 测试"""

    def test_default_values(self):
        threshold = TokenThreshold()
        assert threshold.session_warning == 8000
        assert threshold.session_max == 16000
        assert threshold.bootstrap_warning == 4000
        assert threshold.bootstrap_max == 8000
        assert threshold.compression_target == 3000

    def test_custom_values(self):
        threshold = TokenThreshold(
            session_warning=5000,
            session_max=10000,
        )
        assert threshold.session_warning == 5000
        assert threshold.session_max == 10000
        assert threshold.bootstrap_warning == 4000  # 默认值
        assert threshold.bootstrap_max == 8000  # 默认值
