"""Grep Handler - 文件内容搜索处理器"""
from typing import Any, Dict, List, Optional
from pathlib import Path
import re
import fnmatch

from .base import BaseHandler


class GrepHandler(BaseHandler):
    """文件内容搜索处理器

    使用场景:
    - 在文件内容中搜索文本模式
    - 支持正则表达式
    - 支持显示上下文行数
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

    # 二进制文件扩展名
    BINARY_EXTENSIONS = [
        ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin",
        ".jpg", ".jpeg", ".png", ".gif", ".ico", ".webp",
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".zip", ".tar", ".gz", ".rar",
    ]

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}

        pattern = params.get("pattern")
        path = params.get("path", ".")
        file_pattern = params.get("file_pattern", "*")
        ignore_case = params.get("ignore_case", False)
        context = params.get("context", 0)
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

        try:
            # 编译正则表达式
            flags = re.IGNORECASE if ignore_case else 0
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return {"status": "error", "error_code": 1004, "message": f"Invalid regex pattern: {e}"}

            # 执行搜索
            results = self._grep(regex, path, file_pattern, context, max_results)

            return {
                "status": "success",
                "pattern": pattern,
                "path": path,
                "matches": results["matches"],
                "count": results["count"],
                "total": results["total"]
            }
        except Exception as e:
            return {
                "status": "error",
                "error_code": 1006,
                "message": f"Grep failed: {str(e)}"
            }

    def _is_path_safe(self, path: str) -> bool:
        """检查路径是否安全"""
        normalized = path.lower()
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern.lower() in normalized:
                return False
        return True

    def _grep(
        self,
        regex: re.Pattern,
        path: str,
        file_pattern: str,
        context: int,
        max_results: int
    ) -> Dict[str, Any]:
        """执行 grep 搜索"""
        matches = []
        total = 0
        path_obj = Path(path)

        # 遍历目录
        for root, dirs, files in path_obj.walk():
            # 跳过排除的目录
            dirs[:] = [
                d for d in dirs
                if not any(fp in str(Path(root) / d) for fp in self.FORBIDDEN_PATTERNS)
            ]

            for filename in files:
                # 检查文件名模式
                if file_pattern != "*" and not fnmatch.fnmatch(filename, file_pattern):
                    continue

                # 跳过二进制文件
                ext = Path(filename).suffix.lower()
                if ext in self.BINARY_EXTENSIONS:
                    continue

                full_path = Path(root) / filename

                try:
                    file_matches = self._search_file(full_path, regex, context, max_results - len(matches), path_obj)
                    for match in file_matches:
                        matches.append(match)
                        total += 1

                        if len(matches) >= max_results:
                            break
                except (PermissionError, UnicodeDecodeError):
                    # 跳过无法读取的文件
                    pass

                if len(matches) >= max_results:
                    break

            if len(matches) >= max_results:
                break

        return {
            "matches": matches,
            "count": len(matches),
            "total": total
        }

    def _search_file(
        self,
        file_path: Path,
        regex: re.Pattern,
        context: int,
        remaining: int,
        base_path: Path = None
    ) -> List[Dict[str, Any]]:
        """搜索单个文件"""
        matches = []
        # 使用 base_path 计算相对路径，避免跨目录问题
        try:
            if base_path:
                rel_path = str(file_path.relative_to(base_path))
            else:
                rel_path = str(file_path)
        except ValueError:
            # 如果不在 base_path 子路径中，使用绝对路径
            rel_path = str(file_path)

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except (IOError, OSError):
            return []

        for line_num, line in enumerate(lines, 1):
            match = regex.search(line)
            if match:
                # 获取上下文
                start = max(0, line_num - context - 1)
                end = min(len(lines), line_num + context)
                context_lines = [
                    {"line": start + i + 1, "content": lines[start + i].rstrip()}
                    for i in range(end - start)
                ]

                matches.append({
                    "file": rel_path,
                    "line": line_num,
                    "match": line.rstrip(),
                    "context": context_lines if context > 0 else None,
                    "groups": match.groups()
                })

                if len(matches) >= remaining:
                    break

        return matches
