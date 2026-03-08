#!/usr/bin/env python3
"""Mul-Agent API Routes"""

from fastapi import APIRouter

router = APIRouter()

# Import all route modules to register them
from mul_agent.api.routes import info, agents, logs, chat, memory, token_usage, integrations
