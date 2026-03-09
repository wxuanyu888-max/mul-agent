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


@router.post("/info/files/batch")
async def get_files_content(request_data: dict):
    """Get content of multiple files

    Args:
        request_data: {"file_paths": [...]}

    Returns:
        Dict mapping file paths to their contents
    """
    from pathlib import Path

    file_paths = request_data.get("file_paths", [])
    base_dir = Path(__file__).parent.parent.parent.parent
    files_content = {}

    for file_path in file_paths:
        try:
            # 构建完整路径
            full_path = Path(file_path)
            if not full_path.is_absolute():
                full_path = base_dir / file_path

            # 安全检查：确保文件在 base_dir 内
            try:
                full_path.resolve().relative_to(base_dir.resolve())
            except ValueError:
                files_content[file_path] = {
                    "error": "Access denied: file outside project directory",
                    "content": None
                }
                continue

            if full_path.exists():
                content = full_path.read_text(encoding="utf-8")
                files_content[file_path] = {
                    "content": content,
                    "size": full_path.stat().st_size,
                    "exists": True
                }
            else:
                files_content[file_path] = {
                    "error": "File not found",
                    "content": None,
                    "exists": False
                }
        except Exception as e:
            files_content[file_path] = {
                "error": str(e),
                "content": None
            }

    return {"files": files_content}


# 全局交互缓存（LRU Cache，TTL 30 秒）
from functools import lru_cache
import time

_interaction_cache: dict = {}
_cache_timestamp: float = 0
_CACHE_TTL = 30  # 缓存有效期（秒）


def _get_interactions_from_logs(log_base_dir: Path, time_window: int = 300, source_filter: Optional[str] = None, target_filter: Optional[str] = None) -> list:
    """从日志文件中提取交互数据"""
    import json
    from datetime import datetime

    interactions = []
    current_time = datetime.now()
    cutoff_time = current_time.timestamp() - time_window

    # 收集所有日志文件并按修改时间排序（最新的在前）
    log_files = []
    for agent_dir in log_base_dir.iterdir():
        if not agent_dir.is_dir():
            continue
        for session_dir in agent_dir.iterdir():
            if not session_dir.is_dir():
                continue
            for log_file in session_dir.glob("*.jsonl"):
                try:
                    mtime = log_file.stat().st_mtime
                    log_files.append((mtime, log_file))
                except Exception:
                    pass

    # 按修改时间排序，优先处理最新的文件
    log_files.sort(key=lambda x: x[0], reverse=True)

    # 处理日志文件（限制数量，避免性能问题）
    checked_files = 0
    for _, log_file in log_files:
        if checked_files >= 20:  # 增加扫描范围到 20 个文件
            break

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            log_entry = json.loads(line.strip())
                        except json.JSONDecodeError:
                            continue

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

                            # 时间窗口过滤
                            if timestamp < cutoff_time:
                                continue

                            source = "wang"
                            target = details.get("sub_agent_id", "unknown")

                            # 过滤器检查
                            if source_filter and source != source_filter:
                                continue
                            if target_filter and target != target_filter:
                                continue

                            interaction = {
                                "run_id": run_id,
                                "source": source,
                                "target": target,
                                "type": details.get("sub_agent_type", "chat"),
                                "task": log_entry.get("message", "")[:200],
                                "status": "executing",
                                "timestamp": timestamp,
                                "datetime": timestamp_str
                            }

                            # 避免重复
                            if not any(i["run_id"] == run_id for i in interactions):
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

                            # 时间窗口过滤
                            if timestamp < cutoff_time:
                                continue

                            source = "wang"
                            target = route

                            # 过滤器检查
                            if source_filter and source != source_filter:
                                continue
                            if target_filter and target != target_filter:
                                continue

                            interaction = {
                                "run_id": run_id,
                                "source": source,
                                "target": target,
                                "type": "delegation",
                                "task": details.get("params", {}).get("command", log_entry.get("message", ""))[:200],
                                "status": "pending",
                                "timestamp": timestamp,
                                "datetime": timestamp_str
                            }

                            # 避免重复
                            if not any(i["run_id"] == run_id for i in interactions):
                                interactions.append(interaction)
        except Exception:
            pass  # Skip files that can't be read

        checked_files += 1

    return interactions


@router.get("/info/interactions")
async def get_interactions(
    limit: int = 50,
    project_id: Optional[str] = None,
    time_window: int = 300  # 默认 5 分钟（秒）
):
    """Get agent interactions from logs and agent team structure

    Args:
        limit: 最大返回数量
        project_id: 项目 ID（暂未使用）
        time_window: 时间窗口（秒），默认 300 秒（5 分钟）
    """
    import json
    from datetime import datetime

    global _interaction_cache, _cache_timestamp

    # 检查缓存是否有效
    current_cache_time = time.time()
    use_cache = (current_cache_time - _cache_timestamp) < _CACHE_TTL

    if use_cache and _interaction_cache:
        # 使用缓存数据，但需要重新应用时间窗口过滤
        cached_interactions = _interaction_cache.get("all", [])
        cutoff_time = datetime.now().timestamp() - time_window
        filtered = [i for i in cached_interactions if i.get("timestamp", 0) >= cutoff_time]
        filtered.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        return {"interactions": filtered[:limit]}

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
        cutoff_time = current_time.timestamp() - time_window
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
                "timestamp": int(current_time.timestamp()),
                "datetime": current_time.strftime("%Y-%m-%d %H:%M:%S")
            })

    # 2. 从日志中提取实际的任务委派交互
    if log_base_dir.exists():
        log_interactions = _get_interactions_from_logs(log_base_dir, time_window=time_window)
        for interaction in log_interactions:
            if not any(i["run_id"] == interaction["run_id"] for i in interactions):
                interactions.append(interaction)

    # 更新缓存
    _interaction_cache["all"] = interactions.copy()
    _cache_timestamp = time.time()

    # 按时间戳排序（最新的在前）并限制数量
    interactions.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return {"interactions": interactions[:limit]}


@router.get("/info/interactions/{source}/{target}")
async def get_agent_interactions(
    source: str,
    target: str,
    time_window: int = 300,  # 默认 5 分钟
    limit: int = 50
):
    """Get interactions between two specific agents

    Args:
        source: 发起方 agent ID
        target: 接收方 agent ID
        time_window: 时间窗口（秒），默认 300 秒（5 分钟）
        limit: 最大返回数量

    Returns:
        这两个 agent 之间指定时间窗口内的所有交互
    """
    import json
    from datetime import datetime

    log_base_dir = Path(__file__).parent.parent.parent.parent / "storage" / "conversations"
    interactions = []

    # 1. 检查是否是团队协作关系
    if source == "core_brain" or target == "core_brain":
        current_time = datetime.now()
        cutoff_time = current_time.timestamp() - time_window
        interactions.append({
            "run_id": f"collab-{source if source != 'core_brain' else target}",
            "source": source,
            "target": target,
            "type": "collaboration",
            "task": "Team collaboration",
            "status": "active",
            "timestamp": int(current_time.timestamp()),
            "datetime": current_time.strftime("%Y-%m-%d %H:%M:%S")
        })

    # 2. 从日志中提取特定 agent 对的交互
    if log_base_dir.exists():
        log_interactions = _get_interactions_from_logs(
            log_base_dir,
            time_window=time_window,
            source_filter=source,
            target_filter=target
        )
        for interaction in log_interactions:
            if not any(i["run_id"] == interaction["run_id"] for i in interactions):
                interactions.append(interaction)

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
