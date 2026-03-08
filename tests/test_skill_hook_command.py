"""Tests for Skill, Hook, and Command Systems"""

import pytest
import tempfile
import shutil
from pathlib import Path

from mul_agent.skills.manager import SkillManager
from mul_agent.skills.base import BaseSkill
from mul_agent.hooks.manager import HookManager
from mul_agent.hooks.base import BaseHook, HookEvent
from mul_agent.commands.manager import CommandManager
from mul_agent.commands.base import BaseCommand
from mul_agent.brain.config_manager import ConfigManager


# ============================================================================
# Skill System Tests
# ============================================================================

class TestSkillManager:
    """SkillManager test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def skill_manager(self, temp_dir):
        """Create SkillManager instance"""
        config_manager = ConfigManager(temp_dir)
        return SkillManager(config_manager, agent_id="test_agent")

    def test_skill_manager_creation(self, skill_manager):
        """Test SkillManager can be created"""
        assert skill_manager is not None
        assert skill_manager.agent_id == "test_agent"

    def test_list_builtin_skills(self, skill_manager):
        """Test listing built-in skills"""
        skills = skill_manager.list_skills()
        assert isinstance(skills, list)
        # Should have some built-in skills loaded
        skill_names = [s.get("skill_name", "") for s in skills]
        assert len(skill_names) > 0

    def test_search_skills(self, skill_manager):
        """Test searching skills"""
        results = skill_manager.search_skills("bash")
        assert isinstance(results, list)

    def test_execute_skill(self, skill_manager):
        """Test executing a skill"""
        # Try to execute bash skill if available
        skills = skill_manager.list_skills()
        if skills:
            skill_id = skills[0].get("skill_id")
            if skill_id:
                # Some skills may require specific params
                # Just test that execution doesn't crash
                try:
                    result = skill_manager.execute_skill(skill_id)
                    assert result is not None
                except ValueError as e:
                    # Expected for skills requiring params
                    assert "Invalid parameters" in str(e) or "requires" in str(e).lower()

    def test_get_skill(self, skill_manager):
        """Test getting a specific skill"""
        skills = skill_manager.list_skills()
        if skills:
            skill_id = skills[0].get("skill_id")
            skill = skill_manager.get_skill(skill_id)
            assert skill is not None

    def test_get_nonexistent_skill(self, skill_manager):
        """Test getting nonexistent skill"""
        skill = skill_manager.get_skill("nonexistent_skill_xyz")
        assert skill is None

    def test_disable_enable_skill(self, skill_manager):
        """Test disabling and enabling skills"""
        skills = skill_manager.list_skills()
        if skills:
            skill_id = skills[0].get("skill_id")

            # Disable
            result = skill_manager.disable_skill(skill_id)
            assert result is True

            # Enable
            result = skill_manager.enable_skill(skill_id)
            assert result is True

    def test_to_dict(self, skill_manager):
        """Test converting skill manager to dict"""
        result = skill_manager.to_dict()
        assert isinstance(result, dict)
        assert "agent_id" in result
        assert "skills_count" in result
        assert "skills" in result


class TestCustomSkill(BaseSkill):
    """Custom test skill for testing"""

    skill_id = "test_custom_skill"
    skill_name = "Test Skill"
    skill_description = "A test skill for unit testing"
    skill_tags = ["test", "demo"]
    skill_version = "1.0.0"
    requires_confirmation = False
    enabled = True

    def initialize(self) -> bool:
        return True

    def validate_params(self, params: dict) -> bool:
        return True

    def execute(self, **kwargs) -> dict:
        return {"status": "success", "message": "Test skill executed", "params": kwargs}


class TestSkillRegistration:
    """Skill registration test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_register_custom_skill(self, temp_dir):
        """Test registering a custom skill"""
        config_manager = ConfigManager(temp_dir)
        manager = SkillManager(config_manager, "test")

        skill_id = manager.register_skill(TestCustomSkill)
        assert skill_id == "test_custom_skill"

    def test_register_skill_with_instance(self, temp_dir):
        """Test registering skill with pre-created instance"""
        config_manager = ConfigManager(temp_dir)
        manager = SkillManager(config_manager, "test")

        instance = TestCustomSkill(config_manager, "test")
        skill_id = manager.register_skill(TestCustomSkill, instance)
        assert skill_id == "test_custom_skill"

    def test_execute_registered_skill(self, temp_dir):
        """Test executing a registered custom skill"""
        config_manager = ConfigManager(temp_dir)
        manager = SkillManager(config_manager, "test")

        manager.register_skill(TestCustomSkill)
        result = manager.execute_skill("test_custom_skill", test_param="value")

        assert result["status"] == "success"
        assert result["params"]["test_param"] == "value"

    def test_search_custom_skill(self, temp_dir):
        """Test searching for custom skill"""
        config_manager = ConfigManager(temp_dir)
        manager = SkillManager(config_manager, "test")

        manager.register_skill(TestCustomSkill)
        results = manager.search_skills("test")

        assert len(results) > 0
        assert results[0]["skill_id"] == "test_custom_skill"

    def test_get_skill_by_tag(self, temp_dir):
        """Test getting skill by tag"""
        config_manager = ConfigManager(temp_dir)
        manager = SkillManager(config_manager, "test")

        manager.register_skill(TestCustomSkill)
        skills = manager.get_skill_by_tag("test")

        assert len(skills) > 0
        assert skills[0].skill_id == "test_custom_skill"

    def test_reload_all_skills(self, temp_dir):
        """Test reloading all skills"""
        config_manager = ConfigManager(temp_dir)
        manager = SkillManager(config_manager, "test")

        manager.register_skill(TestCustomSkill)
        initial_count = len(manager.list_skills())

        manager.reload_all()

        # Built-in skills should be reloaded
        assert len(manager.list_skills()) > 0


