"""Repositories - 数据访问层

架构说明:
- Repository 模式封装数据访问逻辑
- 提供统一的 CRUD 接口
- 易于测试和替换存储后端
"""

from .base import BaseRepository
from .agent_repository import AgentRepository
from .team_repository import TeamRepository
from .key_repository import KeyRepository

__all__ = [
    "BaseRepository",
    "AgentRepository",
    "TeamRepository",
    "KeyRepository",
]
