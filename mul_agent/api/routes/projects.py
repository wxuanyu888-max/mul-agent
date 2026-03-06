"""Projects API routes - Manage multiple projects with isolated agents"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import json

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
PROJECTS_DIR = STORAGE_DIR / "projects"


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    project_id: str = ""


@router.get("/projects")
async def list_projects():
    """List all projects"""
    projects = []

    if PROJECTS_DIR.exists():
        for item in PROJECTS_DIR.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                project_id = item.name
                meta_file = item / "meta.json"

                name = project_id
                description = ""
                created_at = ""

                if meta_file.exists():
                    meta = json.loads(meta_file.read_text())
                    name = meta.get("name", project_id)
                    description = meta.get("description", "")
                    created_at = meta.get("created_at", "")

                # Count agents in this project
                agents_dir = item / "agents"
                agent_count = 0
                if agents_dir.exists():
                    agent_count = len([d for d in agents_dir.iterdir() if d.is_dir()])

                projects.append({
                    "project_id": project_id,
                    "name": name,
                    "description": description,
                    "created_at": created_at,
                    "agent_count": agent_count
                })

    return {"projects": projects}


@router.post("/projects")
async def create_project(project: ProjectCreate):
    """Create a new project"""
    # Generate project_id from name if not provided
    project_id = project.project_id or project.name.lower().replace(" ", "_").replace("-", "_")

    project_dir = PROJECTS_DIR / project_id

    if project_dir.exists():
        raise HTTPException(status_code=400, detail="Project already exists")

    # Create project directory structure
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "agents").mkdir(exist_ok=True)
    (project_dir / "runs").mkdir(exist_ok=True)

    # Create meta.json
    meta = {
        "name": project.name,
        "description": project.description,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    (project_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    return {
        "status": "success",
        "project_id": project_id,
        "message": f"Project '{project.name}' created successfully"
    }


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details"""
    project_dir = PROJECTS_DIR / project_id

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    meta_file = project_dir / "meta.json"

    name = project_id
    description = ""
    created_at = ""

    if meta_file.exists():
        meta = json.loads(meta_file.read_text())
        name = meta.get("name", project_id)
        description = meta.get("description", "")
        created_at = meta.get("created_at", "")

    # Count agents
    agents_dir = project_dir / "agents"
    agents = []
    if agents_dir.exists():
        for agent_folder in agents_dir.iterdir():
            if agent_folder.is_dir():
                agent_id = agent_folder.name
                soul_file = agent_folder / "soul.md"

                agent_name = agent_id
                agent_description = ""

                if soul_file.exists():
                    content = soul_file.read_text()
                    if "name: " in content:
                        agent_name = content.split("name: ")[-1].split("\n")[0]
                    if "description: " in content:
                        agent_description = content.split("description: ")[-1].split("\n")[0]

                agents.append({
                    "agent_id": agent_id,
                    "name": agent_name,
                    "description": agent_description
                })

    return {
        "project_id": project_id,
        "name": name,
        "description": description,
        "created_at": created_at,
        "agents": agents
    }


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project"""
    project_dir = PROJECTS_DIR / project_id

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete project directory
    import shutil
    shutil.rmtree(project_dir)

    return {
        "status": "success",
        "message": f"Project '{project_id}' deleted successfully"
    }


@router.get("/projects/{project_id}/agents")
async def list_project_agents(project_id: str):
    """List all agents in a project"""
    project_dir = PROJECTS_DIR / project_id

    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    agents_dir = project_dir / "agents"

    if not agents_dir.exists():
        return {"agents": []}

    agents = []
    for item in agents_dir.iterdir():
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
                "role": user_file.read_text() if user_file.exists() else ""
            })

    return {"agents": agents}
