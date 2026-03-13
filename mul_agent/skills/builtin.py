"""Built-in Skills - 内置技能"""

from .base import BaseSkill


class BashSkill(BaseSkill):
    """Bash 技能 - 执行 bash 命令"""

    skill_id = "bash"
    skill_name = "Bash"
    skill_description = "执行 bash 命令的技能"
    skill_version = "1.0.0"
    skill_tags = ["shell", "command", "execution"]
    priority = 5
    requires_confirmation = True

    def _initialize(self) -> None:
        """初始化 Bash 技能"""
        pass

    def validate_params(self, params: dict) -> bool:
        """验证参数"""
        return "command" in params

    def execute(self, **kwargs) -> dict:
        """执行 bash 命令

        Args:
            command: 要执行的命令
            timeout: 可选的超时时间（秒）

        Returns:
            dict: 执行结果 {stdout, stderr, returncode}
        """
        import subprocess

        command = kwargs.get("command", "")
        timeout = kwargs.get("timeout", 30)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }


class ReadFileSkill(BaseSkill):
    """读取文件技能"""

    skill_id = "read_file"
    skill_name = "Read File"
    skill_description = "读取文件内容的技能"
    skill_version = "1.0.0"
    skill_tags = ["file", "read"]
    priority = 5
    requires_confirmation = False

    def _initialize(self) -> None:
        """初始化读取文件技能"""
        pass

    def validate_params(self, params: dict) -> bool:
        """验证参数"""
        return "path" in params

    def execute(self, **kwargs) -> dict:
        """读取文件

        Args:
            path: 文件路径
            max_lines: 可选的最大行数

        Returns:
            dict: {content, lines, error}
        """
        from pathlib import Path

        path = kwargs.get("path", "")
        max_lines = kwargs.get("max_lines", 1000)

        try:
            file_path = Path(path)
            if not file_path.exists():
                return {
                    "content": "",
                    "lines": 0,
                    "error": f"File not found: {path}"
                }

            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 截断处理
            if len(lines) > max_lines:
                lines = lines[:max_lines]
                lines.append("\n...[内容已截断]\n")

            return {
                "content": "".join(lines),
                "lines": len(lines),
                "error": None,
            }
        except Exception as e:
            return {
                "content": "",
                "lines": 0,
                "error": str(e),
            }


class WriteFileSkill(BaseSkill):
    """写入文件技能"""

    skill_id = "write_file"
    skill_name = "Write File"
    skill_description = "写入文件内容的技能"
    skill_version = "1.0.0"
    skill_tags = ["file", "write"]
    priority = 5
    requires_confirmation = True

    def _initialize(self) -> None:
        """初始化写入文件技能"""
        pass

    def validate_params(self, params: dict) -> bool:
        """验证参数"""
        return "path" in params and "content" in params

    def execute(self, **kwargs) -> dict:
        """写入文件

        Args:
            path: 文件路径
            content: 文件内容

        Returns:
            dict: {success, error}
        """
        from pathlib import Path

        path = kwargs.get("path", "")
        content = kwargs.get("content", "")

        try:
            file_path = Path(path)
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return {
                "success": True,
                "error": None,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


class EditFileSkill(BaseSkill):
    """编辑文件技能"""

    skill_id = "edit_file"
    skill_name = "Edit File"
    skill_description = "编辑文件内容的技能"
    skill_version = "1.0.0"
    skill_tags = ["file", "edit"]
    priority = 5
    requires_confirmation = True

    def _initialize(self) -> None:
        """初始化编辑文件技能"""
        pass

    def validate_params(self, params: dict) -> bool:
        """验证参数"""
        return "path" in params and "old_string" in params and "new_string" in params

    def execute(self, **kwargs) -> dict:
        """编辑文件

        Args:
            path: 文件路径
            old_string: 要替换的字符串
            new_string: 新的字符串

        Returns:
            dict: {success, error, replacements}
        """
        from pathlib import Path

        path = kwargs.get("path", "")
        old_string = kwargs.get("old_string", "")
        new_string = kwargs.get("new_string", "")

        try:
            file_path = Path(path)
            if not file_path.exists():
                return {
                    "success": False,
                    "error": f"File not found: {path}",
                    "replacements": 0,
                }

            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if old_string not in content:
                return {
                    "success": False,
                    "error": "Old string not found in file",
                    "replacements": 0,
                }

            new_content = content.replace(old_string, new_string, 1)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)

            return {
                "success": True,
                "error": None,
                "replacements": 1,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "replacements": 0,
            }


class SearchSkill(BaseSkill):
    """搜索技能"""

    skill_id = "search"
    skill_name = "Search"
    skill_description = "搜索文件和内容的技能"
    skill_version = "1.0.0"
    skill_tags = ["search", "file"]
    priority = 5
    requires_confirmation = False

    def _initialize(self) -> None:
        """初始化搜索技能"""
        pass

    def validate_params(self, params: dict) -> bool:
        """验证参数"""
        return "query" in params

    def execute(self, **kwargs) -> dict:
        """搜索文件

        Args:
            query: 搜索关键词
            path: 搜索路径，默认为当前目录
            file_pattern: 文件模式，如 *.py

        Returns:
            dict: {results, count}
        """
        import subprocess
        from pathlib import Path

        query = kwargs.get("query", "")
        search_path = kwargs.get("path", ".")
        file_pattern = kwargs.get("file_pattern", "*")

        try:
            # 使用 ripgrep 或 grep 搜索
            cmd = ["grep", "-r", "--include", file_pattern, query, search_path]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                return {
                    "results": lines,
                    "count": len(lines),
                    "error": None,
                }
            else:
                return {
                    "results": [],
                    "count": 0,
                    "error": result.stderr or "No matches found",
                }
        except subprocess.TimeoutExpired:
            return {
                "results": [],
                "count": 0,
                "error": "Search timed out",
            }
        except Exception as e:
            return {
                "results": [],
                "count": 0,
                "error": str(e),
            }


__all__ = [
    "BashSkill",
    "ReadFileSkill",
    "WriteFileSkill",
    "EditFileSkill",
    "SearchSkill",
]
