"""Info API routes"""

from fastapi import APIRouter, Query
from pathlib import Path
from typing import Optional

router = APIRouter()

# 所有存储都在 wang 目录下
BASE_DIR = Path(__file__).parent.parent.parent.parent
WANG_DIR = BASE_DIR / "wang"
AGENT_TEAM_DIR = WANG_DIR / "agent-team"
PROJECTS_DIR = WANG_DIR / "projects"
FILE_HISTORY_DIR = WANG_DIR / "file-history"
TOKEN_USAGE_DIR = WANG_DIR / "token_usage"


def get_agent_config_dir(project_id: Optional[str] = None) -> Path:
    """Get agent config directory for a project or global"""
    if project_id:
        project_dir = PROJECTS_DIR / project_id
        if project_dir.exists():
            return project_dir / "agents"
    return AGENT_TEAM_DIR


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
        # Return default for wang
        if agent_id == "wang":
            return {
                "agent_id": agent_id,
                "name": "Wang",
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
async def get_interactions(limit: int = 50, project_id: Optional[str] = None):
    """Get agent interactions from logs and agent team structure"""
    import json
    from datetime import datetime

    # 日志存储在 storage/conversations 目录下，按 agent 和日期组织
    log_base_dir = Path(__file__).parent.parent.parent.parent / "storage" / "conversations"
    interactions = []

    # 1. 先从 agent-team 获取协作关系（基础交互）
    agent_team_dir = Path(__file__).parent.parent.parent.parent / "wang" / "agent-team"
    if agent_team_dir.exists():
        agents_in_team = []
        for item in agent_team_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                agents_in_team.append(item.name)

        # 为每个 agent 创建与 core_brain 的协作关系
        current_time = datetime.now()
        for agent_id in agents_in_team:
            if agent_id in ['core_brain', '.templates']:
                continue
            interactions.append({
                "run_id": f"collab-{agent_id}",
                "source": "core_brain",
                "target": agent_id,
                "type": "collaboration",
                "task": "Team collaboration",
                "status": "active",
                "timestamp": int(current_time.timestamp())
            })

    # 2. 从日志中提取实际的任务委派交互
    if not log_base_dir.exists():
        interactions.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return {"interactions": interactions[:limit]}

    # 使用简单的文件遍历，避免复杂的嵌套循环
    checked_files = 0
    for agent_dir in log_base_dir.iterdir():
        if checked_files >= 10:
            break
        if not agent_dir.is_dir():
            continue

        for session_dir in agent_dir.iterdir():
            if checked_files >= 10:
                break
            if not session_dir.is_dir():
                continue

            for log_file in session_dir.glob("*.jsonl"):
                if checked_files >= 10:
                    break

                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                log_entry = json.loads(line.strip())

                                # 提取 SubAgent 交互
                                if log_entry.get("source") == "SubAgent":
                                    details = log_entry.get("details", {})
                                    run_id = log_entry.get("run_id", log_entry.get("trace_id", ""))
                                    timestamp_str = log_entry.get("datetime", "")

                                    try:
                                        dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                                        timestamp = int(dt.timestamp())
                                    except Exception:
                                        timestamp = 0

                                    interaction = {
                                        "run_id": run_id,
                                        "source": "wang",
                                        "target": details.get("sub_agent_id", "unknown"),
                                        "type": details.get("sub_agent_type", "chat"),
                                        "task": log_entry.get("message", "")[:200],
                                        "status": "executing",
                                        "timestamp": timestamp
                                    }

                                    if interaction not in interactions:
                                        interactions.append(interaction)

                                # 提取 Router 决策
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
                                        "source": "wang",
                                        "target": route,
                                        "type": "delegation",
                                        "task": details.get("params", {}).get("command", log_entry.get("message", ""))[:200],
                                        "status": "pending",
                                        "timestamp": timestamp
                                    }

                                    if interaction not in interactions:
                                        interactions.append(interaction)
                except Exception:
                    pass  # Skip files that can't be read

                checked_files += 1

    # 按时间戳排序（最新的在前）并限制数量
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


# 全局状态存储（用于 WebSocket 推送前的临时方案）
_agent_states: dict = {}


@router.get("/agent/state/{agent_id}")
async def get_agent_state(agent_id: str):
    """Get real-time agent state"""
    state = _agent_states.get(agent_id, {
        "agent_id": agent_id,
        "status": "idle",
        "current_action": None,
        "route": None,
        "elapsed_ms": 0,
        "last_updated": None
    })
    return {"state": state}


@router.post("/agent/state/{agent_id}")
async def update_agent_state(agent_id: str, state_data: dict):
    """Update agent state"""
    import time
    state = {
        "agent_id": agent_id,
        "status": state_data.get("status", "idle"),
        "current_action": state_data.get("current_action"),
        "route": state_data.get("route"),
        "elapsed_ms": state_data.get("elapsed_ms", 0),
        "last_updated": int(time.time() * 1000),
        "details": state_data.get("details")
    }
    _agent_states[agent_id] = state
    return {"status": "success"}


@router.delete("/agent/state/{agent_id}")
async def clear_agent_state(agent_id: str):
    """Clear agent state"""
    if agent_id in _agent_states:
        del _agent_states[agent_id]
    return {"status": "success"}


@router.get("/agent/states")
async def get_all_agent_states():
    """Get all agent states"""
    return {"states": list(_agent_states.values())}
