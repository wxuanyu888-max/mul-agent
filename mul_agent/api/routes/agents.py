"""Agents API routes"""

from fastapi import APIRouter, HTTPException
from pathlib import Path

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
AGENT_CONFIG_DIR = STORAGE_DIR / "agent_config"


@router.get("/agents")
async def list_agents():
    """List all agents"""
    agents = []

    if AGENT_CONFIG_DIR.exists():
        for item in AGENT_CONFIG_DIR.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                agent_id = item.name
                soul_file = item / "soul.md"

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
                    "role": ""
                })

    return {"agents": agents}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get agent details"""
    agent_path = AGENT_CONFIG_DIR / agent_id

    if not agent_path.exists():
        raise HTTPException(status_code=404, detail="Agent not found")

    return {
        "agent_id": agent_id,
        "soul": {},
        "user": {},
        "skill": {},
        "memory": {}
    }


@router.get("/agents/{agent_id}/status")
async def get_agent_status(agent_id: str):
    """Get agent status"""
    return {
        "agent_id": agent_id,
        "status": "idle",
        "session_id": None
    }
