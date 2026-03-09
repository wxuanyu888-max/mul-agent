"""Write Tool - 创建/写入文件"""

import os
from typing import Optional
from mul_agent.tools.base import SyncTool, ToolMetadata, ToolResult


class WriteTool(SyncTool):
    """Write 工具 - 创建或写入文件

    用于创建新文件或覆盖现有文件内容

    安全限制:
    - 禁止覆盖系统关键文件
    - 禁止写入敏感目录
    - 自动创建不存在的目录
    """

    metadata = ToolMetadata(
        name="write",
        description="创建新文件或覆盖现有文件。用于创建代码文件、配置文件等。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径（绝对路径或相对路径）"
                },
                "content": {
                    "type": "string",
                    "description": "文件内容"
                }
            },
            "required": ["path", "content"]
        },
        examples=[
            {"path": "hello.py", "content": "print('Hello, World!')"},
            {"path": "config.json", "content": '{"debug": true}'},
            {"path": "src/utils/helpers.ts", "content": "export function help() {}"},
        ]
    )

    # 禁止写入的路径
    FORBIDDEN_PATHS = [
        "/etc/",
        "/usr/",
        "/bin/",
        "/sbin/",
        "/var/",
        "/root/",
        ".env",
        ".git/",
        "node_modules/",
        "__pycache__/",
        ".venv/",
    ]

    # 最大文件大小（5MB）
    MAX_FILE_SIZE = 5 * 1024 * 1024

    def execute_sync(self, **kwargs) -> ToolResult:
        """写入文件

        Args:
            path: 文件路径
            content: 文件内容

        Returns:
            ToolResult: 执行结果
        """
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")

        # 验证参数
        if not path:
            return ToolResult.error("path is required")
        if not content:
            return ToolResult.error("content is required")

        # 安全检查
        safety_check = self._safety_check(path)
        if not safety_check["safe"]:
            return ToolResult.error(f"Path blocked: {safety_check['reason']}")

        # 解析路径
        file_path = self._resolve_path(path)

        # 检查是否尝试覆盖大文件
        if os.path.exists(file_path):
            try:
                existing_size = os.path.getsize(file_path)
                if existing_size > self.MAX_FILE_SIZE:
                    return ToolResult.error(
                        f"Cannot overwrite large file ({existing_size} bytes)"
                    )
            except OSError:
                pass

        # 检查内容大小
        if len(content.encode("utf-8")) > self.MAX_FILE_SIZE:
            return ToolResult.error(
                f"Content too large ({len(content)} bytes). Max: {self.MAX_FILE_SIZE}"
            )

        try:
            # 创建目录（如果不存在）
            parent_dir = os.path.dirname(file_path)
            if parent_dir and not os.path.exists(parent_dir):
                os.makedirs(parent_dir, exist_ok=True)

            # 写入文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return ToolResult.success(
                data={
                    "path": path,
                    "bytes_written": len(content.encode("utf-8")),
                },
                message=f"Successfully wrote {len(content)} bytes to {path}"
            )

        except PermissionError as e:
            return ToolResult.error(f"Permission denied: {e}")
        except OSError as e:
            return ToolResult.error(f"OS error: {e}")
        except Exception as e:
            return ToolResult.error(error=str(e))

    def _resolve_path(self, path: str) -> str:
        """解析路径"""
        if os.path.isabs(path):
            return path
        return os.path.abspath(path)

    def _safety_check(self, path: str) -> dict:
        """安全检查"""
        normalized = os.path.normpath(path.lower())

        # 检查禁止的路径
        for forbidden in self.FORBIDDEN_PATHS:
            if forbidden.lower() in normalized:
                return {
                    "safe": False,
                    "reason": f"Cannot write to {forbidden}"
                }

        # 检查是否是系统文件
        system_files = [".bashrc", ".bash_profile", ".zshrc", ".profile"]
        basename = os.path.basename(path)
        if basename in system_files:
            return {
                "safe": False,
                "reason": f"Cannot modify system file: {basename}"
            }

        return {"safe": True}
