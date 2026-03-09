"""File Edit Tools - 文件编辑工具 (Patch 模式)

实现 Claude Code 风格的多文件编辑功能：
- search/replace 模式编辑文件
- 支持多文件批量编辑
- 支持 diff 预览
- 自动备份和恢复
"""

import os
import re
import difflib
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from mul_agent.tools.base import SyncTool, ToolMetadata, ToolResult


@dataclass
class FileEdit:
    """文件编辑操作"""
    path: str
    old_content: Optional[str] = None
    new_content: Optional[str] = None
    search_pattern: Optional[str] = None
    replace_text: Optional[str] = None
    action: str = "write"  # write, replace, append, delete


@dataclass
class EditResult:
    """编辑结果"""
    success: bool
    path: str
    action: str
    diff: Optional[str] = None
    backup_path: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FileEditTool(SyncTool):
    """文件编辑工具 - 支持多种编辑模式"""

    metadata = ToolMetadata(
        name="file_edit",
        description="编辑文件内容。支持创建、修改、删除文件。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径"
                },
                "content": {
                    "type": "string",
                    "description": "新内容（用于覆盖或创建）"
                },
                "search": {
                    "type": "string",
                    "description": "搜索模式（用于替换）"
                },
                "replace": {
                    "type": "string",
                    "description": "替换文本"
                },
                "append": {
                    "type": "boolean",
                    "description": "是否追加模式"
                },
                "create_dirs": {
                    "type": "boolean",
                    "description": "是否自动创建目录"
                }
            },
            "required": ["path"]
        },
        examples=[
            {"path": "test.py", "content": "print('hello')"},
            {"path": "config.py", "search": "DEBUG = True", "replace": "DEBUG = False"},
            {"path": "README.md", "append": True, "content": "\n## New Section"},
        ]
    )

    # 备份目录
    BACKUP_DIR = Path("storage/edit_backups")

    # 禁止编辑的文件模式
    FORBIDDEN_PATTERNS = [
        "/etc/*",
        "/usr/*",
        "/bin/*",
        "/sbin/*",
        "*.pyc",
        "*.pyo",
        "*.so",
        "*.dll",
    ]

    def execute_sync(self, **kwargs) -> ToolResult:
        """执行文件编辑

        Args:
            path: 文件路径
            content: 新内容
            search: 搜索模式
            replace: 替换文本
            append: 是否追加
            create_dirs: 是否创建目录

        Returns:
            ToolResult: 编辑结果
        """
        path = kwargs.get("path", "")
        content = kwargs.get("content")
        search = kwargs.get("search")
        replace = kwargs.get("replace")
        append = kwargs.get("append", False)
        create_dirs = kwargs.get("create_dirs", True)

        if not path:
            return ToolResult.error("path is required")

        # 安全检查
        if not self._is_safe_path(path):
            return ToolResult.error(f"Cannot edit file: {path} (forbidden path)")

        try:
            file_path = Path(path)

            # 确定编辑操作类型
            if content is not None and search is None:
                # 覆盖写或创建
                return self._write_file(file_path, content, create_dirs)
            elif search is not None and replace is not None:
                # 搜索替换
                return self._search_replace(file_path, search, replace)
            elif append and content is not None:
                # 追加内容
                return self._append_file(file_path, content)
            else:
                return ToolResult.error("Invalid edit operation. Provide 'content' or 'search'+'replace'")

        except FileNotFoundError as e:
            return ToolResult.error(f"File not found: {e}")
        except PermissionError as e:
            return ToolResult.error(f"Permission denied: {e}")
        except Exception as e:
            return ToolResult.error(f"Edit failed: {str(e)}")

    def _write_file(self, file_path: Path, content: str, create_dirs: bool) -> ToolResult:
        """写入文件（覆盖或创建）"""
        try:
            # 创建目录
            if create_dirs and file_path.parent and not file_path.parent.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)

            # 备份现有文件
            backup_path = None
            if file_path.exists():
                backup_path = self._create_backup(file_path)

            # 读取旧内容（用于 diff）
            old_content = ""
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    old_content = f.read()

            # 写入新内容
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            # 生成 diff
            diff = self._generate_diff(
                str(file_path),
                old_content.splitlines(),
                content.splitlines()
            )

            return ToolResult.success(
                data=EditResult(
                    success=True,
                    path=str(file_path),
                    action="write",
                    diff=diff,
                    backup_path=str(backup_path) if backup_path else None,
                    message=f"Successfully wrote {len(content)} bytes to {file_path}"
                ).to_dict(),
                message=f"Wrote {len(content)} bytes to {file_path}"
            )

        except Exception as e:
            return ToolResult.error(f"Write failed: {str(e)}")

    def _search_replace(self, file_path: Path, search: str, replace: str) -> ToolResult:
        """搜索替换文件内容"""
        if not file_path.exists():
            return ToolResult.error(f"File not found: {file_path}")

        try:
            # 读取文件
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # 备份
            backup_path = self._create_backup(file_path)

            # 执行替换（支持正则）
            try:
                new_content, count = re.subn(search, replace, content)
            except re.error:
                # 回退到普通替换
                new_content = content.replace(search, replace)
                count = 1

            if new_content == content:
                return ToolResult.error("No matches found for the search pattern")

            # 写入新内容
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            # 生成 diff
            diff = self._generate_diff(
                str(file_path),
                content.splitlines(),
                new_content.splitlines()
            )

            return ToolResult.success(
                data=EditResult(
                    success=True,
                    path=str(file_path),
                    action="replace",
                    diff=diff,
                    backup_path=str(backup_path) if backup_path else None,
                    message=f"Replaced {count} occurrence(s) in {file_path}"
                ).to_dict(),
                message=f"Replaced {count} occurrence(s) in {file_path}"
            )

        except Exception as e:
            return ToolResult.error(f"Replace failed: {str(e)}")

    def _append_file(self, file_path: Path, content: str) -> ToolResult:
        """追加内容到文件"""
        try:
            # 备份
            backup_path = None
            old_content = ""
            if file_path.exists():
                backup_path = self._create_backup(file_path)
                with open(file_path, "r", encoding="utf-8") as f:
                    old_content = f.read()
            else:
                # 文件不存在则创建目录
                if file_path.parent and not file_path.parent.exists():
                    file_path.parent.mkdir(parents=True, exist_ok=True)

            # 追加内容
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(content)

            # 读取新内容生成 diff
            with open(file_path, "r", encoding="utf-8") as f:
                new_content = f.read()

            diff = self._generate_diff(
                str(file_path),
                old_content.splitlines(),
                new_content.splitlines()
            )

            return ToolResult.success(
                data=EditResult(
                    success=True,
                    path=str(file_path),
                    action="append",
                    diff=diff,
                    backup_path=str(backup_path) if backup_path else None,
                    message=f"Appended {len(content)} bytes to {file_path}"
                ).to_dict(),
                message=f"Appended {len(content)} bytes to {file_path}"
            )

        except Exception as e:
            return ToolResult.error(f"Append failed: {str(e)}")

    def _create_backup(self, file_path: Path) -> Optional[Path]:
        """创建文件备份"""
        try:
            self.BACKUP_DIR.mkdir(parents=True, exist_ok=True)

            # 生成备份文件名
            timestamp = int(time.time())
            backup_name = f"{file_path.name}.{timestamp}.bak"
            backup_path = self.BACKUP_DIR / backup_name

            # 复制文件
            shutil.copy2(file_path, backup_path)

            return backup_path
        except Exception:
            return None

    def _generate_diff(self, filepath: str, old_lines: List[str], new_lines: List[str]) -> str:
        """生成统一格式 diff"""
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{filepath}",
            tofile=f"b/{filepath}",
            lineterm=""
        )
        return "\n".join(diff)

    def _is_safe_path(self, path: str) -> bool:
        """检查路径是否安全"""
        import fnmatch

        # 规范化路径
        normalized = os.path.normpath(path)

        # 检查禁止模式
        for pattern in self.FORBIDDEN_PATTERNS:
            if fnmatch.fnmatch(normalized, pattern):
                return False

        # 检查系统文件
        system_paths = ["/etc", "/usr", "/bin", "/sbin", "/var", "/root"]
        for sys_path in system_paths:
            if normalized.startswith(sys_path):
                return False

        return True


