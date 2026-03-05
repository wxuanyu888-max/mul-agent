"""Tests for ConfigManager"""

import pytest
import tempfile
import shutil
from pathlib import Path

from mul_agent.brain.config_manager import ConfigManager


class TestConfigManager:
    """ConfigManager test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def config_manager(self, temp_dir):
        """Create ConfigManager instance"""
        return ConfigManager(temp_dir)

    def test_load_default_config(self, config_manager):
        """Test loading default configuration"""
        soul = config_manager.load("core_brain", "soul")

        assert soul["version"] == "1.0"
        assert soul["name"] == "core_brain"
        assert "core_traits" in soul

    def test_save_and_load_config(self, config_manager):
        """Test saving and loading configuration"""
        test_data = {
            "version": "1.0",
            "name": "test_agent",
            "custom_field": "test_value"
        }

        # Save config
        result = config_manager.save("test_agent", "soul", test_data)
        assert result is True

        # Load config
        loaded = config_manager.load("test_agent", "soul")
        assert loaded["name"] == "test_agent"
        assert loaded["custom_field"] == "test_value"

    def test_create_snapshot(self, config_manager):
        """Test snapshot creation"""
        # First save a config
        test_data = {"version": "1.0", "name": "test"}
        config_manager.save("test_agent", "soul", test_data)

        # Create snapshot
        snapshot_name = config_manager._create_snapshot("test_agent", "soul")
        assert snapshot_name is not None

        # List snapshots
        snapshots = config_manager.list_snapshots("test_agent")
        assert len(snapshots) > 0

    def test_restore_snapshot(self, config_manager):
        """Test snapshot restoration"""
        # First save - no snapshot created (file didn't exist before)
        original = {"version": "1.0", "name": "original"}
        config_manager.save("test_agent", "soul", original)

        # Second save - creates snapshot of original
        modified = {"version": "1.0", "name": "modified"}
        config_manager.save("test_agent", "soul", modified)

        # List snapshots - should have one now
        snapshots = config_manager.list_snapshots("test_agent")
        assert len(snapshots) > 0

        # Restore from snapshot
        snapshot_name = snapshots[0]["name"]
        result = config_manager.restore_snapshot(snapshot_name)
        assert result is True

        # Verify restored
        restored = config_manager.load("test_agent", "soul")
        assert restored["name"] == "original"

    def test_list_agents(self, config_manager):
        """Test listing agents"""
        # Save configs for different agents
        config_manager.save("agent1", "soul", {"version": "1.0"})
        config_manager.save("agent2", "soul", {"version": "1.0"})

        agents = config_manager.list_agents()
        assert "agent1" in agents
        assert "agent2" in agents

    def test_validate_config(self, config_manager):
        """Test configuration validation"""
        # Save config first
        config_manager.save("test_agent", "soul", {"version": "1.0"})
        config_manager.save("test_agent", "user", {"version": "1.0"})
        config_manager.save("test_agent", "skill", {"version": "1.0"})
        config_manager.save("test_agent", "memory", {"version": "1.0"})

        # Valid config
        result = config_manager.validate_config("test_agent")
        assert result["valid"] is True
        assert len(result["missing"]) == 0

        # Missing config - partial
        config_manager.save("partial_agent", "soul", {"version": "1.0"})
        result = config_manager.validate_config("partial_agent")
        assert result["valid"] is False
        assert len(result["missing"]) > 0
