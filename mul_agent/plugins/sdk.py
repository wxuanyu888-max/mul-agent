"""
Plugin SDK - 插件开发接口

使用示例:

```python
# 插件入口 (plugin_name/__init__.py)
from mul_agent.plugins import PluginAPI, PluginManifest

def plugin_init(api: PluginAPI) -> PluginManifest:
    # 注册工具
    @api.register_tool(
        name="my_tool",
        description="我的工具",
        schema={"type": "object", "properties": {"input": {"type": "string"}}}
    )
    async def my_tool(input: str) -> dict:
        return {"result": f"Processed: {input}"}

    # 注册 Hook
    @api.register_hook(phase="pre_tool_use", name="log_tool_use")
    async def log_tool_use(context):
        print(f"Tool about to be used: {context.data.get('tool_name')}")
        return context

    return PluginManifest(
        name="my-plugin",
        version="1.0.0",
        description="我的插件",
        author="Author Name",
        entry=__file__,
    )
```
"""

from typing import Any, Callable, Awaitable, Optional, List
from dataclasses import dataclass, field
import functools

from mul_agent.plugins.types import (
    PluginManifest,
    PluginContext,
    ToolRegistry,
    HookRegistry,
    CommandRegistry,
)


class PluginAPI:
    """插件 API 接口实现"""

    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        hook_registry: Optional[HookRegistry] = None,
        command_registry: Optional[CommandRegistry] = None,
    ):
        self._tool_registry = tool_registry or ToolRegistry()
        self._hook_registry = hook_registry or HookRegistry()
        self._command_registry = command_registry or CommandRegistry()
        self._plugins: List[PluginManifest] = []

    # ========== 工具注册 ==========

    def register_tool(
        self,
        name: Optional[str] = None,
        description: str = "",
        schema: Optional[dict] = None,
        optional: bool = False,
    ) -> Callable[[Callable], Callable]:
        """
        注册工具的装饰器

        Args:
            name: 工具名称（默认使用函数名）
            description: 工具描述
            schema: JSON Schema 参数定义
            optional: 是否为可选工具（需要用户显式启用）

        Returns:
            装饰器函数
        """
        def decorator(func: Callable) -> Callable:
            tool_name = name or func.__name__

            # 默认 schema
            if schema is None:
                schema = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }

            # 注册到工具注册表
            self._tool_registry.register(
                name=tool_name,
                description=description,
                schema=schema,
                handler=func,
                optional=optional,
            )

            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    # ========== Hook 注册 ==========

    def register_hook(
        self,
        phase: str,
        name: Optional[str] = None,
        priority: int = 0,
    ) -> Callable[[Callable], Callable]:
        """
        注册 Hook 的装饰器

        Args:
            phase: Hook 阶段 (pre_tool_use, post_tool_use, etc.)
            name: Hook 名称（默认使用函数名）
            priority: 优先级（数字越大越先执行）

        Returns:
            装饰器函数
        """
        def decorator(func: Callable) -> Callable:
            hook_name = name or func.__name__

            self._hook_registry.register(
                name=hook_name,
                phase=phase,
                handler=func,
                priority=priority,
            )

            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    # ========== 命令注册 ==========

    def register_command(
        self,
        name: Optional[str] = None,
        description: str = "",
        aliases: Optional[List[str]] = None,
    ) -> Callable[[Callable], Callable]:
        """
        注册命令的装饰器

        Args:
            name: 命令名称（默认使用函数名）
            description: 命令描述
            aliases: 命令别名

        Returns:
            装饰器函数
        """
        def decorator(func: Callable) -> Callable:
            cmd_name = name or func.__name__

            self._command_registry.register(
                name=cmd_name,
                description=description,
                aliases=aliases or [],
                handler=func,
            )

            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                return await func(*args, **kwargs)

            return wrapper

        return decorator

    # ========== 技能注册 ==========

    def register_skill(self, skill_id: str, skill_path: str) -> None:
        """
        注册技能

        Args:
            skill_id: 技能 ID
            skill_path: SKILL.md 文件路径
        """
        # 技能通过 skill_loader 加载，这里只做标记
        pass

    # ========== 内部方法 ==========

    def load_plugin(self, manifest: PluginManifest) -> None:
        """加载插件清单"""
        self._plugins.append(manifest)

    @property
    def tools(self) -> ToolRegistry:
        """获取工具注册表"""
        return self._tool_registry

    @property
    def hooks(self) -> HookRegistry:
        """获取 Hook 注册表"""
        return self._hook_registry

    @property
    def commands(self) -> CommandRegistry:
        """获取命令注册表"""
        return self._command_registry

    @property
    def plugins(self) -> List[PluginManifest]:
        """获取已加载的插件列表"""
        return self._plugins.copy()
