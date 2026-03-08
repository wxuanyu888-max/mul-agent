"""Tests for Brain core logic"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from mul_agent.brain.brain import Brain, BrainState
from mul_agent.brain.config_manager import ConfigManager


class TestBrainState:
    """BrainState test cases"""

    def test_init(self):
        """Test BrainState initialization"""
        state = BrainState("test_agent")

        assert state.agent_id == "test_agent"
        assert state.max_history_length == 100
        assert state.context["agent_id"] == "test_agent"
        assert state.context["history"] == []
        assert state.get_session_id() is not None

    def test_add_to_history(self):
        """Test adding to history"""
        state = BrainState("test_agent")
        state.add_to_history("user", "Hello")

        assert len(state.get_history()) == 1
        assert state.get_history()[0]["role"] == "user"
        assert state.get_history()[0]["content"] == "Hello"

    def test_trim_history(self):
        """Test history trimming"""
        state = BrainState("test_agent", max_history_length=5)

        # Add more than max
        for i in range(10):
            state.add_to_history("user", f"Message {i}")

        state.trim_history()
        # Should keep first 2 + max_history_length
        assert len(state.get_history()) == 7  # 2 + 5

    def test_get_history(self):
        """Test getting history"""
        state = BrainState("test_agent")
        state.add_to_history("user", "Hello")
        state.add_to_history("assistant", "Hi")

        history = state.get_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"


class TestBrainInitialization:
    """Brain initialization test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_brain_creation(self, temp_dir):
        """Test Brain can be created"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        assert brain.agent_id == "core_brain"
        assert brain.config_manager == config_manager
        assert brain.router is not None
        assert brain.memory is not None
        assert brain.llm is not None

    def test_brain_state_tracking(self, temp_dir):
        """Test Brain state tracking"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        assert brain._current_route is None
        assert brain._start_time is None

    def test_brain_capabilities_extraction(self, temp_dir):
        """Test capability extraction from config"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        capabilities = brain._extract_capabilities()
        # core_brain should have planning/coordination capabilities
        assert isinstance(capabilities, list)


class TestBrainIntentRecognition:
    """Brain intent recognition test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_empty_input(self, temp_dir):
        """Test empty input handling"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        action = brain._decide_action("")
        assert action["route"] == "response"
        assert "message" in action["params"]

    def test_bash_command_prefix(self, temp_dir):
        """Test bash command detection with prefix"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        test_cases = [
            "$ ls -la",
            "$ls",
            "bash echo test",
            "sudo apt update",
        ]

        for cmd in test_cases:
            action = brain._decide_action(cmd)
            assert action["route"] == "bash"
            assert "command" in action["params"]

    def test_bash_command_keywords(self, temp_dir):
        """Test bash command detection with keywords"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        test_cases = [
            "ls -la",
            "cd /tmp",
            "pwd",
            "cat file.txt",
            "grep pattern file",
            "find . -name test",
            "echo hello",
            "mkdir new_dir",
            "head -n 10 file",
            "tail -f log",
        ]

        for cmd in test_cases:
            action = brain._decide_action(cmd)
            assert action["route"] == "bash", f"Failed for: {cmd}"

    def test_greeting_patterns(self, temp_dir):
        """Test greeting detection"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        test_cases = [
            "你好",
            "Hello",
            "Hi there",
            "早上好",
            "下午好",
            "晚上好",
            "再见",
            "Bye",
        ]

        for greeting in test_cases:
            action = brain._decide_action(greeting)
            assert action["route"] == "uncertain", f"Failed for: {greeting}"

    def test_help_request(self, temp_dir):
        """Test help request detection"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        test_cases = [
            "help",
            "help me",
            "?",
            "帮助",
            "怎么用",
            "如何使用",
            "what can you do",
        ]

        for help_cmd in test_cases:
            action = brain._decide_action(help_cmd)
            assert action["route"] == "response"

    def test_create_agent_detection(self, temp_dir):
        """Test create agent detection"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        test_cases = [
            "Create a new agent",
            "New agent please",
            "创建一个 agent",
            "新建一个助手",
            "Add a coder agent",
            "Create team",
            "创建一个团队",
        ]

        for cmd in test_cases:
            action = brain._decide_action(cmd)
            assert action["route"] in ["create_user", "create_team"], f"Failed for: {cmd}"

    def test_memory_related(self, temp_dir):
        """Test memory related detection"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        test_cases = [
            "Show me my memory",
            "Remember this",
            "记住这件事",
            "Forget it",
            "Recall last conversation",
        ]

        for cmd in test_cases:
            action = brain._decide_action(cmd)
            assert action["route"] == "memory", f"Failed for: {cmd}"

    def test_heart_evolution(self, temp_dir):
        """Test heart/evolution detection"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        test_cases = [
            "heart",
            "reflect on yourself",
            "evolve",
            "自省",
            "反思",
            "进化",
            "改进一下",
        ]

        for cmd in test_cases:
            action = brain._decide_action(cmd)
            assert action["route"] == "heart", f"Failed for: {cmd}"

    def test_skill_execution(self, temp_dir):
        """Test skill execution detection"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        test_cases = [
            ("execute skill bash_executor command=ls", "bash_executor"),
            ("run skill code_review", "code_review"),
            ("skill execute test_runner", "execute"),  # Note: parser gets word after "skill"
        ]

        for cmd, expected_skill in test_cases:
            action = brain._decide_action(cmd)
            assert action["route"] == "skill", f"Failed for: {cmd}"
            assert action["params"].get("skill_id") == expected_skill, f"Failed for: {cmd}"

    def test_chat_with_agent(self, temp_dir):
        """Test chat with other agent detection"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        test_cases = [
            "和 coder 对话",
            "Find agent coder",
            "Tell agent reviewer",
            "Send message to writer",
        ]

        for cmd in test_cases:
            action = brain._decide_action(cmd)
            # Chat pattern requires specific regex match
            # "find agent", "tell agent", "send message" patterns
            assert action["route"] == "chat", f"Failed for: {cmd}"

    def test_fallback_uncertain(self, temp_dir):
        """Test fallback to uncertain route"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        # Complex query that doesn't match specific patterns
        action = brain._decide_action("How to improve my code quality?")
        assert action["route"] == "uncertain"


class TestBrainStateUpdates:
    """Brain state update test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_state_update_tracking(self, temp_dir):
        """Test state update tracking"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        # Before think
        assert brain._start_time is None
        assert brain._current_route is None

    @patch('mul_agent.brain.brain.httpx.AsyncClient')
    def test_update_state(self, mock_async_client, temp_dir):
        """Test state update method"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)
        brain._start_time = __import__('time').time()

        # This should not raise
        brain._update_state("working", "test action", {"key": "value"})


