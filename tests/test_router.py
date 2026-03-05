"""Tests for Router"""

import pytest
import tempfile
import shutil
from pathlib import Path

from mul_agent.brain.router import Router
from mul_agent.brain.config_manager import ConfigManager


class TestRouter:
    """Router test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def router(self, temp_dir):
        """Create Router instance"""
        config_manager = ConfigManager(temp_dir)
        return Router(config_manager)

    def test_dispatch_valid_route(self, router):
        """Test dispatching to a valid route"""
        result = router.dispatch("heart", {"trigger": "manual"})

        assert result["status"] == "success"
        assert result["route"] == "heart"

    def test_dispatch_bash_route(self, router):
        """Test dispatching to bash route"""
        result = router.dispatch("bash", {"command": "echo test"})

        assert result["status"] == "success"
        assert result["route"] == "bash"

    def test_dispatch_unknown_route(self, router):
        """Test dispatching to unknown route"""
        result = router.dispatch("unknown_route", {})

        assert result["status"] == "error"
        assert "Unknown route" in result["message"]

    def test_list_routes(self, router):
        """Test listing available routes"""
        routes = router.list_routes()

        assert len(routes) > 0
        route_names = [r["name"] for r in routes]
        assert "create_user" in route_names
        assert "bash" in route_names
        assert "heart" in route_names
        assert "memory" in route_names
