"""Built-in Skills - 内置技能"""

from typing import Any, Dict, List
from mul_agent.skills.base import BaseSkill
from mul_agent.brain.handlers.bash import BashHandler
from mul_agent.brain.handlers.memory import MemoryHandler
from mul_agent.brain.handlers.chat import ChatHandler


class BashSkill(BaseSkill):
    """Bash 执行技能"""

    skill_id = "bash_executor"
    skill_name = "Bash Executor"
    skill_version = "1.0.0"
    skill_description = "Execute shell commands and analyze output"
    skill_tags = ["shell", "command", "execution", "system"]
    priority = 8

    def _initialize(self) -> None:
        """初始化"""
        self.handler = BashHandler(self.config_manager, self.agent_id)

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        return "command" in params

    def execute(self, command: str, timeout: int = 30, cwd: str = None) -> Dict[str, Any]:
        """执行 bash 命令

        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）
            cwd: 工作目录

        Returns:
            Dict: 执行结果
        """
        result = self.handler.handle({
            "command": command,
            "timeout": timeout,
            "cwd": cwd
        })
        return result


class MemorySkill(BaseSkill):
    """记忆管理技能"""

    skill_id = "memory_manager"
    skill_name = "Memory Manager"
    skill_version = "1.0.0"
    skill_description = "Manage short-term and long-term memory"
    skill_tags = ["memory", "storage", "retrieval"]
    priority = 7

    def _initialize(self) -> None:
        """初始化"""
        self.handler = MemoryHandler(self.config_manager, self.agent_id)

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        action = params.get("action")
        return action in ["list", "read", "write", "delete", "search"]

    def execute(
        self,
        action: str,
        memory_type: str = "short_term",
        content: Any = None,
        query: str = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """执行记忆操作

        Args:
            action: 操作类型 (list/read/write/delete/search)
            memory_type: 记忆类型 (short_term/long_term/handover)
            content: 写入的内容
            query: 搜索关键词
            limit: 返回数量限制

        Returns:
            Dict: 操作结果
        """
        params = {
            "action": action,
            "memory_type": memory_type
        }
        if content:
            params["content"] = content
        if query:
            params["query"] = query
        if limit:
            params["limit"] = limit

        return self.handler.handle(params)


class ChatSkill(BaseSkill):
    """Agent 对话技能"""

    skill_id = "agent_chat"
    skill_name = "Agent Chat"
    skill_version = "1.0.0"
    skill_description = "Communicate with other agents"
    skill_tags = ["chat", "communication", "agent", "collaboration"]
    priority = 6

    def _initialize(self) -> None:
        """初始化"""
        self.handler = ChatHandler(self.config_manager, self.agent_id)

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        return "agent_id" in params and "message" in params

    def execute(
        self,
        agent_id: str,
        message: str,
        action: str = "send"
    ) -> Dict[str, Any]:
        """与其他 Agent 对话

        Args:
            agent_id: 目标 Agent ID
            message: 消息内容
            action: 操作类型 (send/receive/list)

        Returns:
            Dict: 对话结果
        """
        params = {
            "action": action,
            "agent_id": agent_id,
            "message": message
        }
        return self.handler.handle(params)


class CodeSkill(BaseSkill):
    """代码执行技能"""

    skill_id = "code_executor"
    skill_name = "Code Executor"
    skill_version = "1.0.0"
    skill_description = "Execute and analyze code"
    skill_tags = ["code", "execution", "analysis", "programming"]
    priority = 8

    def _initialize(self) -> None:
        """初始化"""
        pass

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        return "code" in params or "file_path" in params

    def execute(
        self,
        code: str = None,
        file_path: str = None,
        language: str = "python",
        args: List[str] = None
    ) -> Dict[str, Any]:
        """执行代码

        Args:
            code: 要执行的代码
            file_path: 代码文件路径
            language: 编程语言
            args: 命令行参数

        Returns:
            Dict: 执行结果
        """
        # TODO: 实现代码执行逻辑
        return {
            "status": "success",
            "output": f"Code execution not yet implemented for {language}"
        }


class SearchSkill(BaseSkill):
    """搜索技能"""

    skill_id = "searcher"
    skill_name = "Searcher"
    skill_version = "1.0.0"
    skill_description = "Search files and content"
    skill_tags = ["search", "file", "content", "grep"]
    priority = 7

    def _initialize(self) -> None:
        """初始化"""
        pass

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        return "pattern" in params or "query" in params

    def execute(
        self,
        pattern: str = None,
        query: str = None,
        path: str = ".",
        file_type: str = None,
        max_results: int = 100
    ) -> Dict[str, Any]:
        """搜索内容

        Args:
            pattern: 文件模式
            query: 搜索关键词
            path: 搜索路径
            file_type: 文件类型
            max_results: 最大结果数

        Returns:
            Dict: 搜索结果
        """
        import subprocess
        import os

        try:
            cmd = ["grep", "-r"]
            if max_results:
                cmd.extend(["-m", str(max_results)])
            if path:
                cmd.append(path)

            if query:
                cmd.insert(2, query)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            return {
                "status": "success",
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }


class ProjectExplorer(BaseSkill):
    """项目探索技能 - 主动探索项目结构"""

    skill_id = "project_explorer"
    skill_name = "Project Explorer"
    skill_version = "1.0.0"
    skill_description = "Autonomously explore project structure and generate analysis report"
    skill_tags = ["explore", "project", "analysis", "filesystem"]
    priority = 9

    def _initialize(self) -> None:
        """初始化"""
        self.handler = BashHandler(self.config_manager, self.agent_id)

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """验证参数"""
        # 所有参数都是可选的，有默认行为
        return True

    def execute(
        self,
        path: str = ".",
        depth: int = 2,
        include_hidden: bool = False,
        analyze: bool = True
    ) -> Dict[str, Any]:
        """探索项目结构

        Args:
            path: 要探索的路径（默认当前目录）
            depth: 探索深度（默认 2 层）
            include_hidden: 是否包含隐藏文件
            analyze: 是否进行深度分析

        Returns:
            Dict: 项目结构和分析结果
        """
        result = {
            "status": "success",
            "path": path,
            "structure": {},
            "analysis": {}
        }

        # 1. 列出目录结构
        ls_cmd = f"ls -la {path}"
        ls_result = self._run_command(ls_cmd)

        # 2. 使用 tree 或 find 获取结构
        if self._check_tree_available():
            tree_cmd = f"tree -L {depth} {path}"
            if not include_hidden:
                tree_cmd += " -I '.*'"
            tree_result = self._run_command(tree_cmd)
            result["structure"]["tree"] = tree_result.get("stdout", "")
        else:
            # Fallback 到 find
            find_cmd = f"find {path} -maxdepth {depth} -type f"
            if not include_hidden:
                find_cmd += " ! -name '.*'"
            find_result = self._run_command(find_cmd)
            result["structure"]["files"] = find_result.get("stdout", "").strip().split("\n")

        # 3. 识别项目类型
        project_type = self._detect_project_type(path)
        result["analysis"]["project_type"] = project_type

        # 4. 深度分析（如果启用）
        if analyze:
            result["analysis"]["details"] = self._analyze_project(path, project_type)

        return result

    def _run_command(self, command: str) -> Dict[str, Any]:
        """运行 bash 命令"""
        return self.handler.handle({"command": command, "timeout": 30})

    def _check_tree_available(self) -> bool:
        """检查 tree 命令是否可用"""
        result = self._run_command("which tree")
        return result.get("returncode", 1) == 0

    def _detect_project_type(self, path: str) -> str:
        """检测项目类型"""
        indicators = {
            "python": ["requirements.txt", "setup.py", "pyproject.toml", ".py"],
            "node": ["package.json", "node_modules", ".js", ".ts"],
            "rust": ["Cargo.toml", ".rs"],
            "go": ["go.mod", "go.sum", ".go"],
            "java": ["pom.xml", "build.gradle", ".java"],
        }

        # 检查目录中是否有特征文件
        for project_type, markers in indicators.items():
            for marker in markers:
                if marker.startswith("."):
                    # 检查文件扩展名
                    check_cmd = f"find {path} -maxdepth 2 -name '*{marker}' | head -1"
                else:
                    # 检查文件是否存在
                    check_cmd = f"test -f {path}/{marker} && echo 'found'"

                result = self._run_command(check_cmd)
                if result.get("stdout", "").strip() or result.get("returncode", 1) == 0:
                    return project_type

        return "unknown"

    def _analyze_project(self, path: str, project_type: str) -> Dict[str, Any]:
        """深度分析项目"""
        analysis = {
            "files_count": 0,
            "dirs_count": 0,
            "key_files": [],
            "tech_stack": []
        }

        # 统计文件和目录
        count_result = self._run_command(f"find {path} -maxdepth 3 -type f | wc -l")
        try:
            analysis["files_count"] = int(count_result.get("stdout", "0").strip())
        except ValueError:
            pass

        dir_result = self._run_command(f"find {path} -maxdepth 3 -type d | wc -l")
        try:
            analysis["dirs_count"] = int(dir_result.get("stdout", "0").strip())
        except ValueError:
            pass

        # 根据项目类型识别关键文件和技术栈
        if project_type == "python":
            analysis["key_files"] = self._find_key_files(path, [
                "main.py", "app.py", "__init__.py", "requirements.txt",
                "pyproject.toml", "setup.py", "Dockerfile"
            ])
            analysis["tech_stack"] = self._extract_python_deps(path)

        elif project_type == "node":
            analysis["key_files"] = self._find_key_files(path, [
                "package.json", "index.js", "index.ts", "tsconfig.json",
                "next.config.js", "vite.config.js"
            ])
            analysis["tech_stack"] = self._extract_node_deps(path)

        return analysis

    def _find_key_files(self, path: str, filenames: List[str]) -> List[str]:
        """查找关键文件"""
        found = []
        for filename in filenames:
            result = self._run_command(f"test -f {path}/{filename} && echo '{filename}'")
            if result.get("stdout", "").strip():
                found.append(filename)
        return found

    def _extract_python_deps(self, path: str) -> List[str]:
        """提取 Python 依赖"""
        deps = []

        # 尝试读取 requirements.txt
        result = self._run_command(f"cat {path}/requirements.txt 2>/dev/null | head -20")
        if result.get("stdout"):
            deps = [line.split("==")[0].strip() for line in result["stdout"].split("\n") if line.strip()]

        # 或者读取 pyproject.toml
        if not deps:
            result = self._run_command(f"grep -E '^\\w' {path}/pyproject.toml 2>/dev/null | head -20")
            if result.get("stdout"):
                deps = result["stdout"].split("\n")

        return deps[:10]  # 只返回前 10 个

    def _extract_node_deps(self, path: str) -> List[str]:
        """提取 Node.js 依赖"""
        deps = []

        # 读取 package.json 中的 dependencies
        result = self._run_command(f"cat {path}/package.json 2>/dev/null")
        if result.get("stdout"):
            import json
            try:
                pkg = json.loads(result["stdout"])
                deps = list(pkg.get("dependencies", {}).keys())[:10]
            except json.JSONDecodeError:
                pass

        return deps