# ============================================================================
# Hook System Tests
# ============================================================================

class TestHookManager:
    """HookManager test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def hook_manager(self, temp_dir):
        """Create HookManager instance"""
        config_manager = ConfigManager(temp_dir)
        return HookManager(config_manager, agent_id="test_agent")

    def test_hook_manager_creation(self, hook_manager):
        """Test HookManager can be created"""
        assert hook_manager is not None
        assert hook_manager.agent_id == "test_agent"

    def test_list_hooks_empty(self, hook_manager):
        """Test listing hooks when empty"""
        hooks = hook_manager.list_hooks()
        assert isinstance(hooks, list)

    def test_register_hook(self, hook_manager):
        """Test registering a hook"""
        class TestHook(BaseHook):
            hook_id = "test_hook"

            def pre_tool_use(self, route: str, params: dict) -> dict:
                return params

        hook_id = hook_manager.register_hook(TestHook)
        assert hook_id is not None

    def test_trigger_pre_tool_use(self, hook_manager):
        """Test triggering pre_tool_use hooks"""
        class TestHook(BaseHook):
            hook_id = "test_pre_hook"

            def pre_tool_use(self, route: str, params: dict) -> dict:
                params["modified"] = True
                return params

        hook_manager.register_hook(TestHook)
        result = hook_manager.trigger_pre_tool_use("test_route", {"original": "data"})

        assert result.get("modified") is True

    def test_trigger_post_tool_use(self, hook_manager):
        """Test triggering post_tool_use hooks"""
        class TestHook(BaseHook):
            hook_id = "test_post_hook"

            def post_tool_use(self, route: str, params: dict, result: dict) -> dict:
                result["hook_applied"] = True
                return result

        hook_manager.register_hook(TestHook)
        result = hook_manager.trigger_post_tool_use("test_route", {}, {"original": "data"})

        assert result.get("result", {}).get("hook_applied") is True

    def test_trigger_session_start(self, hook_manager):
        """Test triggering session_start hooks"""
        class TestHook(BaseHook):
            hook_id = "test_session_start"

            def session_start(self, context: dict) -> dict:
                context["session_started"] = True
                return context

        hook_manager.register_hook(TestHook)
        result = hook_manager.trigger_session_start()

        assert result.get("session_started") is True

    def test_trigger_session_end(self, hook_manager):
        """Test triggering session_end hooks"""
        class TestHook(BaseHook):
            hook_id = "test_session_end"

            def session_end(self, context: dict) -> dict:
                context["session_ended"] = True
                return context

        hook_manager.register_hook(TestHook)
        result = hook_manager.trigger_session_end({"test": "data"})

        assert result.get("session_ended") is True

    def test_trigger_pre_message(self, hook_manager):
        """Test triggering pre_message hooks"""
        class TestHook(BaseHook):
            hook_id = "test_pre_message"

            def pre_message(self, context: dict) -> dict:
                context["user_input"] = "modified_" + context.get("user_input", "")
                return context

        hook_manager.register_hook(TestHook)
        result = hook_manager.trigger_hooks(HookEvent.PRE_MESSAGE, {"user_input": "hello"})

        assert result.get("user_input") == "modified_hello"


class TestCustomHook(BaseHook):
    """Custom test hook for testing"""

    hook_id = "test_custom_hook"

    def pre_tool_use(self, route: str, params: dict) -> dict:
        params["custom_hook_applied"] = True
        return params


class TestHookRegistration:
    """Hook registration test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_register_custom_hook(self, temp_dir):
        """Test registering a custom hook"""
        config_manager = ConfigManager(temp_dir)
        manager = HookManager(config_manager, "test")

        hook_id = manager.register_hook(TestCustomHook)
        assert hook_id is not None

    def test_list_registered_hooks(self, temp_dir):
        """Test listing registered hooks"""
        config_manager = ConfigManager(temp_dir)
        manager = HookManager(config_manager, "test")

        manager.register_hook(TestCustomHook)
        hooks = manager.list_hooks()

        assert len(hooks) >= 1


