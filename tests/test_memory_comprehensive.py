"""Comprehensive Tests for Memory System"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import datetime

from mul_agent.memory.memory import Memory


class TestMemoryInitialization:
    """Memory initialization test cases"""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests"""
        temp_path = tempfile.mkdtemp()
        yield Path(temp_path)
        shutil.rmtree(temp_path)

    def test_memory_creation(self, temp_dir):
        """Test Memory can be created"""
        config = {
            "storage_path": str(temp_dir)
        }
        memory = Memory(agent_id="test_agent", config=config)

        assert memory.agent_id == "test_agent"
        assert memory.config == config

    def test_memory_directories_created(self, temp_dir):
        """Test memory directories are created"""
        config = {"storage_path": str(temp_dir)}
        memory = Memory(agent_id="test_agent", config=config)

        # Check directories exist
        assert memory.short_term_path.exists()
        assert memory.long_term_path.exists()
        assert memory.handover_path.exists()


class TestMemoryWrite:
    """Memory write operation test cases"""

    @pytest.fixture
    def memory(self):
        """Create Memory instance for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        config = {"storage_path": str(temp_dir)}
        mem = Memory(agent_id="test_agent", config=config)
        yield mem
        shutil.rmtree(temp_dir)

    def test_write_short_term_memory(self, memory):
        """Test writing to short-term memory"""
        content = {
            "type": "conversation",
            "input": "Hello",
            "result": "Hi there"
        }
        memory_id = memory.write("short_term", content)

        assert memory_id is not None
        assert len(memory_id) > 0

    def test_write_long_term_memory(self, memory):
        """Test writing to long-term memory"""
        content = {
            "type": "skill",
            "name": "code_review",
            "description": "Best practices for code review"
        }
        memory_id = memory.write("long_term", content)

        assert memory_id is not None

    def test_write_dict_content(self, memory):
        """Test writing dictionary content"""
        content = {
            "key1": "value1",
            "key2": 123,
            "nested": {"a": 1, "b": 2}
        }
        memory_id = memory.write("short_term", content)

        assert memory_id is not None
        # Verify content can be read back
        read_memory = memory.read("short_term", memory_id)
        assert read_memory is not None

    def test_write_list_content(self, memory):
        """Test writing list content"""
        content = ["item1", "item2", "item3"]
        memory_id = memory.write("short_term", content)

        assert memory_id is not None
        read_memory = memory.read("short_term", memory_id)
        assert read_memory is not None

    def test_write_string_content(self, memory):
        """Test writing string content"""
        content = "This is a simple string memory"
        memory_id = memory.write("short_term", content)

        assert memory_id is not None
        read_memory = memory.read("short_term", memory_id)
        assert read_memory is not None

    def test_write_generates_unique_id(self, memory):
        """Test that each write generates unique ID"""
        content1 = {"data": "first"}
        content2 = {"data": "second"}

        id1 = memory.write("short_term", content1)
        id2 = memory.write("short_term", content2)

        assert id1 != id2


class TestMemoryRead:
    """Memory read operation test cases"""

    @pytest.fixture
    def memory(self):
        """Create Memory instance for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        config = {"storage_path": str(temp_dir)}
        mem = Memory(agent_id="test_agent", config=config)
        yield mem
        shutil.rmtree(temp_dir)

    def test_read_latest_short_term(self, memory):
        """Test reading latest short-term memory"""
        content = {"message": "Test message"}
        written_id = memory.write("short_term", content)

        read_memory = memory.read("short_term")
        assert read_memory is not None
        assert read_memory["id"] == written_id

    def test_read_latest_long_term(self, memory):
        """Test reading latest long-term memory"""
        content = {"knowledge": "Important fact"}
        written_id = memory.write("long_term", content)

        read_memory = memory.read("long_term")
        assert read_memory is not None
        assert read_memory["id"] == written_id

    def test_read_specific_memory(self, memory):
        """Test reading specific memory by ID"""
        content = {"unique": "data"}
        written_id = memory.write("short_term", content)

        read_memory = memory.read("short_term", written_id)
        assert read_memory is not None
        assert read_memory["id"] == written_id

    def test_read_nonexistent(self, memory):
        """Test reading nonexistent memory"""
        result = memory.read("short_term", "nonexistent_id")
        assert result is None

    def test_read_metadata(self, memory):
        """Test reading memory metadata"""
        content = {"data": "test"}
        memory_id = memory.write("short_term", content)

        read_memory = memory.read("short_term", memory_id)
        assert read_memory is not None
        assert "id" in read_memory
        assert "agent_id" in read_memory
        assert "type" in read_memory
        assert "timestamp" in read_memory


