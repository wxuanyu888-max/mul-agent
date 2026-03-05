"""Tests for BashExecutor"""

import pytest

from mul_agent.tools.bash_executor import BashExecutor, SafeBashExecutor


class TestBashExecutor:
    """BashExecutor test cases"""

    def test_execute_simple_command(self):
        """Test executing a simple command"""
        executor = BashExecutor(timeout=5)
        result = executor.execute("echo hello")

        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]
        assert result["success"] is True

    def test_execute_with_cwd(self):
        """Test executing command with custom working directory"""
        executor = BashExecutor(timeout=5, cwd="/tmp")
        result = executor.execute("pwd")

        assert result["exit_code"] == 0

    def test_command_timeout(self):
        """Test command timeout"""
        executor = BashExecutor(timeout=1)
        result = executor.execute("sleep 10")

        assert result["exit_code"] == -1
        assert "timed out" in result["stderr"]

    def test_invalid_command(self):
        """Test invalid command"""
        executor = BashExecutor(timeout=5)
        result = executor.execute("nonexistent_command_xyz")

        assert result["exit_code"] != 0

    def test_is_safe_wildcard_allowed(self):
        """Test safety check with wildcard"""
        executor = BashExecutor()
        assert executor.is_safe("rm -rf /", ["*"], []) is True

    def test_is_safe_forbidden(self):
        """Test safety check with forbidden commands"""
        executor = BashExecutor()
        assert executor.is_safe("rm -rf /", ["*"], ["rm -rf"]) is False

    def test_is_safe_allowed_list(self):
        """Test safety check with allowed list"""
        executor = BashExecutor()
        assert executor.is_safe("ls -la", ["ls", "cat", "echo"], []) is True
        assert executor.is_safe("rm file", ["ls", "cat", "echo"], []) is False


class TestSafeBashExecutor:
    """SafeBashExecutor test cases"""

    def test_default_forbidden(self):
        """Test default forbidden commands"""
        executor = SafeBashExecutor()

        # These should be forbidden by default
        assert executor.is_safe("rm -rf /", None, None) is False
        assert executor.is_safe("sudo su", None, None) is False
        assert executor.is_safe("dd if=/dev/zero", None, None) is False

    def test_custom_allowed(self):
        """Test custom allowed commands"""
        executor = SafeBashExecutor()
        assert executor.is_safe("ls", ["ls"], []) is True
