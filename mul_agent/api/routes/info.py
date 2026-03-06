"""Info API routes"""

from fastapi import APIRouter, Query
from pathlib import Path
from typing import Optional

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
AGENT_CONFIG_DIR = STORAGE_DIR / "agent_config"
PROJECTS_DIR = STORAGE_DIR / "projects"


def get_agent_config_dir(project_id: Optional[str] = None) -> Path:
    """Get agent config directory for a project or global"""
    if project_id:
        project_dir = PROJECTS_DIR / project_id
        if project_dir.exists():
            return project_dir / "agents"
    return AGENT_CONFIG_DIR


@router.get("/info/summary")
async def get_summary():
    """Get agent summary"""
    return {
        "total_runs": 0,
        "success": 0,
        "failed": 0,
        "error": 0,
        "avg_duration": 0,
        "route_stats": {}
    }


@router.get("/info/routes")
async def get_routes():
    """Get available routes"""
    return {
        "routes": [
            {"name": "bash", "description": "Execute shell command"},
            {"name": "chat", "description": "Chat with agent"},
            {"name": "memory", "description": "Memory management"},
            {"name": "heart", "description": "Self-reflection"},
            {"name": "response", "description": "Direct response"},
            {"name": "create_user", "description": "Create new agent"},
        ]
    }


@router.get("/info/runs")
async def get_runs(limit: int = 10):
    """Get recent runs"""
    return {"runs": []}


@router.get("/info/workflow/current")
async def get_current_workflow():
    """Get current workflow status"""
    return {
        "active": False,
        "phase": "idle",
        "sub_agents": [],
        "flow": []
    }


@router.get("/info/workflow/latest")
async def get_latest_workflow(limit: int = 5):
    """Get latest workflow runs"""
    return {"runs": []}


@router.get("/info/agent-team")
async def get_agent_team(project_id: Optional[str] = Query(None, description="Project ID to filter agents")):
    """Get all agents in the team"""
    agents = []
    active_sub_agents = {}

    config_dir = get_agent_config_dir(project_id)

    if config_dir.exists():
        for item in config_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                agent_id = item.name
                soul_file = item / "soul.md"
                user_file = item / "user.md"

                name = agent_id
                description = ""

                if soul_file.exists():
                    content = soul_file.read_text()
                    if "name: " in content:
                        name = content.split("name: ")[-1].split("\n")[0]
                    if "description: " in content:
                        description = content.split("description: ")[-1].split("\n")[0]

                agents.append({
                    "agent_id": agent_id,
                    "name": name,
                    "description": description,
                    "role": user_file.read_text() if user_file.exists() else "",
                    "project_id": project_id or "global"
                })

    return {
        "agents": agents,
        "active_sub_agents": active_sub_agents,
        "current_task": {
            "active": False,
            "input": None,
            "status": None
        }
    }


@router.get("/info/agent/{agent_id}/details")
async def get_agent_details(agent_id: str, project_id: Optional[str] = Query(None, description="Project ID")):
    """Get agent details"""
    import json
    from pathlib import Path

    config_dir = get_agent_config_dir(project_id)
    agent_path = config_dir / agent_id

    # Get current task from active workflow
    current_task = None
    sub_agents_list = []
    status = "idle"

    # Try to get active workflow state from logs
    log_dir = Path(__file__).parent.parent.parent.parent / "storage" / "logs"
    if log_dir.exists():
        log_files = sorted(log_dir.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)
        for log_file in log_files[:1]:  # Check latest log file
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    for line in reversed(f.readlines()[-100:]):  # Check last 100 lines
                        if line.strip():
                            log_entry = json.loads(line.strip())
                            if log_entry.get("source") == "Brain" and "输入:" in log_entry.get("message", ""):
                                status = "running"
                                current_task = {
                                    "task": log_entry["message"].replace("输入：", ""),
                                    "status": "running",
                                    "type": "user_input"
                                }
                                break
                            elif log_entry.get("source") == "SubAgent":
                                sub_agent_info = {
                                    "agent_id": log_entry.get("details", {}).get("sub_agent_id", "unknown"),
                                    "agent_type": log_entry.get("details", {}).get("sub_agent_type", "unknown"),
                                    "status": "running",
                                    "input": log_entry.get("message", "")[:200]
                                }
                                if sub_agent_info not in sub_agents_list:
                                    sub_agents_list.append(sub_agent_info)
            except Exception:
                continue

    if not agent_path.exists():
        # Return default for core_brain
        if agent_id == "core_brain":
            return {
                "agent_id": agent_id,
                "name": "Core Brain",
                "description": "Central coordinator",
                "role": "coordinator",
                "soul": "",
                "skill": "",
                "memory": "",
                "current_task": current_task,
                "sub_agents": sub_agents_list,
                "status": status,
                "project_id": project_id or "global"
            }
        return {
            "agent_id": agent_id,
            "name": agent_id,
            "description": "",
            "role": "",
            "soul": "",
            "skill": "",
            "memory": "",
            "current_task": current_task,
            "sub_agents": sub_agents_list,
            "status": status,
            "project_id": project_id or "global"
        }

    soul_file = agent_path / "soul.md"
    user_file = agent_path / "user.md"
    skill_file = agent_path / "skill.md"
    memory_file = agent_path / "memory.md"

    # Parse name from soul.md
    name = agent_id
    description = ""
    if soul_file.exists():
        content = soul_file.read_text()
        if "name: " in content:
            name = content.split("name: ")[-1].split("\n")[0]
        if "description: " in content:
            description = content.split("description: ")[-1].split("\n")[0]

    return {
        "agent_id": agent_id,
        "name": name,
        "description": description,
        "role": user_file.read_text() if user_file.exists() else "",
        "soul": soul_file.read_text() if soul_file.exists() else "",
        "skill": skill_file.read_text() if skill_file.exists() else "",
        "memory": memory_file.read_text() if memory_file.exists() else "",
        "current_task": current_task,
        "sub_agents": sub_agents_list,
        "status": status,
        "project_id": project_id or "global"
    }