class TestMemoryUpdate:
    """Memory update operation test cases"""

    @pytest.fixture
    def memory(self):
        """Create Memory instance for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        config = {"storage_path": str(temp_dir)}
        mem = Memory(agent_id="test_agent", config=config)
        yield mem
        shutil.rmtree(temp_dir)

    def test_update_short_term_memory(self, memory):
        """Test updating short-term memory"""
        original = {"data": "original"}
        memory_id = memory.write("short_term", original)

        updated = {"data": "updated", "new_field": "value"}
        result = memory.update(memory_id, updated)

        assert result is True
        read_memory = memory.read("short_term", memory_id)
        assert read_memory is not None
        assert "updated" in str(read_memory.get("content", ""))

    def test_update_long_term_memory(self, memory):
        """Test updating long-term memory"""
        original = {"knowledge": "old"}
        memory_id = memory.write("long_term", original)

        updated = {"knowledge": "new"}
        result = memory.update(memory_id, updated)

        assert result is True

    def test_update_nonexistent(self, memory):
        """Test updating nonexistent memory"""
        result = memory.update("nonexistent_id", {"data": "test"})
        assert result is False

    def test_update_preserves_metadata(self, memory):
        """Test that update preserves metadata"""
        original = {"data": "original"}
        memory_id = memory.write("short_term", original)

        # Get original timestamp
        original_memory = memory.read("short_term", memory_id)
        original_agent_id = original_memory["agent_id"]

        # Update
        memory.update(memory_id, {"data": "updated"})

        # Check metadata preserved
        updated_memory = memory.read("short_term", memory_id)
        assert updated_memory["agent_id"] == original_agent_id
        assert updated_memory["id"] == memory_id


class TestMemoryDelete:
    """Memory delete operation test cases"""

    @pytest.fixture
    def memory(self):
        """Create Memory instance for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        config = {"storage_path": str(temp_dir)}
        mem = Memory(agent_id="test_agent", config=config)
        yield mem
        shutil.rmtree(temp_dir)

    def test_delete_short_term_memory(self, memory):
        """Test deleting short-term memory"""
        content = {"data": "to_delete"}
        memory_id = memory.write("short_term", content)

        result = memory.delete(memory_id)
        assert result is True

        # Verify deleted
        read_memory = memory.read("short_term", memory_id)
        assert read_memory is None

    def test_delete_long_term_memory(self, memory):
        """Test deleting long-term memory"""
        content = {"knowledge": "to_delete"}
        memory_id = memory.write("long_term", content)

        result = memory.delete(memory_id)
        assert result is True

    def test_delete_nonexistent(self, memory):
        """Test deleting nonexistent memory"""
        result = memory.delete("nonexistent_id")
        assert result is False