class TestBrainContextCompression:
    """Brain context compression test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_should_compress_context(self, temp_dir):
        """Test context compression decision"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        # Short history - should not compress
        context = {"history_length": 5}
        should_compress = brain.should_compress_context(context)
        assert isinstance(should_compress, bool)

    def test_compress_history(self, temp_dir):
        """Test history compression"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        # Add some history
        for i in range(20):
            brain.state.add_to_history("user", f"Message {i}")
            brain.state.add_to_history("assistant", f"Response {i}")

        # Compress - should not raise
        brain._compress_history()

        # History should be compressed
        assert len(brain.state.context["history"]) < 40


class TestBrainDelegation:
    """Brain delegation method test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_list_skills(self, temp_dir):
        """Test listing skills"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        skills = brain.list_skills()
        assert isinstance(skills, list)

    def test_list_commands(self, temp_dir):
        """Test listing commands"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        commands = brain.list_commands()
        assert isinstance(commands, list)

    def test_execute_command(self, temp_dir):
        """Test executing command"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        # Execute a valid command
        result = brain.execute_command("help")
        assert isinstance(result, dict)

    def test_list_available_agents(self, temp_dir):
        """Test listing available agents"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        result = brain.list_available_agents()
        assert isinstance(result, dict)
        assert "status" in result


class TestBrainEvolution:
    """Brain evolution test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_evolve(self, temp_dir):
        """Test evolve method"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        result = brain.evolve(focus="all")
        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] == "success"

    def test_apply_evolution(self, temp_dir):
        """Test apply evolution method"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        changes = [{"type": "update", "field": "personality", "value": "friendly"}]
        result = brain.apply_evolution(changes)

        assert result["status"] == "success"
        assert result["applied_count"] == 1


class TestBrainNetwork:
    """Brain network operation test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_send_message(self, temp_dir):
        """Test sending message to another agent"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        result = brain.send_message(
            to_agent="test_agent",
            content={"message": "Hello"}
        )
        assert isinstance(result, dict)
        assert "status" in result

    def test_check_messages(self, temp_dir):
        """Test checking messages"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        result = brain.check_messages()
        assert isinstance(result, dict)
        assert "status" in result
        assert "message_count" in result

    def test_find_specialist(self, temp_dir):
        """Test finding specialist agent"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        result = brain.find_specialist("coding")
        assert isinstance(result, dict)
        assert "status" in result

    def test_get_network_stats(self, temp_dir):
        """Test getting network stats"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        stats = brain.get_network_stats()
        assert isinstance(stats, dict)

    def test_broadcast_message(self, temp_dir):
        """Test broadcasting message"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        result = brain.broadcast_message(
            content={"announcement": "Hello everyone"}
        )
        assert isinstance(result, dict)
        assert "status" in result
        assert "broadcast_count" in result


class TestBrainContextAnalysis:
    """Brain context analysis test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_get_context_analysis(self, temp_dir):
        """Test getting context analysis"""
        config_manager = ConfigManager(temp_dir)
        brain = Brain("core_brain", config_manager)

        analysis = brain.get_context_analysis()
        assert isinstance(analysis, dict)
