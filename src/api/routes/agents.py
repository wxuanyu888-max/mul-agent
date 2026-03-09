"""Agents API routes"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Optional

from mul_agent.brain.config_manager import ConfigManager
from mul_agent.api.global_config import GlobalLLMConfig

router = APIRouter()

# 所有存储都在 wang 目录下
BASE_DIR = Path(__file__).parent.parent.parent.parent
WANG_DIR = BASE_DIR / "wang"
AGENT_TEAM_DIR = WANG_DIR / "agent-team"

# 初始化 ConfigManager 和全局配置
config_manager = ConfigManager(WANG_DIR)
global_config = GlobalLLMConfig(WANG_DIR)


class LlmConfigRequest(BaseModel):
    """LLM 配置请求模型"""
    url: str
    provider: str
    model: str
    key: str


class LlmConfigResponse(BaseModel):
    """LLM 配置响应模型"""
    url: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    has_key: bool = False  # 不返回实际 key，只表示是否存在


@router.get("/agents")
async def list_agents():
    """List all agents - 从 wang/agent-team 读取"""
    agents = []

    if AGENT_TEAM_DIR.exists():
        for item in AGENT_TEAM_DIR.iterdir():
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
    agent_path = AGENT_TEAM_DIR / agent_id

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


@router.get("/llm-config", response_model=LlmConfigResponse)
async def get_llm_config():
    """获取全局 LLM 配置

    返回配置信息（url, provider, model），但不返回实际的 key 值
    """
    config = global_config.get_config()

    if not config:
        return LlmConfigResponse(has_key=False)

    return LlmConfigResponse(
        url=config.get("url"),
        provider=config.get("provider"),
        model=config.get("model"),
        has_key=bool(config.get("key"))
    )


@router.put("/llm-config", response_model=LlmConfigResponse)
async def update_llm_config(request_config: LlmConfigRequest):
    """更新全局 LLM 配置

    需要同时提供 url, provider, model, key 四个参数
    """
    try:
        config = {
            "url": request_config.url,
            "provider": request_config.provider,
            "model": request_config.model,
            "key": request_config.key
        }
        global_config.save_config(config)

        return LlmConfigResponse(
            url=request_config.url,
            provider=request_config.provider,
            model=request_config.model,
            has_key=True
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")


@router.delete("/llm-config")
async def delete_llm_config():
    """删除全局 LLM 配置"""
    try:
        global_config.delete_config()
        return {"message": "Key configuration deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete config: {e}")


@router.get("/agents/{agent_id}/key", response_model=LlmConfigResponse)
async def get_agent_key(agent_id: str):
    """获取全局 LLM 配置（兼容旧接口）"""
    config = global_config.get_config()

    if not config:
        return LlmConfigResponse(has_key=False)

    return LlmConfigResponse(
        url=config.get("url"),
        provider=config.get("provider"),
        model=config.get("model"),
        has_key=bool(config.get("key"))
    )


@router.put("/agents/{agent_id}/key", response_model=LlmConfigResponse)
async def update_agent_key(agent_id: str, config: LlmConfigRequest):
    """更新全局 LLM 配置（兼容旧接口）"""
    try:
        llm_config = {
            "url": config.url,
            "provider": config.provider,
            "model": config.model,
            "key": config.key
        }
        global_config.save_config(llm_config)

        return LlmConfigResponse(
            url=config.url,
            provider=config.provider,
            model=config.model,
            has_key=True
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")


@router.delete("/agents/{agent_id}/key")
async def delete_agent_key(agent_id: str):
    """删除全局 LLM 配置（兼容旧接口）"""
    try:
        global_config.delete_config()
        return {"message": "Key configuration deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete config: {e}")
