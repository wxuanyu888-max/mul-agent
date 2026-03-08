"""Tests for Handlers"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from mul_agent.brain.handlers.chat import ChatHandler
from mul_agent.brain.handlers.bash import BashHandler
from mul_agent.brain.handlers.memory import MemoryHandler
from mul_agent.brain.handlers.heart import HeartHandler
from mul_agent.brain.handlers.response import ResponseHandler
from mul_agent.brain.handlers.create_user import CreateUserHandler
from mul_agent.brain.config_manager import ConfigManager


class TestChatHandler:
    """ChatHandler test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def chat_handler(self, temp_dir):
        """Create ChatHandler instance"""
        config_manager = ConfigManager(temp_dir)
        return ChatHandler(config_manager, agent_id="test_agent")

    def test_handle_send_action(self, chat_handler):
        """Test handling send action"""
        params = {
            "action": "send",
            "agent_id": "test_agent",
            "message": "Hello"
        }
        result = chat_handler.handle(params)
        assert isinstance(result, dict)
        assert "status" in result

    def test_handle_switch_action(self, chat_handler):
        """Test handling switch action"""
        params = {
            "action": "switch",
            "agent_id": "test_agent"
        }
        result = chat_handler.handle(params)
        assert isinstance(result, dict)

    def test_handle_list_action(self, chat_handler):
        """Test handling list action"""
        params = {
            "action": "list",
            "agent_id": "test_agent"
        }
        result = chat_handler.handle(params)
        assert isinstance(result, dict)
        assert "status" in result

    def test_handle_clear_action(self, chat_handler):
        """Test handling clear action"""
        # First create a conversation
        chat_handler.conversations["test_conv"] = [{"role": "user", "content": "test"}]

        params = {
            "action": "clear",
            "conversation_id": "test_conv"
        }
        result = chat_handler.handle(params)
        assert isinstance(result, dict)
        assert "test_conv" not in chat_handler.conversations

    def test_handle_unknown_action(self, chat_handler):
        """Test handling unknown action"""
        params = {
            "action": "unknown_action"
        }
        result = chat_handler.handle(params)
        assert result["status"] == "error"
        assert result["error_code"] == 2001

    def test_handle_missing_params(self, chat_handler):
        """Test handling missing params"""
        result = chat_handler.handle(None)
        assert result["status"] == "error"

    def test_handle_send_creates_conversation(self, chat_handler):
        """Test that send action creates conversation"""
        params = {
            "action": "send",
            "agent_id": "test_agent",
            "message": "Test message"
        }
        result = chat_handler.handle(params)

        # Should create default conversation
        assert "test_agent_001" in chat_handler.conversations

    def test_conversations_shared_state(self, temp_dir):
        """Test that conversations are shared across instances"""
        config_manager = ConfigManager(temp_dir)
        handler1 = ChatHandler(config_manager, "agent_a")
        handler2 = ChatHandler(config_manager, "agent_b")

        # Both should share the same conversations dict
        handler1.conversations["shared"] = [{"role": "user", "content": "test"}]
        assert "shared" in handler2.conversations


class TestBashHandler:
    """BashHandler test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def bash_handler(self, temp_dir):
        """Create BashHandler instance"""
        config_manager = ConfigManager(temp_dir)
        return BashHandler(config_manager, agent_id="test_agent")

    def test_handle_echo_command(self, bash_handler):
        """Test handling echo command"""
        params = {"command": "echo hello"}
        result = bash_handler.handle(params)
        assert isinstance(result, dict)
        assert result["status"] == "success"

    def test_handle_ls_command(self, bash_handler):
        """Test handling ls command"""
        params = {"command": "ls -la"}
        result = bash_handler.handle(params)
        assert isinstance(result, dict)
        assert result["status"] == "success"

    def test_handle_invalid_command(self, bash_handler):
        """Test handling invalid command"""
        params = {"command": "nonexistent_command_xyz_123"}
        result = bash_handler.handle(params)
        assert isinstance(result, dict)
        # Command execution should still return success with error details
        assert "result" in result or "status" in result

    def test_handle_missing_params(self, bash_handler):
        """Test handling missing params"""
        result = bash_handler.handle({})
        assert isinstance(result, dict)

    def test_handle_with_timeout(self, bash_handler):
        """Test handling command with timeout"""
        params = {"command": "sleep 0.1", "timeout": 5}
        result = bash_handler.handle(params)
        assert isinstance(result, dict)


class TestMemoryHandler:
    """MemoryHandler test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def memory_handler(self, temp_dir):
        """Create MemoryHandler instance"""
        config_manager = ConfigManager(temp_dir)
        return MemoryHandler(config_manager, agent_id="test_agent")

    def test_handle_list_action(self, memory_handler):
        """Test handling list action"""
        params = {
            "action": "list",
            "memory_type": "short_term"
        }
        result = memory_handler.handle(params)
        assert isinstance(result, dict)
        assert "status" in result

    def test_handle_write_action(self, memory_handler):
        """Test handling write action"""
        params = {
            "action": "write",
            "memory_type": "short_term",
            "content": {"test": "data"}
        }
        result = memory_handler.handle(params)
        assert isinstance(result, dict)
        assert "status" in result

    def test_handle_search_action(self, memory_handler):
        """Test handling search action"""
        # First write something
        memory_handler.handle({
            "action": "write",
            "memory_type": "short_term",
            "content": {"content": "Test search data"}
        })

        params = {
            "action": "search",
            "query": "search"
        }
        result = memory_handler.handle(params)
        assert isinstance(result, dict)
        assert "status" in result

    def test_handle_delete_action(self, memory_handler):
        """Test handling delete action"""
        # First write and get ID
        write_result = memory_handler.handle({
            "action": "write",
            "memory_type": "short_term",
            "content": {"test": "to_delete"}
        })

        params = {
            "action": "delete",
            "memory_id": write_result.get("memory_id")
        }
        result = memory_handler.handle(params)
        assert isinstance(result, dict)

    def test_handle_unknown_action(self, memory_handler):
        """Test handling unknown action"""
        params = {"action": "unknown_action"}
        result = memory_handler.handle(params)
        assert result["status"] == "error"

    def test_handle_missing_action(self, memory_handler):
        """Test handling missing action"""
        result = memory_handler.handle({})
        assert result["status"] == "error"


