"""
Agents - Agent 核心系统

包含 Agent 基类、配置和身份管理
"""

from mul_agent.src.agents.brain.brain import Brain
from mul_agent.src.agents.brain.brain_v2 import BrainV2

__all__ = [
    "Brain",
    "BrainV2",
]
