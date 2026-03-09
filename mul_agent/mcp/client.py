"""MCP (Model Context Protocol) Client - MCP 客户端

参考 Anthropic 的 MCP 协议设计：
1. 发现 MCP 服务器并连接
2. 获取服务器提供的工具列表
3. 调用远程工具
4. 支持多种传输方式（stdio, SSE, WebSocket）
"""

import asyncio
import json
import subprocess
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
from pathlib import Path

# 可选的 aiohttp 依赖
try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    aiohttp = None


class MCPServerStatus(Enum):
    """MCP 服务器状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class MCPServerConfig:
    """MCP 服务器配置"""
    name: str
    command: Optional[str] = None  # stdio 模式的可执行命令
    args: List[str] = field(default_factory=list)
    url: Optional[str] = None  # SSE/HTTP 模式的 URL
    transport: str = "stdio"  # stdio, sse, http
    env: Dict[str, str] = field(default_factory=dict)
    timeout: int = 30


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "server": self.server_name
        }


class MCPServer:
    """MCP 服务器连接"""

    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.status = MCPServerStatus.DISCONNECTED
        self.tools: List[MCPTool] = []
        self._process: Optional[subprocess.Popen] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._request_id = 0

    async def connect(self) -> bool:
        """连接到 MCP 服务器"""
        try:
            if self.config.transport == "stdio":
                return await self._connect_stdio()
            elif self.config.transport in ("sse", "http"):
                return await self._connect_http()
            else:
                raise ValueError(f"Unknown transport: {self.config.transport}")
        except Exception as e:
            self.status = MCPServerStatus.ERROR
            print(f"MCP server {self.config.name} connection error: {e}")
            return False

    async def _connect_stdio(self) -> bool:
        """通过 stdio 连接 MCP 服务器"""
        try:
            self._process = subprocess.Popen(
                [self.config.command] + self.config.args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env={**Path.cwd().as_posix(), **self.config.env},
            )
            self.status = MCPServerStatus.CONNECTED

            # 获取工具列表
            await self._list_tools()
            return True
        except Exception as e:
            self.status = MCPServerStatus.ERROR
            raise e

    async def _connect_http(self) -> bool:
        """通过 HTTP/SSE 连接 MCP 服务器"""
        if not HAS_AIOHTTP:
            raise RuntimeError("aiohttp is required for HTTP/SSE transport. Install with: pip install aiohttp")

        try:
            self._session = aiohttp.ClientSession()
            self.status = MCPServerStatus.CONNECTED

            # 获取工具列表
            await self._list_tools()
            return True
        except Exception as e:
            self.status = MCPServerStatus.ERROR
            raise e

    async def disconnect(self):
        """断开连接"""
        if self._process:
            self._process.terminate()
        if self._session:
            await self._session.close()
        self.status = MCPServerStatus.DISCONNECTED

    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """发送 JSON-RPC 请求"""
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or {}
        }

        if self.config.transport == "stdio" and self._process:
            # stdio 传输
            request_bytes = (json.dumps(request) + "\n").encode('utf-8')
            self._process.stdin.write(request_bytes)
            self._process.stdin.flush()

            # 读取响应
            response_line = self._process.stdout.readline()
            response = json.loads(response_line.decode('utf-8'))
            return response

        elif self.config.transport in ("sse", "http") and self._session:
            # HTTP 传输
            async with self._session.post(
                self.config.url or "http://localhost:8080",
                json=request,
                headers={"Content-Type": "application/json"}
            ) as resp:
                return await resp.json()

        raise RuntimeError("Not connected")

    async def _list_tools(self):
        """获取服务器提供的工具列表"""
        response = await self._send_request("tools/list")

        if "result" in response and "tools" in response["result"]:
            self.tools = [
                MCPTool(
                    name=tool.get("name", ""),
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {}),
                    server_name=self.config.name
                )
                for tool in response["result"]["tools"]
            ]

    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """调用远程工具

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            Dict: 工具执行结果
        """
        response = await self._send_request(
            "tools/call",
            {
                "name": tool_name,
                "arguments": kwargs
            }
        )

        if "error" in response:
            return {
                "success": False,
                "error": response["error"].get("message", "Unknown error")
            }

        return {
            "success": True,
            "data": response.get("result", {}),
            "content": response.get("result", {}).get("content", [])
        }

    def get_tool_definition(self, tool_name: str) -> Optional[MCPTool]:
        """获取工具定义"""
        for tool in self.tools:
            if tool.name == tool_name:
                return tool
        return None


class MCPClient:
    """MCP 客户端 - 管理多个 MCP 服务器连接"""

    def __init__(self):
        self.servers: Dict[str, MCPServer] = {}
        self._lock = threading.Lock()
        self._initialized = False

    def add_server(self, config: MCPServerConfig) -> bool:
        """添加 MCP 服务器配置

        Args:
            config: 服务器配置

        Returns:
            bool: 是否添加成功
        """
        with self._lock:
            if config.name in self.servers:
                return False

            server = MCPServer(config)
            self.servers[config.name] = server
            return True

    def remove_server(self, name: str) -> bool:
        """移除 MCP 服务器"""
        with self._lock:
            if name in self.servers:
                del self.servers[name]
                return True
            return False

    async def connect_server(self, name: str) -> bool:
        """连接到指定的 MCP 服务器

        Args:
            name: 服务器名称

        Returns:
            bool: 是否连接成功
        """
        server = self.servers.get(name)
        if not server:
            return False

        return await server.connect()

    async def connect_all(self) -> Dict[str, bool]:
        """连接所有 MCP 服务器

        Returns:
            Dict: 各服务器的连接结果
        """
        results = {}
        for name, server in self.servers.items():
            results[name] = await server.connect()
        return results

    async def disconnect_server(self, name: str) -> bool:
        """断开指定服务器连接"""
        server = self.servers.get(name)
        if not server:
            return False

        await server.disconnect()
        return True

    async def disconnect_all(self):
        """断开所有连接"""
        for server in self.servers.values():
            await server.disconnect()

    def list_tools(self) -> List[MCPTool]:
        """列出所有可用的 MCP 工具"""
        all_tools = []
        for server in self.servers.values():
            if server.status == MCPServerStatus.CONNECTED:
                all_tools.extend(server.tools)
        return all_tools

    def get_tools_prompt(self) -> str:
        """生成 MCP 工具列表提示词"""
        tools = self.list_tools()
        if not tools:
            return "没有可用的 MCP 工具。"

        lines = ["## MCP 工具\n"]
        for tool in tools:
            lines.append(f"### {tool.name} (来自：{tool.server_name})")
            lines.append(f"{tool.description}\n")
            lines.append(f"**输入 Schema**: {json.dumps(tool.input_schema, ensure_ascii=False)}\n")
            lines.append("")

        return "\n".join(lines)

    async def call_tool(self, tool_name: str, server_name: str = None, **kwargs) -> Dict[str, Any]:
        """调用 MCP 工具

        Args:
            tool_name: 工具名称
            server_name: 服务器名称（可选，如果工具名唯一可省略）
            **kwargs: 工具参数

        Returns:
            Dict: 执行结果
        """
        # 确定要调用的服务器
        if server_name:
            server = self.servers.get(server_name)
        else:
            # 查找第一个有该工具的服务器
            server = None
            for s in self.servers.values():
                if s.get_tool_definition(tool_name):
                    server = s
                    break

        if not server:
            return {"success": False, "error": f"Server not found for tool: {tool_name}"}

        if server.status != MCPServerStatus.CONNECTED:
            return {"success": False, "error": f"Server not connected: {server.config.name}"}

        return await server.call_tool(tool_name, **kwargs)

    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有服务器状态"""
        status = {}
        for name, server in self.servers.items():
            status[name] = {
                "status": server.status.value,
                "tools_count": len(server.tools),
                "transport": server.config.transport,
                "url": server.config.url or server.config.command
            }
        return status


