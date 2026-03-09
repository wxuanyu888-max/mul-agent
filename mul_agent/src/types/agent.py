"""
Types - 类型定义模块
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, List, Dict


class AgentRoleType(str, Enum):
    """Agent 角色类型"""
    EXECUTOR = "executor"
    PLANNER = "planner"
    WORKER = "worker"
    SUPERVISOR = "supervisor"


@dataclass
class AgentRole:
    """Agent 角色定义"""
    type: AgentRoleType
    title: str
    responsibilities: List[str] = field(default_factory=list)


@dataclass
class AgentIdentity:
    """Agent 身份"""
    agent_id: str
    name: str
    role: AgentRole


@dataclass
class AgentConfig:
    """Agent 配置"""
    agent_id: str
    name: str
    role: AgentRole
    tools: Dict[str, bool] = field(default_factory=dict)
    llm_enabled: bool = True
    llm_model: str = "claude-sonnet-4-20250514"
    temperature: float = 0.3
    memory_enabled: bool = True


__all__ = [
    "AgentRoleType",
    "AgentRole",
    "AgentIdentity",
    "AgentConfig",
]
