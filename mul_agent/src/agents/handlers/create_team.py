"""Create Team Handler - 创建团队处理器"""
from typing import Any, Dict
import json

from .base import BaseHandler


class CreateTeamHandler(BaseHandler):
    """创建新团队处理器"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}
        team_name = params.get("name")
        description = params.get("description")

        if not team_name or not str(team_name).strip():
            return {"status": "error", "error_code": 1004, "message": "Missing: name"}
        if not description or not str(description).strip():
            return {"status": "error", "error_code": 1004, "message": "Missing: description"}
        if str(team_name).lower().strip() == "default":
            return {"status": "error", "error_code": 1004, "message": "Team name 'default' is reserved"}

        try:
            team_config = {"name": str(team_name).strip(), "description": str(description).strip(), "created_by": "wang", "members": []}
            teams_dir = self.config_manager.wang_dir / ".teams"
            teams_dir.mkdir(parents=True, exist_ok=True)
            team_file = teams_dir / f"{team_name}.json"
            if team_file.exists():
                return {"status": "error", "error_code": 1004, "message": f"Team '{team_name}' already exists"}
            with open(team_file, "w", encoding="utf-8") as f:
                json.dump(team_config, f, indent=2, ensure_ascii=False)
            return {"team_name": str(team_name).strip(), "description": str(description).strip(), "status": "created", "message": f"Team '{team_name}' created!"}
        except Exception as e:
            return {"status": "error", "error_code": 1005, "message": f"Failed: {str(e)}"}
