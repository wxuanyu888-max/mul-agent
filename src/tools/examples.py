"""Example Tools - 工具示例

展示如何创建符合新架构的工具
"""

from mul_agent.tools.base import SyncTool, AsyncTool, ToolMetadata, ToolResult, ToolGate


# =============================================================================
# 示例 1: 简单的同步工具
# =============================================================================

class HelloTool(SyncTool):
    """简单的问候工具 - 演示最基本的工具结构"""

    metadata = ToolMetadata(
        name="hello",
        description="返回问候语。用于测试工具系统。",
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "要问候的名字"
                },
                "language": {
                    "type": "string",
                    "description": "语言",
                    "enum": ["en", "zh", "ja"]
                }
            },
            "required": ["name"]
        },
        examples=[
            {"name": "World", "language": "en"},
            {"name": "世界", "language": "zh"},
        ],
        tags=["demo", "test"],
    )

    def execute_sync(self, **kwargs) -> ToolResult:
        """执行问候"""
        name = kwargs.get("name", "World")
        language = kwargs.get("language", "en")

        greetings = {
            "en": f"Hello, {name}!",
            "zh": f"你好，{name}!",
            "ja": f"こんにちは、{name}!",
        }

        greeting = greetings.get(language, greetings["en"])

        return ToolResult.success(
            data={"greeting": greeting},
            message=greeting
        )


# =============================================================================
# 示例 2: 带门控条件的工具
# =============================================================================

class WeatherTool(SyncTool):
    """天气查询工具 - 演示门控条件

    需要:
    - 环境变量：WEATHER_API_KEY
    - 或配置项：weather.api_key
    """

    metadata = ToolMetadata(
        name="weather",
        description="查询天气预报。需要有效的天气 API 密钥。",
        input_schema={
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称"
                },
                "days": {
                    "type": "integer",
                    "description": "预报天数 (1-7)",
                    "default": 1
                }
            },
            "required": ["city"]
        },
        examples=[
            {"city": "Beijing", "days": 3},
            {"city": "Shanghai"},
        ],
        gate=ToolGate(
            env=["WEATHER_API_KEY"],  # 需要环境变量
            os=["darwin", "linux", "win32"],  # 所有平台
        ),
        tags=["weather", "api"],
    )

    def execute_sync(self, **kwargs) -> ToolResult:
        """查询天气"""
        city = kwargs.get("city")
        days = kwargs.get("days", 1)

        # 验证参数
        if not city:
            return ToolResult.error("city is required")

        if days < 1 or days > 7:
            return ToolResult.error("days must be between 1 and 7")

        # 获取 API 密钥
        api_key = self.context.get("config", {}).get("weather", {}).get("api_key")
        if not api_key:
            import os
            api_key = os.environ.get("WEATHER_API_KEY")

        if not api_key:
            return ToolResult.error(
                "WEATHER_API_KEY not configured. "
                "Please set the environment variable or configure weather.api_key"
            )

        # 模拟 API 调用（实际使用时替换为真实 API）
        # import requests
        # response = requests.get(f"https://api.weather.com/...")

        return ToolResult.success(
            data={
                "city": city,
                "temperature": "22°C",
                "condition": "Sunny",
                "forecast": [{"day": i, "temp": f"{20+i}°C"} for i in range(days)]
            },
            message=f"{city} 当前温度 22°C，晴朗"
        )


# =============================================================================
# 示例 3: 异步工具
# =============================================================================

class HttpFetchTool(AsyncTool):
    """HTTP 获取工具 - 演示异步工具"""

    metadata = ToolMetadata(
        name="http_fetch",
        description="获取网页内容。用于抓取公开网页数据。",
        input_schema={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要获取的 URL"
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时时间（秒）",
                    "default": 30
                },
                "headers": {
                    "type": "object",
                    "description": "自定义请求头"
                }
            },
            "required": ["url"]
        },
        examples=[
            {"url": "https://example.com"},
            {"url": "https://api.github.com", "timeout": 10},
        ],
        gate=ToolGate(
            os=["darwin", "linux"],  # 不支持 Windows
        ),
        tags=["web", "http"],
    )

    async def execute_async(self, **kwargs) -> ToolResult:
        """获取网页内容"""
        import aiohttp

        url = kwargs.get("url")
        timeout = kwargs.get("timeout", 30)
        headers = kwargs.get("headers", {})

        if not url:
            return ToolResult.error("url is required")

        if not url.startswith(("http://", "https://")):
            return ToolResult.error("url must start with http:// or https://")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=timeout) as response:
                    content = await response.text()
                    status = response.status

                    return ToolResult.success(
                        data={
                            "url": url,
                            "status": status,
                            "content_length": len(content),
                            "content": content[:5000]  # 限制返回长度
                        },
                        message=f"获取成功 (HTTP {status})"
                    )

        except aiohttp.ClientError as e:
            return ToolResult.error(f"HTTP 请求失败：{e}")
        except asyncio.TimeoutError:
            return ToolResult.error(f"请求超时 ({timeout}秒)")


