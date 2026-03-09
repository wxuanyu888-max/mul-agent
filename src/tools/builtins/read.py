"""Read Tool - 读取文件内容"""

import os
from typing import Optional
from mul_agent.tools.base import SyncTool, ToolMetadata, ToolResult


class ReadTool(SyncTool):
    """Read 工具 - 读取文件内容

    用于读取文件内容，支持：
    - 自动检测文件编码
    - 大文件分块读取
    - 二进制文件检测
    - 路径安全检查
    """

    metadata = ToolMetadata(
        name="read",
        description="读取文件内容。用于查看代码、配置文件、文档等。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径（绝对路径或相对路径）"
                },
                "offset": {
                    "type": "integer",
                    "description": "起始行号（从 1 开始），默认 1"
                },
                "limit": {
                    "type": "integer",
                    "description": "读取行数，默认 2000"
                }
            },
            "required": ["path"]
        },
        examples=[
            {"path": "README.md"},
            {"path": "/Users/agent/project/src/main.py"},
            {"path": "package.json"},
            {"path": "src/utils.ts", "offset": 100, "limit": 50},
        ]
    )

    # 禁止访问的路径模式
    FORBIDDEN_PATTERNS = [
        "/etc/passwd",
        "/etc/shadow",
        "/etc/sudoers",
        "/root/.ssh/",
        ".env",
        ".git/",
        "node_modules/",
        "__pycache__/",
        ".venv/",
        "vendor/",
    ]

    # 最大读取大小（10MB）
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def execute_sync(self, **kwargs) -> ToolResult:
        """读取文件

        Args:
            path: 文件路径
            offset: 起始行号
            limit: 读取行数

        Returns:
            ToolResult: 执行结果
        """
        path = kwargs.get("path", "")
        offset = kwargs.get("offset", 1)
        limit = kwargs.get("limit", 2000)

        # 验证参数
        if not path:
            return ToolResult.error("path is required")

        # 安全检查
        safety_check = self._safety_check(path)
        if not safety_check["safe"]:
            return ToolResult.error(f"Path blocked: {safety_check['reason']}")

        # 解析路径
        file_path = self._resolve_path(path)

        # 检查文件是否存在
        if not os.path.exists(file_path):
            return ToolResult.error(f"File not found: {path}")

        # 检查是否是目录
        if os.path.isdir(file_path):
            return ToolResult.error(f"Path is a directory: {path}")

        # 检查文件大小
        try:
            file_size = os.path.getsize(file_path)
            if file_size > self.MAX_FILE_SIZE:
                return ToolResult.error(
                    f"File too large ({file_size} bytes). Max size: {self.MAX_FILE_SIZE} bytes"
                )
        except OSError as e:
            return ToolResult.error(f"Cannot get file size: {e}")

        try:
            # 读取文件
            content = self._read_file(file_path, offset, limit)

            return ToolResult.success(
                data={
                    "path": path,
                    "content": content,
                    "lines": len(content.split("\n")),
                },
                message=f"Read {len(content)} bytes from {path}"
            )

        except UnicodeDecodeError as e:
            return ToolResult.error(f"Cannot decode file (binary file?): {e}")
        except Exception as e:
            return ToolResult.error(error=str(e))

    def _resolve_path(self, path: str) -> str:
        """解析路径

        将相对路径转换为绝对路径
        """
        if os.path.isabs(path):
            return path
        return os.path.abspath(path)

    def _read_file(self, file_path: str, offset: int, limit: int) -> str:
        """读取文件内容

        支持按行读取，避免大文件内存溢出
        """
        # 检测编码
        encoding = self._detect_encoding(file_path)

        lines = []
        with open(file_path, "r", encoding=encoding, errors="replace") as f:
            # 跳过 offset-1 行
            for _ in range(offset - 1):
                if not f.readline():
                    break

            # 读取 limit 行
            for _ in range(limit):
                line = f.readline()
                if not line:
                    break
                lines.append(line)

        return "".join(lines)

    def _detect_encoding(self, file_path: str) -> str:
        """检测文件编码

        优先尝试 UTF-8，失败则使用系统默认编码
        """
        # 检查扩展名
        ext = os.path.splitext(file_path)[1].lower()
        binary_extensions = [".pyc", ".pyo", ".so", ".dll", ".exe", ".bin"]
        if ext in binary_extensions:
            raise UnicodeDecodeError("", b"", 0, 1, "Binary file detected")

        # 尝试 UTF-8
        try:
            with open(file_path, "rb") as f:
                f.read(1024).decode("utf-8")
            return "utf-8"
        except UnicodeDecodeError:
            pass

        # 回退到系统默认编码
        return os.getenv("LANG", "en_US.UTF-8").split(".")[-1] or "utf-8"

    def _safety_check(self, path: str) -> dict:
        """安全检查"""
        # 规范化路径
        normalized = os.path.normpath(path.lower())

        # 检查禁止的模式
        for pattern in self.FORBIDDEN_PATTERNS:
            if pattern.lower() in normalized:
                return {
                    "safe": False,
                    "reason": f"Path contains forbidden pattern: {pattern}"
                }

        return {"safe": True}
