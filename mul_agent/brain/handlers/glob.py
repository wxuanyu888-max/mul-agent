"""Glob Handler - 文件名模式匹配处理器"""
from typing import Any, Dict, List
from pathlib import Path
import fnmatch

from .base import BaseHandler


class GlobHandler(BaseHandler):
    """文件名模式匹配处理器

    使用场景:
    - 搜索匹配特定模式的文件
    - 支持通配符 (*, ?, [])
    - 支持递归搜索
    """

    # 禁止访问的路径
    FORBIDDEN_PATTERNS = [
        "/etc/",
        "/proc/",
        "/sys/",
        ".git/objects/",
        "node_modules/",
        "__pycache__/",
        ".venv/",
    ]

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}

        pattern = params.get("pattern")
        path = params.get("path", ".")
        recursive = params.get("recursive", True)
        exclude = params.get("exclude")
        max_results = params.get("max_results", 100)

        if not pattern:
            return {"status": "error", "error_code": 1004, "message": "Missing: pattern"}

        # 安全性检查
        if not self._is_path_safe(path):
            return {"status": "error", "error_code": 1003, "message": f"Path not allowed: {path}"}

        # 检查路径是否存在
        path_obj = Path(path)
        if not path_obj.exists():
            return {"status": "error", "error_code": 1004, "message": f"Path not found: {path}"}

        if not path_obj.is_dir():
            return {"status": "error", "error_code": 1004, "message": f"Not a directory: {path}"}

        try:
            matches = self._glob(pattern, path, recursive, exclude, max_results)

            return {
                "status": "success",
                "pattern": pattern,
                "path": path,
                "files": matches["files"],
                "count": matches["count"],
                "total": matches["total"]
            }
        except Exception as e:
            return {
                "status": "error",
                "error_code": 1006,
                "message": f"Glob failed: {str(e)}"
            }

    def _is_path_safe(self, path: str) -> bool:
        """检查路径是否安全"""
        normalized = path.lower()
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern.lower() in normalized:
                return False
        return True

    def _glob(
        self,
        pattern: str,
        path: str,
        recursive: bool,
        exclude: str = None,
        max_results: int = 100
    ) -> Dict[str, Any]:
        """执行 glob 搜索"""
        matches = []
        total = 0
        path_obj = Path(path)

        # 解析模式
        if pattern.startswith("**/"):
            recursive = True
            pattern = pattern[3:]

        # 遍历目录
        if recursive:
            for root, dirs, files in path_obj.walk():
                # 跳过排除的目录
                if exclude:
                    dirs[:] = [
                        d for d in dirs
                        if not fnmatch.fnmatch(d, exclude.rstrip("/*"))
                    ]

                # 跳过禁止的目录
                dirs[:] = [
                    d for d in dirs
                    if not any(fp in str(Path(root) / d) for fp in self.FORBIDDEN_PATTERNS)
                ]

                for filename in files:
                    if fnmatch.fnmatch(filename, pattern):
                        full_path = Path(root) / filename
                        rel_path = full_path.relative_to(path_obj)
                        matches.append(str(rel_path))
                        total += 1

                        if len(matches) >= max_results:
                            break

                if len(matches) >= max_results:
                    break
        else:
            # 非递归搜索
            try:
                entries = list(path_obj.iterdir())
                for entry in entries:
                    if entry.is_file() and fnmatch.fnmatch(entry.name, pattern):
                        matches.append(entry.name)
                        total += 1

                        if len(matches) >= max_results:
                            break
            except PermissionError:
                pass

        return {
            "files": sorted(matches),
            "count": len(matches),
            "total": total
        }
