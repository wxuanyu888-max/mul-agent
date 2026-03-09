"""Team Repository - 团队数据访问"""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import BaseRepository


class TeamRepository(BaseRepository):
    """团队 Repository

    负责团队数据的 CRUD 操作
    """

    def __init__(self, config_manager):
        """初始化 Repository

        Args:
            config_manager: ConfigManager 实例
        """
        self.config_manager = config_manager
        self.teams_dir = config_manager.wang_dir / ".teams"
        self.teams_dir.mkdir(parents=True, exist_ok=True)

    def find_by_id(self, team_name: str) -> Optional[Dict[str, Any]]:
        """根据团队名查找团队

        Args:
            team_name: 团队名称

        Returns:
            团队配置字典，如果不存在则返回 None
        """
        team_file = self.teams_dir / f"{team_name}.json"

        if not team_file.exists():
            return None

        try:
            with open(team_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def find_all(self) -> Dict[str, List[str]]:
        """获取所有团队及其成员

        Returns:
            团队名到 Agent 列表的映射
        """
        return self.config_manager.list_teams()

    def find_members(self, team_name: str) -> List[str]:
        """获取团队成员列表

        Args:
            team_name: 团队名称

        Returns:
            Agent ID 列表
        """
        teams = self.find_all()
        return teams.get(team_name, [])

    def add_member(self, team_name: str, agent_id: str) -> bool:
        """添加团队成员

        Args:
            team_name: 团队名称
            agent_id: Agent ID

        Returns:
            是否添加成功
        """
        team_data = self.find_by_id(team_name)
        if not team_data:
            # 如果团队不存在，先创建
            team_data = {
                "name": team_name,
                "description": "",
                "created_by": "system",
                "members": []
            }

        if agent_id not in team_data.get("members", []):
            team_data.setdefault("members", []).append(agent_id)
            return self._save_team(team_name, team_data)

        return True

    def remove_member(self, team_name: str, agent_id: str) -> bool:
        """移除团队成员

        Args:
            team_name: 团队名称
            agent_id: Agent ID

        Returns:
            是否移除成功
        """
        team_data = self.find_by_id(team_name)
        if not team_data:
            return False

        members = team_data.get("members", [])
        if agent_id in members:
            members.remove(agent_id)
            return self._save_team(team_name, team_data)

        return True

    def save(self, team_name: str, data: Dict[str, Any]) -> bool:
        """保存团队配置

        Args:
            team_name: 团队名称
            data: 团队配置数据

        Returns:
            是否保存成功
        """
        return self._save_team(team_name, data)

    def _save_team(self, team_name: str, data: Dict[str, Any]) -> bool:
        """保存团队到文件

        Args:
            team_name: 团队名称
            data: 团队配置数据

        Returns:
            是否保存成功
        """
        if team_name.lower() == "default":
            return False  # 保留字

        team_file = self.teams_dir / f"{team_name}.json"

        try:
            with open(team_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def delete(self, team_name: str) -> bool:
        """删除团队

        Args:
            team_name: 团队名称

        Returns:
            是否删除成功
        """
        if team_name.lower() == "default":
            return False  # 不能删除默认团队

        team_file = self.teams_dir / f"{team_name}.json"

        if team_file.exists():
            try:
                team_file.unlink()
                return True
            except Exception:
                return False

        return False

    def exists(self, team_name: str) -> bool:
        """检查团队是否存在

        Args:
            team_name: 团队名称

        Returns:
            是否存在
        """
        team_file = self.teams_dir / f"{team_name}.json"
        return team_file.exists()

    def list_all(self) -> List[Dict[str, Any]]:
        """列出所有团队配置

        Returns:
            团队配置列表
        """
        teams = []
        for team_file in self.teams_dir.glob("*.json"):
            try:
                with open(team_file, "r", encoding="utf-8") as f:
                    teams.append(json.load(f))
            except Exception:
                pass
        return teams
