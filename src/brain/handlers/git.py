"""Git Handler - Git 操作处理器"""

from typing import Any, Dict
from .base import BaseHandler


class GitDiffHandler(BaseHandler):
    """Git diff 处理器 - 查看未提交的改动"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}

        path = params.get("path")  # 可选，指定文件
        staged = params.get("staged", False)  # 是否查看已暂存的改动

        from mul_agent.tools.git_diff import GitDiffTool

        # 使用项目根目录作为 repo_path
        repo_path = self._get_repo_path()
        tool = GitDiffTool(repo_path)

        if not tool.is_git_repo():
            return {
                "status": "error",
                "error_code": 1004,
                "message": "Not a git repository"
            }

        result = tool.diff(path=path, staged=staged)

        if result["status"] == "error":
            return {
                "status": "error",
                "error_code": 1006,
                "message": result.get("error", "Git diff failed")
            }

        return {
            "status": "success",
            "diff": result["diff"],
            "files_changed": result["files_changed"],
            "stats": result["stats"]
        }

    def _get_repo_path(self) -> str:
        """获取 Git 仓库路径"""
        # 尝试从配置中获取，或使用工作区根目录
        try:
            from mul_agent.brain.workspace import get_current_workspace
            workspace = get_current_workspace()
            return str(workspace.root_path)
        except Exception:
            return "."


class GitStatusHandler(BaseHandler):
    """Git status 处理器 - 查看仓库状态"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from mul_agent.tools.git_diff import GitDiffTool

        repo_path = self._get_repo_path()
        tool = GitDiffTool(repo_path)

        if not tool.is_git_repo():
            return {
                "status": "error",
                "error_code": 1004,
                "message": "Not a git repository"
            }

        return tool.status()


class GitCommitHandler(BaseHandler):
    """Git commit 处理器 - 提交改动"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}

        message = params.get("message")
        if not message:
            return {"status": "error", "error_code": 1004, "message": "Missing: commit message"}

        from mul_agent.tools.git_diff import GitDiffTool

        repo_path = self._get_repo_path()
        tool = GitDiffTool(repo_path)

        if not tool.is_git_repo():
            return {
                "status": "error",
                "error_code": 1004,
                "message": "Not a git repository"
            }

        files = params.get("files")  # 可选，指定文件
        return tool.commit(message=message, files=files)


class GitLogHandler(BaseHandler):
    """Git log 处理器 - 查看提交历史"""

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        from mul_agent.tools.git_diff import GitDiffTool

        repo_path = self._get_repo_path()
        tool = GitDiffTool(repo_path)

        if not tool.is_git_repo():
            return {
                "status": "error",
                "error_code": 1004,
                "message": "Not a git repository"
            }

        limit = params.get("limit", 10)
        return tool.log(limit=limit)