# ============================================================================
# Command System Tests
# ============================================================================

class TestCommandManager:
    """CommandManager test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def command_manager(self, temp_dir):
        """Create CommandManager instance"""
        config_manager = ConfigManager(temp_dir)
        return CommandManager(config_manager, agent_id="test_agent")

    def test_command_manager_creation(self, command_manager):
        """Test CommandManager can be created"""
        assert command_manager is not None
        assert command_manager.agent_id == "test_agent"

    def test_list_commands(self, command_manager):
        """Test listing commands"""
        commands = command_manager.list_commands()
        assert isinstance(commands, list)
        # Should have some built-in commands
        assert len(commands) > 0

    def test_execute_help_command(self, command_manager):
        """Test executing help command"""
        result = command_manager.execute("help", "")
        assert isinstance(result, dict)
        assert result.status.value in ["success", "error"]

    def test_execute_command_with_args(self, command_manager):
        """Test executing command with arguments"""
        # Try to execute a command that accepts args
        result = command_manager.execute("help", "test")
        assert isinstance(result, dict)

    def test_execute_nonexistent_command(self, command_manager):
        """Test executing nonexistent command"""
        result = command_manager.execute("nonexistent_command_xyz", "")
        assert result.status.value == "error"

    def test_execute_from_input(self, command_manager):
        """Test executing command from input string"""
        # Test with /help format
        result = command_manager.execute_from_input("/help")
        assert isinstance(result, dict)

        # Test with !help format
        result = command_manager.execute_from_input("!help")
        assert isinstance(result, dict)

    def test_execute_from_input_no_command_prefix(self, command_manager):
        """Test executing from input without command prefix"""
        result = command_manager.execute_from_input("just some text")
        # Should return not_found or similar
        assert result.status.value == "not_found"


class TestCustomCommand(BaseCommand):
    """Custom test command for testing"""

    command_id = "test_cmd"
    command_name = "test"
    command_description = "A test command"
    command_usage = "/test [args]"
    command_aliases = ["testcmd"]

    def execute(self, args: str = "") -> dict:
        return {
            "status": "success",
            "message": f"Test command executed with args: {args}"
        }


class TestCommandRegistration:
    """Command registration test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_register_custom_command(self, temp_dir):
        """Test registering a custom command"""
        config_manager = ConfigManager(temp_dir)
        manager = CommandManager(config_manager, "test")

        manager.register_command(TestCustomCommand)
        commands = manager.list_commands()

        cmd_names = [c.get("command_name", "") for c in commands]
        assert "test" in cmd_names

    def test_execute_registered_command(self, temp_dir):
        """Test executing a registered custom command"""
        config_manager = ConfigManager(temp_dir)
        manager = CommandManager(config_manager, "test")

        manager.register_command(TestCustomCommand)
        result = manager.execute("test", "arg1 arg2")

        assert result.status.value == "success"
        assert "Test command executed" in str(result.data)

    def test_execute_command_by_alias(self, temp_dir):
        """Test executing command by alias"""
        config_manager = ConfigManager(temp_dir)
        manager = CommandManager(config_manager, "test")

        manager.register_command(TestCustomCommand)
        result = manager.execute("testcmd", "")

        assert result.status.value == "success"