# 预定义的 MCP 服务器配置
BUILTIN_MCP_SERVERS = {
    "filesystem": MCPServerConfig(
        name="filesystem",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem"],
        transport="stdio"
    ),
    "github": MCPServerConfig(
        name="github",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-github"],
        transport="stdio"
    ),
    "postgres": MCPServerConfig(
        name="postgres",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-postgres"],
        transport="stdio"
    ),
    "slack": MCPServerConfig(
        name="slack",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-slack"],
        transport="stdio"
    ),
}


# 全局客户端实例
_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    """获取 MCP 客户端单例"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client


# 便捷函数
async def init_mcp_servers(server_configs: List[MCPServerConfig] = None) -> Dict[str, bool]:
    """初始化并连接所有 MCP 服务器"""
    client = get_mcp_client()

    # 添加内置服务器
    if server_configs is None:
        server_configs = list(BUILTIN_MCP_SERVERS.values())

    for config in server_configs:
        client.add_server(config)

    return await client.connect_all()


async def call_mcp_tool(tool_name: str, server_name: str = None, **kwargs) -> Dict[str, Any]:
    """便捷调用 MCP 工具"""
    client = get_mcp_client()
    return await client.call_tool(tool_name, server_name, **kwargs)


def list_mcp_tools() -> List[MCPTool]:
    """列出所有可用的 MCP 工具"""
    client = get_mcp_client()
    return client.list_tools()
