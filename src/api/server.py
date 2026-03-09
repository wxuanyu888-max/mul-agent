#!/usr/bin/env python3
"""FastAPI Server for Mul-Agent"""

import logging
import json
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"
AGENT_CONFIG_DIR = STORAGE_DIR / "agent_config"
LOG_DIR = STORAGE_DIR / "logs"

# Ensure log directory exists
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging to write to JSONL file
log_file = LOG_DIR / f"server_{datetime.now().strftime('%Y%m%d')}.jsonl"

class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for logging"""
    def format(self, record):
        log_entry = {
            "datetime": datetime.fromtimestamp(record.created).isoformat(),
            "timestamp": record.created,
            "level": record.levelname,
            "source": "server",
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            log_entry["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)

# Setup logger
logger = logging.getLogger("mul_agent")
logger.setLevel(logging.DEBUG)

# File handler - JSONL format
file_handler = logging.FileHandler(log_file, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(JsonFormatter())
logger.addHandler(file_handler)

# Console handler for development
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(console_handler)

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
# Note: Use 'import module' instead of 'from module import x' to avoid namespace issues
import mul_agent.api.routes.info as info_routes
import mul_agent.api.routes.agents as agents_routes
import mul_agent.api.routes.logs as logs_routes
import mul_agent.api.routes.chat as chat_routes
import mul_agent.api.routes.memory as memory_routes
import mul_agent.api.routes.projects as projects_routes
import mul_agent.api.routes.token_usage as token_usage_routes
import mul_agent.api.routes.integrations as integrations_routes
import mul_agent.api.routes.stream as stream_routes

app.include_router(info_routes.router, prefix="/api/v1", tags=["info"])
app.include_router(agents_routes.router, prefix="/api/v1", tags=["agents"])
app.include_router(logs_routes.router, prefix="/api/v1", tags=["logs"])
app.include_router(chat_routes.router, prefix="/api/v1", tags=["chat"])
app.include_router(memory_routes.router, prefix="/api/v1", tags=["memory"])
app.include_router(projects_routes.router, prefix="/api/v1", tags=["projects"])
app.include_router(token_usage_routes.router, prefix="/api/v1", tags=["token_usage"])
app.include_router(integrations_routes.router, prefix="/api/v1", tags=["integrations"])
app.include_router(stream_routes.router, prefix="/api/v1", tags=["stream"])

# Also include agents router without v1 for frontend compatibility
app.include_router(agents_routes.router, prefix="/api", tags=["agents-v2"])


@app.get("/api/v1/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