class TestMemoryList:
    """Memory list operation test cases"""

    @pytest.fixture
    def memory(self):
        """Create Memory instance for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        config = {"storage_path": str(temp_dir)}
        mem = Memory(agent_id="test_agent", config=config)
        yield mem
        shutil.rmtree(temp_dir)

    def test_list_short_term_memories(self, memory):
        """Test listing short-term memories"""
        # Write multiple memories
        for i in range(5):
            memory.write("short_term", {"index": i})

        memories = memory.list_memories("short_term")
        assert len(memories) == 5

    def test_list_long_term_memories(self, memory):
        """Test listing long-term memories"""
        # Write multiple memories
        for i in range(3):
            memory.write("long_term", {"knowledge": i})

        memories = memory.list_memories("long_term")
        assert len(memories) == 3

    def test_list_with_limit(self, memory):
        """Test listing with limit"""
        # Write more than limit
        for i in range(10):
            memory.write("short_term", {"index": i})

        memories = memory.list_memories("short_term", limit=5)
        assert len(memories) == 5

    def test_list_empty(self, memory):
        """Test listing empty memory"""
        memories = memory.list_memories("short_term")
        assert len(memories) == 0

    def test_list_sorted_by_recency(self, memory):
        """Test that listing returns memories sorted by recency"""
        # Write memories in order
        for i in range(5):
            memory.write("short_term", {"index": i})

        memories = memory.list_memories("short_term")

        # Most recent should be first
        assert memories[0]["content"] == {"index": 4}


class TestMemorySearch:
    """Memory search operation test cases"""

    @pytest.fixture
    def memory(self):
        """Create Memory instance for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        config = {"storage_path": str(temp_dir)}
        mem = Memory(agent_id="test_agent", config=config)
        yield mem
        shutil.rmtree(temp_dir)

    def test_search_exact_match(self, memory):
        """Test search with exact match"""
        memory.write("short_term", {"content": "Python programming"})
        memory.write("short_term", {"content": "Java programming"})
        memory.write("short_term", {"content": "JavaScript frameworks"})

        results = memory.search("Python")
        assert len(results) > 0
        assert results[0]["relevance_score"] >= 100

    def test_search_partial_match(self, memory):
        """Test search with partial match"""
        memory.write("short_term", {"content": "Error handling best practices"})
        memory.write("short_term", {"content": "Database connection pooling"})

        results = memory.search("error")
        assert len(results) > 0

    def test_search_across_types(self, memory):
        """Test search across all memory types"""
        memory.write("short_term", {"content": "Quick note"})
        memory.write("long_term", {"content": "Important knowledge"})
        memory.write("short_term", {"content": "Another note"})

        results = memory.search("note")
        # Should find memories from short_term
        assert len(results) >= 2

    def test_search_with_limit(self, memory):
        """Test search with result limit"""
        for i in range(10):
            memory.write("short_term", {"content": f"Test item {i}"})

        results = memory.search("Test", limit=5)
        assert len(results) <= 5

    def test_search_no_results(self, memory):
        """Test search with no matching results"""
        memory.write("short_term", {"content": "Python code"})
        memory.write("long_term", {"content": "Java code"})

        results = memory.search("nonexistent_keyword_xyz")
        assert len(results) == 0

    def test_search_relevance_scoring(self, memory):
        """Test search relevance scoring"""
        memory.write("short_term", {"content": "Python programming language"})
        memory.write("short_term", {"content": "Just mentioning python"})

        results = memory.search("Python programming")

        # First result should have higher score (exact match)
        assert results[0]["relevance_score"] > results[1]["relevance_score"]

    def test_search_metadata(self, memory):
        """Test search includes metadata"""
        content = {"topic": "API design", "details": "REST best practices"}
        memory.write("long_term", content)

        results = memory.search("API")
        assert len(results) > 0
        assert "memory_type" in results[0]
        assert "relevance_score" in results[0]


