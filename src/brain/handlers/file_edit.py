"""File Edit Handler - 文件编辑处理器"""
from typing import Any, Dict
from pathlib import Path

from .base import BaseHandler


class FileEditHandler(BaseHandler):
    """文件编辑处理器 - 支持长文件的部分改写

    使用场景：
    - 长文件不需要全部读取再改写
    - 支持指定行范围进行替换
    - 支持在指定位置插入内容
    """

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}

        action = params.get("action", "edit")
        path = params.get("path")

        if not path:
            return {"status": "error", "error_code": 1004, "message": "Missing: path"}

        # 安全性检查
        if not self._is_path_safe(path):
            return {"status": "error", "error_code": 1003, "message": f"Invalid path: {path}"}

        file_path = Path(path)
        if not file_path.exists() and action != "create":
            return {"status": "error", "error_code": 1004, "message": f"File not found: {path}"}

        if action == "edit":
            return self._edit_file(file_path, params)
        elif action == "insert":
            return self._insert_file(file_path, params)
        elif action == "delete_lines":
            return self._delete_lines(file_path, params)
        elif action == "read":
            return self._read_file(file_path, params)
        elif action == "create":
            return self._create_file(file_path, params)
        else:
            return {"status": "error", "error_code": 1005, "message": f"Unknown action: {action}"}

    def _is_path_safe(self, path: str) -> bool:
        """检查路径是否安全"""
        # 禁止访问的路径
        forbidden = ["/etc/", "/proc/", "/sys/", ".env", ".git/"]
        for f in forbidden:
            if f in path:
                return False
        return True

    def _edit_file(self, file_path: Path, params: Dict[str, Any]) -> Dict[str, Any]:
        """编辑文件 - 替换指定行范围的内容

        参数：
        - path: 文件路径
        - start: 起始行号（从 1 开始，包含）
        - end: 结束行号（从 1 开始，包含）
        - content: 新内容
        """
        start = params.get("start", 1)
        end = params.get("end")
        new_content = params.get("content", "")

        try:
            # 读取文件
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 转换为 0-based 索引
            start_idx = max(0, start - 1)
            end_idx = len(lines) if end is None else min(len(lines), end)

            # 替换内容 - 确保每行都有换行符
            new_lines = []
            for line in new_content.split("\n"):
                new_lines.append(line + "\n")
            # 移除最后一个多余的换行符（如果内容本身以换行结尾）
            if new_content.endswith("\n") and new_lines:
                pass  # 保持原样
            elif new_lines:
                new_lines[-1] = new_lines[-1].rstrip("\n")  # 移除最后一个换行符

            # 构建新文件内容
            result_lines = lines[:start_idx] + new_lines + lines[end_idx:]

            # 写回文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(result_lines)

            return {
                "status": "success",
                "action": "edit",
                "path": str(file_path),
                "lines_replaced": end_idx - start_idx,
                "new_lines_added": len(new_lines),
                "message": f"Replaced lines {start}-{end_idx} with {len(new_lines)} lines"
            }
        except Exception as e:
            return {
                "status": "error",
                "error_code": 1006,
                "message": f"Edit failed: {str(e)}"
            }

    def _insert_file(self, file_path: Path, params: Dict[str, Any]) -> Dict[str, Any]:
        """在指定位置插入内容

        参数：
        - path: 文件路径
        - line: 插入位置（行号，从 1 开始）
        - content: 要插入的内容
        - position: "before" 或 "after"（默认"after"）
        """
        line = params.get("line", 1)
        content = params.get("content", "")
        position = params.get("position", "after")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 转换为 0-based 索引
            insert_idx = max(0, line - 1)
            if position == "after":
                insert_idx = min(insert_idx + 1, len(lines))

            # 分割插入内容 - 确保每行都有换行符
            new_lines = []
            for line_content in content.split("\n"):
                new_lines.append(line_content + "\n")
            # 处理最后一个换行符
            if content.endswith("\n") and new_lines:
                pass
            elif new_lines:
                new_lines[-1] = new_lines[-1].rstrip("\n")

            # 插入内容
            result_lines = lines[:insert_idx] + new_lines + lines[insert_idx:]

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(result_lines)

            return {
                "status": "success",
                "action": "insert",
                "path": str(file_path),
                "lines_inserted": len(new_lines),
                "inserted_at": insert_idx + 1,
                "message": f"Inserted {len(new_lines)} lines at line {insert_idx + 1}"
            }
        except Exception as e:
            return {
                "status": "error",
                "error_code": 1006,
                "message": f"Insert failed: {str(e)}"
            }

    def _delete_lines(self, file_path: Path, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除指定行

        参数：
        - path: 文件路径
        - start: 起始行号
        - end: 结束行号（可选，默认只删除 start 行）
        """
        start = params.get("start", 1)
        end = params.get("end", start)

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            start_idx = max(0, start - 1)
            end_idx = min(len(lines), end)

            # 删除行
            result_lines = lines[:start_idx] + lines[end_idx:]

            with open(file_path, "w", encoding="utf-8") as f:
                f.writelines(result_lines)

            return {
                "status": "success",
                "action": "delete_lines",
                "path": str(file_path),
                "lines_deleted": end_idx - start_idx,
                "message": f"Deleted lines {start}-{end_idx}"
            }
        except Exception as e:
            return {
                "status": "error",
                "error_code": 1006,
                "message": f"Delete failed: {str(e)}"
            }

    def _read_file(self, file_path: Path, params: Dict[str, Any]) -> Dict[str, Any]:
        """读取文件（支持指定行范围）

        参数：
        - path: 文件路径
        - start: 起始行号（可选，默认 1）
        - end: 结束行号（可选，默认全部）
        """
        start = params.get("start", 1)
        end = params.get("end")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            start_idx = max(0, start - 1)
            end_idx = len(lines) if end is None else min(len(lines), end)

            selected_lines = lines[start_idx:end_idx]

            return {
                "status": "success",
                "action": "read",
                "path": str(file_path),
                "content": "".join(selected_lines),
                "total_lines": len(lines),
                "read_lines": len(selected_lines),
                "line_range": f"{start_idx + 1}-{end_idx}"
            }
        except Exception as e:
            return {
                "status": "error",
                "error_code": 1006,
                "message": f"Read failed: {str(e)}"
            }

    def _create_file(self, file_path: Path, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建新文件

        参数：
        - path: 文件路径
        - content: 文件内容
        """
        content = params.get("content", "")

        try:
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # 写文件
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {
                "status": "success",
                "action": "create",
                "path": str(file_path),
                "bytes_written": len(content),
                "message": f"Created file: {file_path}"
            }
        except Exception as e:
            return {
                "status": "error",
                "error_code": 1006,
                "message": f"Create failed: {str(e)}"
            }