class MultiFileEditTool(SyncTool):
    """多文件批量编辑工具"""

    metadata = ToolMetadata(
        name="multi_file_edit",
        description="批量编辑多个文件。支持一次性编辑多个文件。",
        input_schema={
            "type": "object",
            "properties": {
                "edits": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"},
                            "search": {"type": "string"},
                            "replace": {"type": "string"}
                        },
                        "required": ["path"]
                    },
                    "description": "编辑操作列表"
                }
            },
            "required": ["edits"]
        },
        examples=[
            {
                "edits": [
                    {"path": "a.py", "content": "# New content"},
                    {"path": "b.py", "search": "old", "replace": "new"}
                ]
            }
        ]
    )

    def __init__(self):
        self.single_edit_tool = FileEditTool()

    def execute_sync(self, **kwargs) -> ToolResult:
        """执行多文件编辑"""
        edits = kwargs.get("edits", [])

        if not edits:
            return ToolResult.error("No edits provided")

        results = []
        success_count = 0
        error_count = 0

        for edit in edits:
            path = edit.get("path")
            if not path:
                results.append({
                    "path": edit.get("path", "unknown"),
                    "success": False,
                    "error": "path is required"
                })
                error_count += 1
                continue

            # 调用单文件编辑工具
            result = self.single_edit_tool.execute_sync(**edit)

            if result.success:
                success_count += 1
            else:
                error_count += 1

            results.append({
                "path": path,
                "success": result.success,
                "error": result.error,
                "message": result.message
            })

        return ToolResult.success(
            data={
                "results": results,
                "success_count": success_count,
                "error_count": error_count,
                "total": len(edits)
            },
            message=f"Multi-file edit: {success_count}/{len(edits)} successful"
        )


# 便捷函数
def quick_edit(path: str, **kwargs) -> ToolResult:
    """快速编辑文件的便捷函数"""
    tool = FileEditTool()
    kwargs["path"] = path
    return tool.execute_sync(**kwargs)


def search_replace(path: str, search: str, replace: str) -> ToolResult:
    """搜索替换的便捷函数"""
    return quick_edit(path, search=search, replace=replace)