# ============================================================================
# System Integration Tests
# ============================================================================

class TestSkillHookCommandIntegration:
    """Integration tests for Skill, Hook, Command systems"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_skill_and_hook_together(self, temp_dir):
        """Test skill and hook working together"""
        config_manager = ConfigManager(temp_dir)
        skill_manager = SkillManager(config_manager, "test")
        hook_manager = HookManager(config_manager, "test")

        # Register hook that modifies params
        class ModifierHook(BaseHook):
            hook_id = "modifier"

            def pre_tool_use(self, route: str, params: dict) -> dict:
                params["hooked"] = True
                return params

        hook_manager.register_hook(ModifierHook)

        # Register skill
        skill_manager.register_skill(TestCustomSkill)

        # Pre-tool hook should be triggered
        result = hook_manager.trigger_pre_tool_use("skill", {"skill_id": "test_custom_skill"})
        assert result.get("hooked") is True

    def test_command_and_skill_together(self, temp_dir):
        """Test command and skill working together"""
        config_manager = ConfigManager(temp_dir)
        skill_manager = SkillManager(config_manager, "test")
        command_manager = CommandManager(config_manager, "test")

        # Register both
        skill_manager.register_skill(TestCustomSkill)
        command_manager.register_command(TestCustomCommand)

        # Both should be listable
        skills = skill_manager.list_skills()
        commands = command_manager.list_commands()

        assert len(skills) > 0
        assert len(commands) > 0

    def test_full_workflow(self, temp_dir):
        """Test full workflow with all three systems"""
        config_manager = ConfigManager(temp_dir)
        skill_manager = SkillManager(config_manager, "test")
        hook_manager = HookManager(config_manager, "test")
        command_manager = CommandManager(config_manager, "test")

        # 1. Register hook for logging
        class LogHook(BaseHook):
            hook_id = "logger"
            log = []

            def pre_tool_use(self, route: str, params: dict) -> dict:
                self.log.append(f"pre:{route}")
                return params

            def post_tool_use(self, route: str, params: dict, result: dict) -> dict:
                self.log.append(f"post:{route}")
                return result

        hook_manager.register_hook(LogHook)

        # 2. Register custom command
        command_manager.register_command(TestCustomCommand)

        # 3. Register custom skill
        skill_manager.register_skill(TestCustomSkill)

        # 4. Execute command
        cmd_result = command_manager.execute("test", "args")
        assert cmd_result.status.value == "success"

        # 5. Execute skill
        skill_result = skill_manager.execute_skill("test_custom_skill")
        assert skill_result["status"] == "success"

        # 6. Verify hooks were triggered
        assert len(LogHook.log) >= 2  # At least pre and post for skill
