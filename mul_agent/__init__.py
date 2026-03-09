"""
mul-agent - Multi-Agent Collaboration System

一个自主的多 Agent 协作系统
参考 OpenClaw 架构设计
"""

__version__ = "2026.3.9"
__author__ = "mul-agent team"

# 核心模块 - 新架构
from mul_agent.src import (
    agents,
    commands,
    hooks,
    memory,
    plugin_sdk,
    types,
    cli,
    tools,
    skills,
)

# 兼容旧导入路径
from mul_agent.brain.brain import Brain
from mul_agent.brain.llm import LLM
from mul_agent.tools.base import BaseTool

# 新架构导出
from mul_agent.src.agents.brain.brain import Brain as BrainV2
from mul_agent.src.types.agent import AgentConfig

__all__ = [
    # 核心
    "Brain",
    "BrainV2",
    "LLM",
    "AgentConfig",
    "BaseTool",
    # 模块
    "agents",
    "commands",
    "hooks",
    "memory",
    "plugin_sdk",
    "types",
    "cli",
    "tools",
    "skills",
]
