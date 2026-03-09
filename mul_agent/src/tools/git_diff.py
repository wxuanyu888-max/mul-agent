"""Git Diff Tool - Git 差异查看工具"""

import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any


class GitDiffTool:
    """Git 差异查看工具

    功能:
    - 查看工作区未提交的改动
    - 查看指定文件的改动
    - 查看最近提交的改动
    """

    def __init__(self, repo_path: Optional[str] = None):
        """初始化工具

        Args:
            repo_path: Git 仓库路径，默认为当前工作目录
        """
        self.repo_path = Path(repo_path) if repo_path else Path.cwd()

    def _run_git(self, args: List[str]) -> tuple[bool, str, str]:
        """运行 git 命令

        Returns:
            (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Git command timed out"
        except FileNotFoundError:
            return False, "", "Git not found. Please install git."
        except Exception as e:
            return False, "", str(e)

    def is_git_repo(self) -> bool:
        """检查是否是 Git 仓库"""
        success, _, _ = self._run_git(["rev-parse", "--git-dir"])
        return success

    def diff(self, path: Optional[str] = None, staged: bool = False) -> Dict[str, Any]:
        """查看未提交的改动

        Args:
            path: 文件路径，None 表示所有文件
            staged: 是否查看已暂存的改动

        Returns:
            {
                "status": "success/error",
                "diff": "diff 内容",
                "files_changed": ["改动的文件列表"],
                "stats": {"additions": 数字，"deletions": 数字}
            }
        """
        if not self.is_git_repo():
            return {
                "status": "error",
                "error": "Not a git repository"
            }

        args = ["diff"]
        if staged:
            args.append("--cached")
        if path:
            args.extend(["--", str(path)])

        success, stdout, stderr = self._run_git(args)

        if not success:
            return {
                "status": "error",
                "error": stderr
            }

        # 解析改动的文件
        files_changed = []
        if stdout:
            for line in stdout.split('\n'):
                if line.startswith('diff --git'):
                    parts = line.split(' ')
                    if len(parts) >= 3:
                        # 提取文件路径
                        file_path = parts[2][2:]  # 移除 "a/" 前缀
                        files_changed.append(file_path)

        # 统计增减行数
        additions = stdout.count('\n+') if stdout else 0
        deletions = stdout.count('\n-') if stdout else 0

        # 移除 diff 开头的统计行
        diff_content = stdout

        return {
            "status": "success",
            "diff": diff_content,
            "files_changed": files_changed,
            "stats": {
                "additions": additions,
                "deletions": deletions,
                "files_changed": len(files_changed)
            }
        }

    def diff_summary(self) -> Dict[str, Any]:
        """获取改动摘要

        Returns:
            {
                "status": "success/error",
                "summary": "简短描述",
                "files_changed": 数字，
                "additions": 数字，
                "deletions": 数字
            }
        """
        result = self.diff()

        if result["status"] == "error":
            return result

        return {
            "status": "success",
            "summary": f"{result['stats']['files_changed']} 个文件改动，"
                      f"+{result['stats']['additions']} -{result['stats']['deletions']}",
            "files_changed": result['stats']['files_changed'],
            "additions": result['stats']['additions'],
            "deletions": result['stats']['deletions']
        }

    def status(self) -> Dict[str, Any]:
        """获取 Git 状态

        Returns:
            {
                "status": "success/error",
                "output": "git status 输出",
                "changed_files": ["未暂存的文件"],
                "staged_files": ["已暂存的文件"],
                "untracked_files": ["未追踪的文件"]
            }
        """
        if not self.is_git_repo():
            return {
                "status": "error",
                "error": "Not a git repository"
            }

        success, stdout, stderr = self._run_git(["status", "--porcelain"])

        if not success:
            return {
                "status": "error",
                "error": stderr
            }

        changed_files = []
        staged_files = []
        untracked_files = []

        for line in stdout.strip().split('\n'):
            if not line:
                continue
            status_code = line[:2]
            file_path = line[3:]

            if status_code.startswith('??'):
                untracked_files.append(file_path)
            elif status_code.startswith('M ') or status_code.startswith(' D'):
                changed_files.append(file_path)
            elif status_code.startswith('M') or status_code.startswith('D') or status_code.startswith('A'):
                staged_files.append(file_path)

        return {
            "status": "success",
            "output": stdout,
            "changed_files": changed_files,
            "staged_files": staged_files,
            "untracked_files": untracked_files
        }

    def commit(self, message: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """提交改动

        Args:
            message: 提交信息
            files: 要提交的文件列表，None 表示所有改动的文件

        Returns:
            {
                "status": "success/error",
                "commit_hash": "提交的 hash",
                "message": "提交信息"
            }
        """
        if not self.is_git_repo():
            return {
                "status": "error",
                "error": "Not a git repository"
            }

        # 如果有指定文件，先暂存
        if files:
            for file in files:
                success, _, stderr = self._run_git(["add", file])
                if not success:
                    return {
                        "status": "error",
                        "error": f"Failed to stage {file}: {stderr}"
                    }
        else:
            # 暂存所有改动
            success, _, stderr = self._run_git(["add", "-A"])
            if not success:
                return {
                    "status": "error",
                    "error": f"Failed to stage all files: {stderr}"
                }

        # 提交
        success, stdout, stderr = self._run_git(["commit", "-m", message])

        if not success:
            return {
                "status": "error",
                "error": stderr
            }

        # 获取提交 hash
        _, commit_hash, _ = self._run_git(["rev-parse", "--short", "HEAD"])

        return {
            "status": "success",
            "commit_hash": commit_hash.strip(),
            "message": message
        }

    def log(self, limit: int = 10) -> Dict[str, Any]:
        """查看提交历史

        Args:
            limit: 显示的提交数量

        Returns:
            {
                "status": "success/error",
                "commits": [
                    {"hash": "abc123", "message": "提交信息", "date": "2024-01-01"}
                ]
            }
        """
        if not self.is_git_repo():
            return {
                "status": "error",
                "error": "Not a git repository"
            }

        success, stdout, stderr = self._run_git([
            "log",
            f"-n {limit}",
            "--format=%h|%s|%ad",
            "--date=short"
        ])

        if not success:
            return {
                "status": "error",
                "error": stderr
            }

        commits = []
        for line in stdout.strip().split('\n'):
            if line:
                parts = line.split('|')
                if len(parts) >= 3:
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                        "date": parts[2]
                    })

        return {
            "status": "success",
            "commits": commits
        }


# 便捷函数
def get_git_diff_tool(repo_path: Optional[str] = None) -> GitDiffTool:
    """获取 Git 差异工具实例"""
    return GitDiffTool(repo_path)
