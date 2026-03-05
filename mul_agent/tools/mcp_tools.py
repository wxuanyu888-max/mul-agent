"""MCP Tool Integrations"""

import subprocess
import os
import re
from typing import Any, Dict, List, Optional
import json


class MCPToolBase:
    """MCP工具基类"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)

    def is_enabled(self) -> bool:
        """检查工具是否启用"""
        return self.enabled

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        """执行工具 - 子类实现"""
        raise NotImplementedError


class ChromeMCP(MCPToolBase):
    """Chrome MCP 工具"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.headless = self.config.get("headless", False)

    def navigate(self, url: str) -> Dict[str, Any]:
        """导航到URL"""
        # This would use the chrome-devtools MCP
        # Placeholder implementation
        return {
            "status": "simulated",
            "action": "navigate",
            "url": url,
            "message": "Chrome MCP would navigate to: " + url
        }

    def click(self, selector: str) -> Dict[str, Any]:
        """点击元素"""
        return {
            "status": "simulated",
            "action": "click",
            "selector": selector,
            "message": "Chrome MCP would click: " + selector
        }

    def fill(self, selector: str, value: str) -> Dict[str, Any]:
        """填写表单"""
        return {
            "status": "simulated",
            "action": "fill",
            "selector": selector,
            "value": value,
            "message": f"Chrome MCP would fill {selector} with: {value}"
        }

    def screenshot(self) -> Dict[str, Any]:
        """截图"""
        return {
            "status": "simulated",
            "action": "screenshot",
            "message": "Chrome MCP would take a screenshot"
        }

    def execute_script(self, script: str) -> Any:
        """执行JavaScript"""
        return {
            "status": "simulated",
            "action": "execute_script",
            "script": script,
            "message": "Chrome MCP would execute JavaScript"
        }

    def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """统一执行入口"""
        action_map = {
            "navigate": self.navigate,
            "click": self.click,
            "fill": self.fill,
            "screenshot": self.screenshot,
            "execute_script": self.execute_script
        }

        if action not in action_map:
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }

        return action_map[action](**kwargs)


