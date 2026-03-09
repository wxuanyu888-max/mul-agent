"""
Core - Agent 核心模块

包含：
- Agent: Agent 核心类
- Brain: 决策引擎
- Router: 路由系统
"""

from mul_agent.core.agent import Agent, AgentConfig
from mul_agent.core.brain import Brain, BrainConfig

__all__ = [
    "Agent",
    "AgentConfig",
    "Brain",
    "BrainConfig",
]