@router.get("/info/agent/{agent_id}/loaded-docs")
async def get_loaded_docs(agent_id: str):
    """Get loaded documents for an agent"""
    from pathlib import Path

    # Get agent storage path
    storage_dir = Path(__file__).parent.parent.parent.parent / "storage" / "agents" / agent_id

    loaded_docs = {}
    doc_types = ["soul", "user", "skill", "memory"]

    if storage_dir.exists():
        for doc_type in doc_types:
            doc_path = storage_dir / f"{doc_type}.md"
            if doc_path.exists():
                content = doc_path.read_text(encoding="utf-8")
                loaded_docs[doc_type] = {
                    "content": content[:2000],  # Limit content size
                    "attributes": {
                        "size": doc_path.stat().st_size,
                        "modified": doc_path.stat().st_mtime
                    }
                }

    return {
        "agent_id": agent_id,
        "loaded_docs": loaded_docs,
        "doc_count": len(loaded_docs)
    }


@router.get("/info/interactions")
async def get_interactions(limit: int = 20):
    """Get agent interactions from logs"""
    import json
    from datetime import datetime

    log_dir = Path(__file__).parent.parent.parent.parent / "storage" / "logs"
    interactions = []

    if not log_dir.exists():
        return {"interactions": []}

    log_files = sorted(log_dir.glob("*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)

    for log_file in log_files[:3]:  # Check last 3 log files
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        log_entry = json.loads(line.strip())

                        # Extract interactions from SubAgent logs
                        if log_entry.get("source") == "SubAgent":
                            details = log_entry.get("details", {})
                            run_id = log_entry.get("run_id", log_entry.get("trace_id", ""))
                            timestamp_str = log_entry.get("datetime", "")

                            # Parse timestamp
                            try:
                                dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                timestamp = int(dt.timestamp())
                            except Exception:
                                timestamp = 0

                            interaction = {
                                "run_id": run_id,
                                "source": "core_brain",
                                "target": details.get("sub_agent_id", "unknown"),
                                "type": details.get("sub_agent_type", "unknown"),
                                "task": log_entry.get("message", "")[:200],
                                "status": "executing",
                                "timestamp": timestamp
                            }

                            # Avoid duplicates
                            if interaction not in interactions:
                                interactions.append(interaction)

                        # Also check for Router decisions showing task delegation
                        elif log_entry.get("source") == "Router":
                            details = log_entry.get("details", {})
                            route = details.get("route", "")
                            run_id = log_entry.get("run_id", log_entry.get("trace_id", ""))
                            timestamp_str = log_entry.get("datetime", "")

                            try:
                                dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                timestamp = int(dt.timestamp())
                            except Exception:
                                timestamp = 0

                            interaction = {
                                "run_id": run_id,
                                "source": "core_brain",
                                "target": route,
                                "type": "delegation",
                                "task": details.get("params", {}).get("command", log_entry.get("message", ""))[:200],
                                "status": "pending",
                                "timestamp": timestamp
                            }

                            if interaction not in interactions:
                                interactions.append(interaction)

        except Exception:
            continue

        if len(interactions) >= limit:
            break

    # Sort by timestamp (newest first) and limit
    interactions.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return {"interactions": interactions[:limit]}


@router.get("/thinking/modes")
async def get_thinking_modes():
    """Get thinking modes"""
    return {
        "modes": [
            {"value": "fast", "name": "Fast", "description": "Quick responses"},
            {"value": "analytical", "name": "Analytical", "description": "Step-by-step analysis"},
            {"value": "creative", "name": "Creative", "description": "Innovative thinking"},
            {"value": "critical", "name": "Critical", "description": "Critical evaluation"},
            {"value": "empathetic", "name": "Empathetic", "description": "Emotional understanding"},
        ]
    }


@router.get("/thoughts/{session_id}")
async def get_thoughts(session_id: str):
    """Get thought process"""
    return {
        "session_id": session_id,
        "steps": [],
        "is_complete": True,
        "total_duration_ms": 0
    }


@router.post("/thinking/config")
async def set_thinking_config():
    """Set thinking config"""
    return {"status": "success"}