class WebSearchMCP(MCPToolBase):
    """Web Search MCP 工具"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.max_results = self.config.get("max_results", 10)

    def search(self, query: str, max_results: Optional[int] = None) -> Dict[str, Any]:
        """搜索网页"""
        if max_results is None:
            max_results = self.max_results

        # This would use actual web search
        # Placeholder implementation
        return {
            "status": "simulated",
            "action": "search",
            "query": query,
            "max_results": max_results,
            "results": [],
            "message": f"Web search would find {max_results} results for: {query}"
        }

    def get_page(self, url: str) -> Dict[str, Any]:
        """获取页面内容"""
        return {
            "status": "simulated",
            "action": "get_page",
            "url": url,
            "content": "",
            "message": f"Web MCP would fetch content from: {url}"
        }

    def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """统一执行入口"""
        action_map = {
            "search": self.search,
            "get_page": self.get_page
        }

        if action not in action_map:
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }

        return action_map[action](**kwargs)


class GrepTool(MCPToolBase):
    """Grep 搜索工具 - 在文件中搜索文本模式"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.max_results = self.config.get("max_results", 100)
        self.default_context = self.config.get("default_context", 2)
        self.allowed_extensions = self.config.get("allowed_extensions", None)
        self.forbidden_paths = self.config.get("forbidden_paths", [
            "/etc/passwd",
            "/etc/shadow",
            ".git/objects",
            "node_modules/",
            "__pycache__/",
            ".venv/"
        ])

    def search(
        self,
        pattern: str,
        path: str = ".",
        file_pattern: str = "*",
        context: int = 2,
        ignore_case: bool = False,
        recursive: bool = True,
        max_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """在文件中搜索模式

        Args:
            pattern: 要搜索的正则表达式或文本
            path: 搜索路径
            file_pattern: 文件名匹配模式 (如 "*.py", "*.js")
            context: 匹配行前后显示的行数
            ignore_case: 是否忽略大小写
            recursive: 是否递归搜索子目录
            max_results: 最大结果数

        Returns:
            搜索结果字典
        """
        if max_results is None:
            max_results = self.max_results

        # 安全性检查
        if not self._is_path_safe(path):
            return {
                "status": "error",
                "message": f"Path not allowed: {path}"
            }

        try:
            # 构建grep命令
            cmd = ["grep"]

            # 添加选项
            if ignore_case:
                cmd.append("-i")
            cmd.extend(["-n"])  # 显示行号
            cmd.extend(["-H"])  # 显示文件名

            # 上下文行数
            if context > 0:
                cmd.extend([f"-C{context}"])
            elif context == 0:
                cmd.extend(["--no-context"])

            # 递归搜索
            if recursive:
                cmd.append("-r")
                cmd.extend(["--include", file_pattern])
            else:
                # 非递归时使用通配符
                if path.endswith("/"):
                    cmd.append(os.path.join(path, file_pattern))
                else:
                    cmd.append(os.path.join(path, "*", file_pattern))

            cmd.append(pattern)

            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.getcwd()
            )

            # 处理输出
            output = result.stdout.strip()
            if not output:
                return {
                    "status": "success",
                    "pattern": pattern,
                    "path": path,
                    "matches": [],
                    "count": 0,
                    "message": f"No matches found for: {pattern}"
                }

            # 解析输出
            matches = self._parse_grep_output(output, max_results)

            return {
                "status": "success",
                "pattern": pattern,
                "path": path,
                "matches": matches["results"],
                "count": matches["count"],
                "total_matches": matches["total"],
                "message": f"Found {matches['count']} matches (showing {len(matches['results'])})"
            }

        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "message": "Search timed out after 30 seconds"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Search failed: {str(e)}"
            }

    def _is_path_safe(self, path: str) -> bool:
        """检查路径是否安全"""
        # 检查禁止路径
        for forbidden in self.forbidden_paths:
            if forbidden in path:
                return False
        return True

    def _parse_grep_output(self, output: str, max_results: int) -> Dict[str, Any]:
        """解析grep输出"""
        lines = output.split("\n")
        results = []
        total = 0

        for line in lines:
            if not line.strip():
                continue

            # 解析格式: filename:line_number:content
            if ":" in line:
                parts = line.split(":", 2)
                if len(parts) >= 3:
                    filename = parts[0]
                    try:
                        line_num = int(parts[1])
                        content = parts[2]
                    except ValueError:
                        # 文件名可能包含冒号
                        filename = ":".join(parts[:-2])
                        try:
                            line_num = int(parts[-2])
                            content = parts[-1]
                        except ValueError:
                            continue

                    results.append({
                        "file": filename,
                        "line": line_num,
                        "content": content
                    })
                    total += 1

                    if len(results) >= max_results:
                        break

        return {
            "results": results,
            "count": len(results),
            "total": total
        }

    def count(
        self,
        pattern: str,
        path: str = ".",
        file_pattern: str = "*",
        ignore_case: bool = False
    ) -> Dict[str, Any]:
        """统计匹配行数"""
        if not self._is_path_safe(path):
            return {
                "status": "error",
                "message": f"Path not allowed: {path}"
            }

        try:
            cmd = ["grep"]
            if ignore_case:
                cmd.append("-i")
            cmd.extend(["-r", "-c", "--include", file_pattern])
            cmd.append(pattern)
            cmd.append(path)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            # 解析输出
            counts = {}
            for line in result.stdout.strip().split("\n"):
                if ":" in line:
                    parts = line.rsplit(":", 1)
                    if len(parts) == 2:
                        counts[parts[0]] = int(parts[1])

            return {
                "status": "success",
                "pattern": pattern,
                "path": path,
                "counts": counts,
                "total": sum(counts.values())
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Count failed: {str(e)}"
            }

    def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """统一执行入口"""
        action_map = {
            "search": self.search,
            "count": self.count
        }

        if action not in action_map:
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }

        return action_map[action](**kwargs)


class MCPToolManager:
    """MCP工具管理器"""

    def __init__(self, user_config: Dict):
        self.user_config = user_config
        self.tools_config = user_config.get("tools", {})
        self.enabled_tools = self.tools_config.get("enabled", [])

        # Initialize tools
        self.tools = {}
        self._init_tools()

    def _init_tools(self):
        """初始化工具"""
        # Chrome MCP
        if "chrome_mcp" in self.enabled_tools:
            chrome_config = self.tools_config.get("chrome_mcp", {})
            self.tools["chrome_mcp"] = ChromeMCP(chrome_config)

        # Web Search MCP
        if "web_search" in self.enabled_tools:
            web_config = self.tools_config.get("web_search", {})
            self.tools["web_search"] = WebSearchMCP(web_config)

        # Grep Tool
        if "grep" in self.enabled_tools:
            grep_config = self.tools_config.get("grep", {})
            self.tools["grep"] = GrepTool(grep_config)

    def execute(self, tool_name: str, action: str, **kwargs) -> Dict[str, Any]:
        """执行工具"""
        if tool_name not in self.tools:
            return {
                "status": "error",
                "message": f"Tool not found: {tool_name}"
            }

        tool = self.tools[tool_name]
        if not tool.is_enabled():
            return {
                "status": "error",
                "message": f"Tool disabled: {tool_name}"
            }

        return tool.execute(action, **kwargs)

    def list_tools(self) -> List[Dict[str, Any]]:
        """列出所有可用工具"""
        return [
            {
                "name": name,
                "enabled": tool.is_enabled(),
                "config": tool.config
            }
            for name, tool in self.tools.items()
        ]