class TestMemoryHandover:
    """Memory handover operation test cases"""

    @pytest.fixture
    def memory(self):
        """Create Memory instance for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        config = {"storage_path": str(temp_dir)}
        mem = Memory(agent_id="test_agent", config=config)
        yield mem
        shutil.rmtree(temp_dir)

    def test_create_handover(self, memory):
        """Test creating handover document"""
        content = {
            "task": "Complete the feature",
            "context": "User requested changes",
            "next_steps": ["Review code", "Write tests"]
        }

        handover_id = memory.create_handover(
            from_agent="teacher",
            to_agent="student",
            content=content
        )

        assert handover_id is not None
        assert "handover" in handover_id
        assert "teacher" in handover_id
        assert "student" in handover_id

    def test_read_handover(self, memory):
        """Test reading handover document"""
        content = {"task": "Test task"}
        handover_id = memory.create_handover(
            from_agent="agent_a",
            to_agent="agent_b",
            content=content
        )

        read_handover = memory.read_handover(handover_id)
        assert read_handover is not None
        assert read_handover["from_agent"] == "agent_a"
        assert read_handover["to_agent"] == "agent_b"
        assert read_handover["status"] == "pending"

    def test_list_handovers(self, memory):
        """Test listing handover documents"""
        # Create multiple handovers
        memory.create_handover("a1", "b1", {"task": "1"})
        memory.create_handover("a2", "b2", {"task": "2"})
        memory.create_handover("a3", "b3", {"task": "3"})

        handovers = memory.list_handoffs()
        assert len(handovers) == 3

    def test_list_handovers_filtered(self, memory):
        """Test listing handovers with filter"""
        memory.create_handover("agent_x", "agent_y", {"task": "1"})
        memory.create_handover("agent_x", "agent_z", {"task": "2"})
        memory.create_handover("agent_a", "agent_x", {"task": "3"})

        # Filter by from_agent
        handovers = memory.list_handoffs(agent_id="agent_x")
        assert len(handovers) == 3  # All handovers involving agent_x


class TestMemoryGetRecent:
    """Memory get_recent operation test cases"""

    @pytest.fixture
    def memory(self):
        """Create Memory instance for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        config = {"storage_path": str(temp_dir)}
        mem = Memory(agent_id="test_agent", config=config)
        yield mem
        shutil.rmtree(temp_dir)

    def test_get_recent_all_types(self, memory):
        """Test getting recent memories from all types"""
        memory.write("short_term", {"type": "short"})
        memory.write("long_term", {"type": "long"})

        recent = memory.get_recent(limit=10)
        assert len(recent) >= 2

    def test_get_recent_specific_type(self, memory):
        """Test getting recent memories from specific type"""
        memory.write("short_term", {"data": "short1"})
        memory.write("short_term", {"data": "short2"})
        memory.write("long_term", {"data": "long1"})

        recent = memory.get_recent(memory_type="short_term", limit=10)
        assert len(recent) == 2

    def test_get_recent_sorted(self, memory):
        """Test that recent memories are sorted by timestamp"""
        memory.write("short_term", {"index": 1})
        memory.write("short_term", {"index": 2})
        memory.write("short_term", {"index": 3})

        recent = memory.get_recent(limit=10)
        # Most recent first
        assert recent[0]["content"] == {"index": 3}


class TestMemoryCleanup:
    """Memory cleanup operation test cases"""

    @pytest.fixture
    def memory(self):
        """Create Memory instance for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        config = {"storage_path": str(temp_dir)}
        mem = Memory(agent_id="test_agent", config=config)
        yield mem
        shutil.rmtree(temp_dir)

    def test_cleanup_short_term(self, memory):
        """Test cleaning up short-term memory"""
        # Write some memories
        for i in range(5):
            memory.write("short_term", {"index": i})

        # Cleanup (current implementation is basic)
        cleaned = memory.cleanup("short_term")
        assert isinstance(cleaned, int)


class TestMemoryFormatContent:
    """Memory _format_content helper method test cases"""

    @pytest.fixture
    def memory(self):
        """Create Memory instance for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        config = {"storage_path": str(temp_dir)}
        mem = Memory(agent_id="test_agent", config=config)
        yield mem
        shutil.rmtree(temp_dir)

    def test_format_dict_content(self, memory):
        """Test formatting dictionary content"""
        content = {"key1": "value1", "key2": "value2"}
        formatted = memory._format_content(content)

        assert "**key1**" in formatted
        assert "**key2**" in formatted
        assert "value1" in formatted
        assert "value2" in formatted

    def test_format_list_content(self, memory):
        """Test formatting list content"""
        content = ["item1", "item2", "item3"]
        formatted = memory._format_content(content)

        assert "- item1" in formatted
        assert "- item2" in formatted
        assert "- item3" in formatted

    def test_format_string_content(self, memory):
        """Test formatting string content"""
        content = "Plain text"
        formatted = memory._format_content(content)

        assert formatted == "Plain text"