# =============================================================================
# 示例 4: 需要二进制文件的工具
# =============================================================================

class GitStatusTool(SyncTool):
    """Git 状态工具 - 演示二进制文件门控"""

    metadata = ToolMetadata(
        name="git_status",
        description="显示 Git 仓库状态。需要安装 git。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "仓库路径，默认当前目录"
                },
                "short": {
                    "type": "boolean",
                    "description": "使用简短输出格式",
                    "default": False
                }
            }
        },
        examples=[
            {"path": ".", "short": True},
            {"path": "/path/to/repo"},
        ],
        gate=ToolGate(
            bins=["git"],  # 需要 git 命令
            os=["darwin", "linux", "win32"],
        ),
        tags=["git", "vcs"],
    )

    def execute_sync(self, **kwargs) -> ToolResult:
        """获取 Git 状态"""
        import subprocess

        path = kwargs.get("path", ".")
        short = kwargs.get("short", False)

        try:
            cmd = ["git", "-C", path, "status"]
            if short:
                cmd.append("--short")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return ToolResult.error(
                    f"Git 命令失败：{result.stderr}",
                    data={"returncode": result.returncode}
                )

            return ToolResult.success(
                data={"output": result.stdout},
                message="Git status 获取成功"
            )

        except subprocess.TimeoutExpired:
            return ToolResult.error("Git 命令超时")
        except FileNotFoundError:
            return ToolResult.error("git 命令未安装，请先安装 Git")
        except Exception as e:
            return ToolResult.error(f"执行失败：{e}")


# =============================================================================
# 示例 5: 需要权限的工具
# =============================================================================

class AdminOnlyTool(SyncTool):
    """管理员专用工具 - 演示 owner_only 限制"""

    metadata = ToolMetadata(
        name="admin_action",
        description="执行管理员操作。仅限所有者使用。",
        input_schema={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "要执行的操作",
                    "enum": ["restart", "backup", "cleanup"]
                },
                "confirm": {
                    "type": "boolean",
                    "description": "确认执行危险操作"
                }
            },
            "required": ["action"]
        },
        examples=[
            {"action": "backup", "confirm": True},
        ],
        owner_only=True,  # 仅所有者可用
        sandbox_safe=False,  # 沙箱中不安全
        tags=["admin", "system"],
    )

    def execute_sync(self, **kwargs) -> ToolResult:
        """执行管理员操作"""
        action = kwargs.get("action")
        confirm = kwargs.get("confirm", False)

        # 检查 owner_only（基类会自动检查，但这里可以添加额外逻辑）
        if not self.context.get("sender_is_owner"):
            return ToolResult.error("此操作仅限管理员执行", status=403)

        if action == "restart" and not confirm:
            return ToolResult.error("重启操作需要 confirm=True 确认")

        # 模拟执行
        return ToolResult.success(
            data={"action": action, "status": "completed"},
            message=f"管理员操作 '{action}' 执行完成"
        )


# =============================================================================
# 工具注册示例
# =============================================================================

# 注册这些工具的便捷函数
def register_example_tools(manager):
    """将示例工具注册到工具管理器"""
    from mul_agent.tools.manager import ToolManager

    if isinstance(manager, ToolManager):
        manager.register_tool_class("hello", HelloTool)
        manager.register_tool_class("weather", WeatherTool)
        manager.register_tool_class("http_fetch", HttpFetchTool)
        manager.register_tool_class("git_status", GitStatusTool)
        manager.register_tool_class("admin_action", AdminOnlyTool)


# 用于测试的主函数
if __name__ == "__main__":
    from mul_agent.tools.manager import ToolManager, ToolContext
    from mul_agent.tools.policy import ToolPolicy

    # 创建测试上下文
    context = ToolContext(
        agent_id="test",
        workspace_dir=".",
        sender_is_owner=True,
    )

    # 创建管理器
    policy = ToolPolicy.from_profile("full")
    manager = ToolManager(context, policy)

    # 注册示例工具
    register_example_tools(manager)

    # 测试 HelloTool
    print("\n=== 测试 HelloTool ===")
    result = manager.execute("hello", name="World", language="zh")
    print(result.to_dict())

    # 测试 GitStatusTool
    print("\n=== 测试 GitStatusTool ===")
    result = manager.execute("git_status", path=".", short=True)
    print(result.to_dict())

    # 列出所有可用工具
    print("\n=== 可用工具列表 ===")
    tools = manager.list_tools()
    for tool in tools:
        print(f"  - {tool['name']}: {tool['description']}")
