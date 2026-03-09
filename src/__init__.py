"""
mul-agent - Multi-Agent Collaboration System

A personal AI assistant with extensible architecture.
Inspired by OpenClaw architecture.
"""

__version__ = "2026.3.9"
__author__ = "mul-agent team"

# Core exports - new architecture
from mul_agent.core.agent import Agent, AgentConfig
from mul_agent.core.brain import Brain, BrainConfig

# Plugins
from mul_agent.plugins.sdk import PluginAPI
from mul_agent.plugins.types import (
    PluginManifest,
    PluginContext,
    ToolRegistry,
    HookRegistry,
    CommandRegistry,
    ToolEntry,
    HookEntry,
    HookPhase,
    CommandEntry,
)

__all__ = [
    # Core
    "Agent",
    "AgentConfig",
    "Brain",
    "BrainConfig",
    # Plugins
    "PluginAPI",
    "PluginManifest",
    "PluginContext",
    "ToolRegistry",
    "HookRegistry",
    "CommandRegistry",
    "ToolEntry",
    "HookEntry",
    "HookPhase",
    "CommandEntry",
]