class TestMemoryParseMdFile:
    """Memory _parse_md_file helper method test cases"""

    @pytest.fixture
    def memory(self):
        """Create Memory instance for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        config = {"storage_path": str(temp_dir)}
        mem = Memory(agent_id="test_agent", config=config)
        yield mem
        shutil.rmtree(temp_dir)

    def test_parse_valid_md_file(self, memory):
        """Test parsing valid markdown file"""
        content = """---
id: test123
agent_id: test_agent
type: short_term
timestamp: 2024-01-01T00:00:00
---

# 记忆

This is the content
"""
        filepath = memory.short_term_path / "test123.md"
        filepath.write_text(content)

        parsed = memory._parse_md_file(filepath)
        assert parsed is not None
        assert parsed["id"] == "test123"
        assert parsed["agent_id"] == "test_agent"
        assert parsed["type"] == "short_term"
        assert "This is the content" in parsed["content"]

    def test_parse_nonexistent_file(self, memory):
        """Test parsing nonexistent file"""
        filepath = memory.short_term_path / "nonexistent.md"
        result = memory._parse_md_file(filepath)
        assert result is None

    def test_parse_invalid_md_file(self, memory):
        """Test parsing invalid markdown file"""
        content = "No YAML front matter"
        filepath = memory.short_term_path / "invalid.md"
        filepath.write_text(content)

        parsed = memory._parse_md_file(filepath)
        assert parsed is None

    def test_parse_handover_file(self, memory):
        """Test parsing handover markdown file"""
        content = """---
id: handover123
from_agent: agent_a
to_agent: agent_b
type: handover
timestamp: 2024-01-01T00:00:00
status: pending
---

# 交接文档

Handover content
"""
        filepath = memory.handover_path / "handover123.md"
        filepath.write_text(content)

        parsed = memory._parse_md_file(filepath)
        assert parsed is not None
        assert parsed["from_agent"] == "agent_a"
        assert parsed["to_agent"] == "agent_b"
        assert parsed["status"] == "pending"


class TestMemoryIntegration:
    """Memory integration test cases"""

    @pytest.fixture
    def memory(self):
        """Create Memory instance for tests"""
        temp_dir = Path(tempfile.mkdtemp())
        config = {"storage_path": str(temp_dir)}
        mem = Memory(agent_id="integration_test_agent", config=config)
        yield mem
        shutil.rmtree(temp_dir)

    def test_full_workflow(self, memory):
        """Test complete memory workflow"""
        # Write memories
        short_id = memory.write("short_term", {"type": "conversation", "data": "Hello"})
        long_id = memory.write("long_term", {"type": "knowledge", "data": "Important"})

        # Read back
        short_memory = memory.read("short_term", short_id)
        long_memory = memory.read("long_term", long_id)

        assert short_memory is not None
        assert long_memory is not None

        # Search
        search_results = memory.search("Hello")
        assert len(search_results) > 0

        # List
        all_short = memory.list_memories("short_term")
        assert len(all_short) >= 1

        # Update
        memory.update(short_id, {"type": "conversation", "data": "Updated Hello"})
        updated = memory.read("short_term", short_id)
        assert "Updated Hello" in str(updated.get("content", ""))

        # Delete
        memory.delete(long_id)
        deleted = memory.read("long_term", long_id)
        assert deleted is None