class TestHeartHandler:
    """HeartHandler test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def heart_handler(self, temp_dir):
        """Create HeartHandler instance"""
        config_manager = ConfigManager(temp_dir)
        return HeartHandler(config_manager, agent_id="test_agent")

    def test_handle_manual_trigger(self, heart_handler):
        """Test handling manual trigger"""
        params = {"trigger": "manual", "focus": "status"}
        result = heart_handler.handle(params)
        assert isinstance(result, dict)
        assert "status" in result

    def test_handle_auto_trigger(self, heart_handler):
        """Test handling auto trigger"""
        params = {"trigger": "auto"}
        result = heart_handler.handle(params)
        assert isinstance(result, dict)

    def test_handle_evolution_focus(self, heart_handler):
        """Test handling evolution focus"""
        params = {"trigger": "manual", "focus": "evolution"}
        result = heart_handler.handle(params)
        assert isinstance(result, dict)

    def test_handle_missing_params(self, heart_handler):
        """Test handling missing params"""
        result = heart_handler.handle({})
        assert isinstance(result, dict)


class TestResponseHandler:
    """ResponseHandler test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def response_handler(self, temp_dir):
        """Create ResponseHandler instance"""
        config_manager = ConfigManager(temp_dir)
        return ResponseHandler(config_manager, agent_id="test_agent")

    def test_handle_with_message(self, response_handler):
        """Test handling response with message"""
        params = {"message": "Hello World"}
        result = response_handler.handle(params)
        assert isinstance(result, dict)
        assert "message" in result

    def test_handle_without_message(self, response_handler):
        """Test handling response without message"""
        params = {}
        result = response_handler.handle(params)
        assert isinstance(result, dict)
        assert "message" in result

    def test_handle_empty_string_message(self, response_handler):
        """Test handling empty string message"""
        params = {"message": ""}
        result = response_handler.handle(params)
        assert isinstance(result, dict)


class TestCreateUserHandler:
    """CreateUserHandler test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def create_user_handler(self, temp_dir):
        """Create CreateUserHandler instance"""
        config_manager = ConfigManager(temp_dir)
        return CreateUserHandler(config_manager, agent_id="test_agent")

    def test_handle_create_agent(self, create_user_handler):
        """Test creating a new agent"""
        params = {
            "agent_id": "new_agent",
            "name": "New Agent",
            "role_type": "worker"
        }
        result = create_user_handler.handle(params)
        assert isinstance(result, dict)
        assert result["status"] == "success"

    def test_handle_missing_agent_id(self, create_user_handler):
        """Test handling missing agent_id"""
        params = {"name": "New Agent"}
        result = create_user_handler.handle(params)
        # Should still succeed with generated ID
        assert isinstance(result, dict)

    def test_handle_create_agent_directory_created(self, create_user_handler, temp_dir):
        """Test that agent directory is created"""
        params = {
            "agent_id": "test_new_agent",
            "name": "Test Agent"
        }
        result = create_user_handler.handle(params)

        agent_dir = temp_dir / "agent-team" / "test_new_agent"
        assert agent_dir.exists()


class TestHandlerIntegration:
    """Handler integration test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_bash_then_memory(self, temp_dir):
        """Test bash command followed by memory write"""
        config_manager = ConfigManager(temp_dir)
        bash_handler = BashHandler(config_manager, "test")
        memory_handler = MemoryHandler(config_manager, "test")

        # Execute bash command
        bash_result = bash_handler.handle({"command": "echo test"})
        assert bash_result["status"] == "success"

        # Write result to memory
        memory_result = memory_handler.handle({
            "action": "write",
            "memory_type": "short_term",
            "content": {"bash_output": bash_result.get("result", {})}
        })
        assert memory_result["status"] == "success"

    def test_chat_then_heart(self, temp_dir):
        """Test chat followed by heart introspection"""
        config_manager = ConfigManager(temp_dir)
        chat_handler = ChatHandler(config_manager, "test")
        heart_handler = HeartHandler(config_manager, "test")

        # Send chat message
        chat_result = chat_handler.handle({
            "action": "send",
            "agent_id": "test",
            "message": "Hello"
        })
        assert chat_result["status"] == "success"

        # Introspect
        heart_result = heart_handler.handle({
            "trigger": "manual",
            "focus": "status"
        })
        assert heart_result["status"] == "success"
