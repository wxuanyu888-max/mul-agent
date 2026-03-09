"""Integrations API routes - AI Platform Integrations Management"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import json
import uuid

router = APIRouter()

# 配置目录
BASE_DIR = Path(__file__).parent.parent.parent.parent
WANG_DIR = BASE_DIR / "wang"
INTEGRATIONS_DIR = WANG_DIR / ".integrations"
INTEGRATIONS_FILE = INTEGRATIONS_DIR / "integrations.json"

# 确保目录存在
INTEGRATIONS_DIR.mkdir(parents=True, exist_ok=True)


class IntegrationCreate(BaseModel):
    """创建集成请求模型"""
    name: str
    url: str
    provider: str
    model: Optional[str] = None
    key: Optional[str] = None
    icon: Optional[str] = None


class IntegrationUpdate(BaseModel):
    """更新集成请求模型"""
    name: Optional[str] = None
    url: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    key: Optional[str] = None
    icon: Optional[str] = None
    status: Optional[str] = None


class IntegrationResponse(BaseModel):
    """集成响应模型"""
    id: str
    name: str
    url: str
    provider: str
    model: Optional[str] = None
    icon: Optional[str] = None
    status: str
    has_key: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


def _load_integrations() -> List[dict]:
    """加载集成列表"""
    if not INTEGRATIONS_FILE.exists():
        return []

    try:
        with open(INTEGRATIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_integrations(integrations: List[dict]) -> bool:
    """保存集成列表"""
    try:
        with open(INTEGRATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(integrations, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


@router.get("/integrations")
async def list_integrations():
    """获取所有集成列表"""
    integrations = _load_integrations()

    # 返回时不包含实际的 key
    result = []
    for integration in integrations:
        result.append({
            "id": integration["id"],
            "name": integration["name"],
            "url": integration["url"],
            "provider": integration["provider"],
            "model": integration.get("model"),
            "icon": integration.get("icon"),
            "status": integration.get("status", "inactive"),
            "has_key": bool(integration.get("key")),
            "created_at": integration.get("created_at"),
            "updated_at": integration.get("updated_at"),
        })

    return {"integrations": result}


@router.get("/integrations/{integration_id}")
async def get_integration(integration_id: str):
    """获取单个集成详情"""
    integrations = _load_integrations()

    for integration in integrations:
        if integration["id"] == integration_id:
            return {
                "id": integration["id"],
                "name": integration["name"],
                "url": integration["url"],
                "provider": integration["provider"],
                "model": integration.get("model"),
                "icon": integration.get("icon"),
                "status": integration.get("status", "inactive"),
                "has_key": bool(integration.get("key")),
                "created_at": integration.get("created_at"),
                "updated_at": integration.get("updated_at"),
            }

    raise HTTPException(status_code=404, detail="Integration not found")


@router.post("/integrations")
async def create_integration(data: IntegrationCreate):
    """创建新的集成"""
    try:
        integrations = _load_integrations()

        # 检查名称是否已存在
        for existing in integrations:
            if existing["name"].lower() == data.name.lower():
                raise HTTPException(status_code=400, detail="Integration with this name already exists")

        now = datetime.now().isoformat()
        new_integration = {
            "id": str(uuid.uuid4()),
            "name": data.name,
            "url": data.url,
            "provider": data.provider,
            "model": data.model,
            "key": data.key,  # 存储加密的 key
            "icon": data.icon,
            "status": "active",
            "created_at": now,
            "updated_at": now,
        }

        integrations.append(new_integration)
        _save_integrations(integrations)

        return {
            "status": "success",
            "integration": {
                "id": new_integration["id"],
                "name": new_integration["name"],
                "url": new_integration["url"],
                "provider": new_integration["provider"],
                "model": new_integration.get("model"),
                "icon": new_integration.get("icon"),
                "status": new_integration["status"],
                "has_key": bool(new_integration["key"]),
                "created_at": new_integration["created_at"],
                "updated_at": new_integration["updated_at"],
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create integration: {str(e)}")


@router.put("/integrations/{integration_id}")
async def update_integration(integration_id: str, data: IntegrationUpdate):
    """更新集成"""
    try:
        integrations = _load_integrations()

        for i, integration in enumerate(integrations):
            if integration["id"] == integration_id:
                # 更新字段
                if data.name is not None:
                    # 检查新名称是否与其他集成重复
                    for other in integrations:
                        if other["id"] != integration_id and other["name"].lower() == data.name.lower():
                            raise HTTPException(status_code=400, detail="Integration with this name already exists")
                    integration["name"] = data.name

                if data.url is not None:
                    integration["url"] = data.url
                if data.provider is not None:
                    integration["provider"] = data.provider
                if data.model is not None:
                    integration["model"] = data.model
                if data.key is not None and data.key:  # 只有在提供了新 key 时才更新
                    integration["key"] = data.key
                if data.icon is not None:
                    integration["icon"] = data.icon
                if data.status is not None:
                    integration["status"] = data.status

                integration["updated_at"] = datetime.now().isoformat()
                integrations[i] = integration
                _save_integrations(integrations)

                return {
                    "status": "success",
                    "integration": {
                        "id": integration["id"],
                        "name": integration["name"],
                        "url": integration["url"],
                        "provider": integration["provider"],
                        "model": integration.get("model"),
                        "icon": integration.get("icon"),
                        "status": integration["status"],
                        "has_key": bool(integration.get("key")),
                        "created_at": integration.get("created_at"),
                        "updated_at": integration.get("updated_at"),
                    }
                }

        raise HTTPException(status_code=404, detail="Integration not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update integration: {str(e)}")


@router.delete("/integrations/{integration_id}")
async def delete_integration(integration_id: str):
    """删除集成"""
    try:
        integrations = _load_integrations()

        for i, integration in enumerate(integrations):
            if integration["id"] == integration_id:
                del integrations[i]
                _save_integrations(integrations)
                return {"status": "success", "message": "Integration deleted successfully"}

        raise HTTPException(status_code=404, detail="Integration not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete integration: {str(e)}")


@router.post("/integrations/{integration_id}/duplicate")
async def duplicate_integration(integration_id: str):
    """复制集成"""
    try:
        integrations = _load_integrations()

        for integration in integrations:
            if integration["id"] == integration_id:
                now = datetime.now().isoformat()
                new_integration = {
                    "id": str(uuid.uuid4()),
                    "name": f"{integration['name']} (Copy)",
                    "url": integration["url"],
                    "provider": integration["provider"],
                    "model": integration.get("model"),
                    "key": integration.get("key"),
                    "icon": integration.get("icon"),
                    "status": "inactive",  # 复制后默认禁用
                    "created_at": now,
                    "updated_at": now,
                }

                integrations.append(new_integration)
                _save_integrations(integrations)

                return {
                    "status": "success",
                    "integration": {
                        "id": new_integration["id"],
                        "name": new_integration["name"],
                        "url": new_integration["url"],
                        "provider": new_integration["provider"],
                        "model": new_integration.get("model"),
                        "icon": new_integration.get("icon"),
                        "status": new_integration["status"],
                        "has_key": bool(new_integration["key"]),
                        "created_at": new_integration["created_at"],
                        "updated_at": new_integration["updated_at"],
                    }
                }

        raise HTTPException(status_code=404, detail="Integration not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to duplicate integration: {str(e)}")


@router.put("/integrations/reorder")
async def reorder_integrations(data: dict):
    """重新排序集成"""
    try:
        integrations = _load_integrations()
        reorder_list = data.get("integrations", [])

        # 根据给定的顺序重新排列
        new_order = []
        for item in reorder_list:
            integration_id = item.get("id")
            for integration in integrations:
                if integration["id"] == integration_id:
                    new_order.append(integration)
                    break

        # 添加可能遗漏的集成
        existing_ids = {item["id"] for item in new_order}
        for integration in integrations:
            if integration["id"] not in existing_ids:
                new_order.append(integration)

        _save_integrations(new_order)
        return {"status": "success", "message": "Integrations reordered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reorder integrations: {str(e)}")
