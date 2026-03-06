#!/usr/bin/env python3
"""FastAPI Server for Mul-Agent"""

from pathlib import Path
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
AGENT_CONFIG_DIR = STORAGE_DIR / "agent_config"

app = FastAPI(title="Mul-Agent API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from mul_agent.api.routes import info, agents, logs, chat, memory, projects, token_usage

app.include_router(info.router, prefix="/api/v1", tags=["info"])
app.include_router(agents.router, prefix="/api/v1", tags=["agents"])
app.include_router(logs.router, prefix="/api/v1", tags=["logs"])
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(memory.router, prefix="/api/v1", tags=["memory"])
app.include_router(projects.router, prefix="/api/v1", tags=["projects"])
app.include_router(token_usage.router, prefix="/api/v1", tags=["token_usage"])


@app.get("/api/v1/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
