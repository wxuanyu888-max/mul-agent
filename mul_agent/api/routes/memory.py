"""Memory API routes"""

import json
from pathlib import Path
from typing import Any, Dict, List
from fastapi import APIRouter

router = APIRouter()

# Memory storage path
MEMORY_BASE = Path(__file__).parent.parent.parent.parent / "storage" / "memory"


def _parse_memory_file(filepath: Path) -> dict:
    """Parse a memory file (Markdown with YAML front matter)"""
    if not filepath.exists():
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse YAML front matter
        import re
        yaml_match = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)

        if not yaml_match:
            # Try JSON format
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return None

        metadata = {}
        yaml_content = yaml_match.group(1)
        for line in yaml_content.strip().split('\n'):
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                metadata[key.strip()] = value.strip()

        # Extract body (content after YAML front matter)
        body_start = yaml_match.end()
        body = content[body_start:].strip()

        # Remove markdown header if present
        if body.startswith("#"):
            lines = body.split('\n')
            body = '\n'.join(lines[1:]).strip()

        result = {
            "id": metadata.get("id", filepath.stem),
            "agent_id": metadata.get("agent_id", ""),
            "type": metadata.get("type", ""),
            "timestamp": metadata.get("timestamp", ""),
            "content": body
        }
        # 添加 handover 特有字段
        if "from_agent" in metadata:
            result["from_agent"] = metadata["from_agent"]
        if "to_agent" in metadata:
            result["to_agent"] = metadata["to_agent"]
        if "status" in metadata:
            result["status"] = metadata["status"]
        return result
    except Exception as e:
        print(f"Error parsing memory file {filepath}: {e}")
        return None


def _get_memory_path(memory_type: str, agent_id: str) -> Path:
    """Get the path for a memory type"""
    if memory_type == "short_term":
        return MEMORY_BASE / "short_term" / agent_id
    elif memory_type == "long_term":
        return MEMORY_BASE / "long_term" / agent_id
    elif memory_type == "handover":
        return MEMORY_BASE / "handover"
    else:
        return MEMORY_BASE / "short_term" / agent_id


@router.get("/memory/short-term")
async def get_short_term_memory(agent_id: str = "core_brain", limit: int = 20):
    """Get short-term memory"""
    path = _get_memory_path("short_term", agent_id)

    if not path.exists():
        return {"memories": [], "total": 0}

    memories = []
    files = sorted(path.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

    for f in files[:limit]:
        memory = _parse_memory_file(f)
        if memory:
            memories.append(memory)

    return {"memories": memories, "total": len(memories)}


@router.get("/memory/long-term")
async def get_long_term_memory(agent_id: str = "core_brain", limit: int = 20):
    """Get long-term memory"""
    path = _get_memory_path("long_term", agent_id)

    if not path.exists():
        return {"memories": [], "total": 0}

    memories = []
    files = sorted(path.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

    for f in files[:limit]:
        memory = _parse_memory_file(f)
        if memory:
            memories.append(memory)

    return {"memories": memories, "total": len(memories)}


@router.get("/memory/handover")
async def get_handover_memory(agent_id: str = "core_brain"):
    """Get handover memory"""
    path = _get_memory_path("handover", agent_id)

    if not path.exists():
        return {"memories": [], "total": 0}

    memories = []
    files = sorted(path.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

    for f in files:
        memory = _parse_memory_file(f)
        if memory:
            # Filter by agent_id if specified
            if memory.get("from_agent") == agent_id or memory.get("to_agent") == agent_id:
                memories.append(memory)

    return {"memories": memories, "total": len(memories)}


@router.post("/memory/write")
async def write_memory(
    content: str,
    agent_id: str = "core_brain",
    memory_type: str = "short_term",
    metadata: Dict[str, Any] = None
):
    """Write memory"""
    import hashlib
    from datetime import datetime

    path = _get_memory_path(memory_type, agent_id)
    path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()
    memory_id = hashlib.md5(f"{agent_id}:{timestamp}:{content}".encode()).hexdigest()[:16]

    # Create Markdown content
    lines = ["---"]
    lines.append(f"id: {memory_id}")
    lines.append(f"agent_id: {agent_id}")
    lines.append(f"type: {memory_type}")
    lines.append(f"timestamp: {timestamp}")
    lines.append("---\n")
    lines.append("# 记忆\n")
    lines.append(content)

    filepath = path / f"{memory_id}.md"
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return {"status": "success", "memory_id": memory_id, "path": str(filepath)}


@router.delete("/memory/{memory_id}")
async def delete_memory(memory_id: str, agent_id: str = "core_brain", memory_type: str = "short_term"):
    """Delete memory"""
    path = _get_memory_path(memory_type, agent_id)
    filepath = path / f"{memory_id}.md"

    if filepath.exists():
        filepath.unlink()
        return {"status": "success", "deleted": memory_id}

    return {"status": "not_found", "message": f"Memory {memory_id} not found"}
