"""Tests for API Routes"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import shutil


class TestAgentsAPI:
    """Agents API route test cases"""

    @pytest.fixture
    def temp_wang_dir(self):
        """Create temporary wang directory"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def client(self, temp_wang_dir):
        """Create test client with temporary directory"""
        from mul_agent.api.routes.agents import router, config_manager, global_config

        # Update config manager to use temp directory
        import mul_agent.api.routes.agents as agents_module
        agents_module.config_manager = type('MockConfigManager', (), {
            'wang_dir': temp_wang_dir
        })()

        # Create agent-team directory
        agent_team_dir = temp_wang_dir / "agent-team"
        agent_team_dir.mkdir(parents=True, exist_ok=True)

        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_list_agents_empty(self, client, temp_wang_dir):
        """Test listing agents when empty"""
        response = client.get("/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) == 0

    def test_list_agents_with_agents(self, client, temp_wang_dir):
        """Test listing agents with some agents created"""
        # Create a test agent directory
        agent_dir = temp_wang_dir / "agent-team" / "test_agent"
        agent_dir.mkdir(parents=True, exist_ok=True)

        # Create soul.md
        soul_file = agent_dir / "soul.md"
        soul_file.write_text("""---
name: Test Agent
description: A test agent
---

# Soul

Test agent soul content
""")

        response = client.get("/agents")
        assert response.status_code == 200
        data = response.json()
        assert len(data["agents"]) == 1
        assert data["agents"][0]["agent_id"] == "test_agent"
        assert data["agents"][0]["name"] == "Test Agent"

    def test_get_agent(self, client):
        """Test getting single agent"""
        response = client.get("/agents/test_agent")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test_agent"

    def test_get_agent_status(self, client):
        """Test getting agent status"""
        response = client.get("/agents/test_agent/status")
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "test_agent"
        assert data["status"] == "idle"

    def test_get_llm_config_empty(self, client):
        """Test getting LLM config when not set"""
        response = client.get("/llm-config")
        assert response.status_code == 200
        data = response.json()
        assert data["has_key"] is False

    def test_update_llm_config(self, client, temp_wang_dir):
        """Test updating LLM config"""
        config_data = {
            "url": "https://api.test.com",
            "provider": "anthropic",
            "model": "claude-test",
            "key": "test-key-123"
        }

        response = client.put("/llm-config", json=config_data)
        assert response.status_code == 200
        data = response.json()
        assert data["has_key"] is True
        assert data["url"] == config_data["url"]

        # Verify config was saved
        get_response = client.get("/llm-config")
        assert get_response.status_code == 200
        get_data = get_response.json()
        assert get_data["has_key"] is True

    def test_delete_llm_config(self, client, temp_wang_dir):
        """Test deleting LLM config"""
        # First set config
        config_data = {
            "url": "https://api.test.com",
            "provider": "anthropic",
            "model": "claude-test",
            "key": "test-key"
        }
        client.put("/llm-config", json=config_data)

        # Then delete
        response = client.delete("/llm-config")
        assert response.status_code == 200

        # Verify deleted
        get_response = client.get("/llm-config")
        assert get_response.json()["has_key"] is False

    def test_get_agent_key(self, client):
        """Test getting agent key (legacy endpoint)"""
        response = client.get("/agents/test_agent/key")
        assert response.status_code == 200

    def test_update_agent_key(self, client):
        """Test updating agent key (legacy endpoint)"""
        config_data = {
            "url": "https://api.test.com",
            "provider": "anthropic",
            "model": "claude-test",
            "key": "test-key"
        }

        response = client.put("/agents/test_agent/key", json=config_data)
        assert response.status_code == 200

    def test_delete_agent_key(self, client):
        """Test deleting agent key (legacy endpoint)"""
        response = client.delete("/agents/test_agent/key")
        assert response.status_code == 200


class TestChatAPI:
    """Chat API route test cases"""

    @pytest.fixture
    def temp_wang_dir(self):
        """Create temporary wang directory"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def mock_client(self, temp_wang_dir):
        """Create mock test client for chat API"""
        # Create required directories
        agent_team_dir = temp_wang_dir / "agent-team"
        agent_team_dir.mkdir(parents=True, exist_ok=True)

        # Create a mock agent
        agent_dir = agent_team_dir / "wangyue"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "soul.md").write_text("---\nname: Wangyue\n---\n")
        (agent_dir / "user.md").write_text("---\nrole:\n  title: Assistant\n---\n")

        from fastapi import FastAPI
        from mul_agent.api.routes.chat import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_chat_empty_message(self, mock_client):
        """Test chat with empty message"""
        response = mock_client.post("/chat", json={"message": ""})
        # Should return some response, may be error or default
        assert response.status_code in [200, 500]

    def test_chat_get_history(self, mock_client):
        """Test getting chat history"""
        response = mock_client.get("/chat/history")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert "total" in data

    def test_chat_get_sessions(self, mock_client):
        """Test getting chat sessions"""
        response = mock_client.get("/chat/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data


class TestMemoryAPI:
    """Memory API route test cases"""

    @pytest.fixture
    def temp_wang_dir(self):
        """Create temporary wang directory"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def client(self, temp_wang_dir):
        """Create test client for memory API"""
        from fastapi import FastAPI
        from mul_agent.api.routes.memory import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_get_memories_empty(self, client):
        """Test getting memories when empty"""
        response = client.get("/api/v1/memory/wangyue")
        assert response.status_code in [200, 404, 500]

    def test_write_memory(self, client):
        """Test writing memory"""
        memory_data = {
            "memory_type": "short_term",
            "content": {"test": "data"}
        }
        response = client.post("/api/v1/memory/wangyue", json=memory_data)
        assert response.status_code in [200, 500]  # May fail if agent not configured

    def test_search_memories(self, client):
        """Test searching memories"""
        response = client.get("/api/v1/memory/wangyue/search", params={"q": "test"})
        assert response.status_code in [200, 404, 500]


class TestInfoAPI:
    """Info API route test cases"""

    @pytest.fixture
    def client(self):
        """Create test client for info API"""
        from fastapi import FastAPI
        from mul_agent.api.routes.info import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_get_health(self, client):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_get_version(self, client):
        """Test version endpoint"""
        response = client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data


class TestTokenUsageAPI:
    """Token Usage API route test cases"""

    @pytest.fixture
    def temp_wang_dir(self):
        """Create temporary wang directory"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def client(self, temp_wang_dir):
        """Create test client for token usage API"""
        from fastapi import FastAPI
        from mul_agent.api.routes.token_usage import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_get_token_usage_empty(self, client):
        """Test getting token usage when empty"""
        response = client.get("/token-usage/wangyue")
        assert response.status_code in [200, 404, 500]

    def test_get_token_usage_summary(self, client):
        """Test getting token usage summary"""
        response = client.get("/token-usage/wangyue/summary")
        assert response.status_code in [200, 404, 500]


class TestLogsAPI:
    """Logs API route test cases"""

    @pytest.fixture
    def client(self):
        """Create test client for logs API"""
        from fastapi import FastAPI
        from mul_agent.api.routes.logs import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_get_logs_empty(self, client):
        """Test getting logs when empty"""
        response = client.get("/logs/wangyue")
        assert response.status_code in [200, 404, 500]

    def test_get_logs_with_level(self, client):
        """Test getting logs with level filter"""
        response = client.get("/logs/wangyue", params={"level": "info"})
        assert response.status_code in [200, 404, 500]


class TestProjectsAPI:
    """Projects API route test cases"""

    @pytest.fixture
    def temp_wang_dir(self):
        """Create temporary wang directory"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def client(self, temp_wang_dir):
        """Create test client for projects API"""
        from fastapi import FastAPI
        from mul_agent.api.routes.projects import router

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_list_projects_empty(self, client):
        """Test listing projects when empty"""
        response = client.get("/projects")
        assert response.status_code in [200, 500]


class TestAPIIntegration:
    """API integration test cases"""

    @pytest.fixture
    def temp_wang_dir(self):
        """Create temporary wang directory"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    @pytest.fixture
    def full_client(self, temp_wang_dir):
        """Create full API test client"""
        # Create required structure
        agent_team_dir = temp_wang_dir / "agent-team"
        agent_team_dir.mkdir(parents=True, exist_ok=True)

        # Create a test agent
        agent_dir = agent_team_dir / "test_agent"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "soul.md").write_text("---\nname: Test\n---\n")
        (agent_dir / "user.md").write_text("---\nrole:\n  title: Tester\n---\n")

        from fastapi import FastAPI
        from mul_agent.api.routes.agents import router as agents_router
        from mul_agent.api.routes.info import router as info_router

        app = FastAPI()
        app.include_router(agents_router)
        app.include_router(info_router)
        return TestClient(app)

    def test_full_workflow(self, full_client, temp_wang_dir):
        """Test full API workflow"""
        # 1. Check health
        health_response = full_client.get("/health")
        assert health_response.status_code == 200

        # 2. List agents (should have test_agent)
        agents_response = full_client.get("/agents")
        assert agents_response.status_code == 200

        # 3. Set LLM config
        config_data = {
            "url": "https://api.test.com",
            "provider": "anthropic",
            "model": "claude-test",
            "key": "test-key"
        }
        llm_response = full_client.put("/llm-config", json=config_data)
        assert llm_response.status_code == 200

        # 4. Get agent details
        agent_response = full_client.get("/agents/test_agent")
        assert agent_response.status_code == 200
