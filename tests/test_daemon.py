"""Tests for Agent Daemon"""

import pytest
import time
import tempfile
from pathlib import Path

from mul_agent.brain.daemon import AgentDaemon, AgentState, create_daemon, ScheduledTask
from mul_agent.brain.config_manager import ConfigManager


class TestAgentDaemon:
    """Agent Daemon test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        import shutil
        shutil.rmtree(temp_path)

    @pytest.fixture
    def daemon(self, temp_dir):
        """Create daemon instance"""
        return create_daemon(temp_dir, idle_timeout=2, grow_interval=3600)

    def test_daemon_creation(self, daemon):
        """Test daemon can be created"""
        assert daemon is not None
        assert daemon.state == AgentState.WORKING

    def test_record_activity(self, daemon):
        """Test activity recording"""
        daemon.record_activity()
        assert daemon.state == AgentState.WORKING
        assert daemon.last_activity <= time.time()

    def test_idle_timeout(self, daemon):
        """Test idle timeout triggers rest"""
        # Don't record activity, wait for idle timeout
        time.sleep(2.5)

        # Manually check idle
        assert daemon._check_idle() is True

    def test_force_rest(self, daemon):
        """Test force rest"""
        daemon.force_rest()
        assert daemon.state == AgentState.RESTING

    def test_force_work(self, daemon):
        """Test force work"""
        daemon.force_rest()
        daemon.force_work()
        assert daemon.state == AgentState.WORKING

    def test_add_scheduled_task(self, daemon):
        """Test adding scheduled task"""
        task_id = daemon.add_scheduled_task(
            name="test task",
            action="heart",
            params={"trigger": "test"},
            interval=60
        )

        assert task_id is not None
        assert len(daemon.scheduled_tasks) == 1
        assert task_id in daemon.scheduled_tasks

    def test_remove_scheduled_task(self, daemon):
        """Test removing scheduled task"""
        task_id = daemon.add_scheduled_task(
            name="test task",
            action="heart",
            params={},
            interval=60
        )

        assert daemon.remove_scheduled_task(task_id) is True
        assert len(daemon.scheduled_tasks) == 0

    def test_list_scheduled_tasks(self, daemon):
        """Test listing scheduled tasks"""
        daemon.add_scheduled_task("task1", "heart", {}, 60)
        daemon.add_scheduled_task("task2", "bash", {"command": "echo test"}, 120)

        tasks = daemon.list_scheduled_tasks()
        assert len(tasks) == 2
        assert tasks[0]["name"] == "task1"
        assert tasks[1]["name"] == "task2"

    def test_default_growth_task(self, daemon):
        """Test adding default growth task"""
        daemon.add_default_growth_task()

        tasks = daemon.list_scheduled_tasks()
        growth_tasks = [t for t in tasks if t["name"] == "自我成长"]
        assert len(growth_tasks) == 1
        assert growth_tasks[0]["action"] == "heart"

    def test_get_status(self, daemon):
        """Test getting daemon status"""
        daemon.add_default_growth_task()

        status = daemon.get_status()
        assert status["state"] == "working"
        assert status["idle_time"] >= 0
        assert status["scheduled_tasks_count"] == 1

    def test_daemon_start_stop(self, daemon):
        """Test daemon can start and stop"""
        daemon.start()
        assert daemon._running is True

        daemon.stop()
        assert daemon._running is False

    def test_state_change_callback(self, daemon):
        """Test state change callback"""
        changes = []

        def on_change(old, new):
            changes.append((old.value, new.value))

        daemon.on_state_change = on_change

        daemon.force_rest()
        assert len(changes) == 1
        assert changes[0] == ("working", "resting")

    def test_daemon_loop_transitions_to_rest(self, temp_dir):
        """Test daemon automatically transitions to rest"""
        from mul_agent.brain.daemon import AgentDaemon
        config_manager = ConfigManager(temp_dir)
        daemon = AgentDaemon(config_manager, idle_timeout=1, check_interval=1)
        daemon.start()

        # Wait for idle timeout
        time.sleep(2)

        assert daemon.state == AgentState.RESTING

        daemon.stop()
