"""Tool Manager - 工具管理器

参考 OpenClaw 的 createOpenClawTools 设计：
1. 统一管理所有工具实例
2. 支持工具策略过滤
3. 支持插件工具扩展
4. 提供工具查询和执行接口

使用方式:
    from mul_agent.tools.manager import ToolManager, ToolContext

    # 创建上下文
    context = ToolContext(
        agent_id="wangyue",
        session_id="xxx",
        workspace_dir="/path/to/workspace",
        config=config,
    )

    # 创建管理器
    manager = ToolManager(context)

    # 获取工具列表
    tools = manager.list_tools()

    # 执行工具
    result = manager.execute("bash", command="ls -la")
"""

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Type
from pathlib import Path

from mul_agent.tools.base import SyncTool, AsyncTool, ToolResult, ToolMetadata, AnyTool
from mul_agent.tools.policy import ToolPolicy, ToolGroup, normalize_tool_name


@dataclass
class ToolContext:
    """工具执行上下文"""
    agent_id: str
    session_id: Optional[str] = None
    workspace_dir: str = "."
    config: Dict[str, Any] = field(default_factory=dict)
    sender_is_owner: bool = False
    sandboxed: bool = False
    message_channel: Optional[str] = None
    account_id: Optional[str] = None


class ToolManager:
    """工具管理器

    职责：
    1. 注册和管理工具实例
    2. 根据策略过滤可用工具
    3. 提供工具执行接口
    4. 支持动态添加/移除工具
    """

    def __init__(self, context: ToolContext, policy: Optional[ToolPolicy] = None):
        self.context = context
        self.policy = policy or ToolPolicy.from_profile("full")

        # 工具注册表：name -> tool instance
        self._tools: Dict[str, AnyTool] = {}

        # 工具类注册表：name -> tool class (用于懒加载)
        self._tool_classes: Dict[str, Type[AnyTool]] = {}

        # 已加载的工具名
        self._loaded_tools: Set[str] = set()

        # 注册内置工具
        self._register_builtin_tools()

    def _register_builtin_tools(self):
        """注册内置工具"""
        # 文件操作工具
        from mul_agent.tools.builtins import ReadTool, WriteTool, EditTool
        self.register_tool_class("read", ReadTool)
        self.register_tool_class("write", WriteTool)
        self.register_tool_class("edit", EditTool)

        # Bash 工具
        from mul_agent.tools.builtins import BashTool
        self.register_tool_class("bash", BashTool)

        # 搜索工具
        try:
            from mul_agent.tools.search import GlobTool, GrepTool
            self.register_tool_class("glob", GlobTool)
            self.register_tool_class("grep", GrepTool)
        except ImportError:
            pass

        # Git 工具
        try:
            from mul_agent.tools.git_diff import GitDiffTool
            self.register_tool_class("git_diff", GitDiffTool)
        except ImportError:
            pass

    def register_tool(self, name: str, tool: AnyTool):
        """注册工具实例"""
        name = normalize_tool_name(name)
        self._tools[name] = tool
        self._loaded_tools.add(name)

    def register_tool_class(self, name: str, tool_class: Type[AnyTool]):
        """注册工具类（懒加载）"""
        name = normalize_tool_name(name)
        self._tool_classes[name] = tool_class
        # 同时添加到工具列表用于元数据查询
        if name not in self._tools:
            # 创建一个占位条目用于元数据
            pass

    def unregister_tool(self, name: str):
        """注销工具"""
        name = normalize_tool_name(name)
        self._tools.pop(name, None)
        self._tool_classes.pop(name, None)
        self._loaded_tools.discard(name)

    def get_tool(self, name: str) -> Optional[AnyTool]:
        """获取工具实例（懒加载）"""
        name = normalize_tool_name(name)

        # 先检查已加载的
        if name in self._tools:
            return self._tools[name]

        # 检查是否有注册的类
        if name in self._tool_classes:
            tool_class = self._tool_classes[name]
            # 创建实例（尝试传入 context，如果不支持则不用）
            try:
                tool = tool_class(context=vars(self.context))
            except TypeError:
                # 旧式工具不支持 context 参数
                tool = tool_class()
            self.register_tool(name, tool)
            return tool

        return None

    def list_tools(self, include_metadata: bool = True) -> List[Dict[str, Any]]:
        """列出所有允许的工具

        Args:
            include_metadata: 是否包含元数据

        Returns:
            工具定义列表
        """
        result = []

        # 收集所有可能的工具名
        all_tool_names = set(self._tools.keys()) | set(self._tool_classes.keys())

        for name in all_tool_names:
            # 检查策略
            if not self.policy.is_allowed(name):
                continue

            tool = self.get_tool(name)
            if tool:
                # 检查门控（如果工具支持）
                if hasattr(tool, 'check_gate'):
                    if not tool.check_gate():
                        continue

                if include_metadata:
                    if hasattr(tool, 'to_registry_definition'):
                        result.append(tool.to_registry_definition())
                    else:
                        # 旧式工具
                        result.append({
                            "name": name,
                            "description": getattr(tool, '__doc__', '') or '',
                            "input_schema": {},
                            "examples": [],
                        })
                else:
                    result.append({"name": name})

        return result

    def list_tool_names(self) -> List[str]:
        """列出所有允许的工具名"""
        return [t["name"] for t in self.list_tools(include_metadata=False)]

    def execute(self, name: str, **kwargs) -> ToolResult:
        """执行工具

        Args:
            name: 工具名
            **kwargs: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        name = normalize_tool_name(name)

        # 检查策略
        if not self.policy.is_allowed(name):
            return ToolResult.error(
                f"Tool '{name}' is not allowed by current policy",
                status=403
            )

        tool = self.get_tool(name)
        if not tool:
            return ToolResult.error(f"Tool '{name}' not found", status=404)

        # 检查门控
        if not tool.check_gate():
            return ToolResult.error(
                f"Tool '{name}' is not available (gate check failed)",
                status=503
            )

        try:
            return tool.execute(**kwargs)
        except Exception as e:
            return ToolResult.error(f"Tool execution failed: {e}", status=500)

    async def execute_async(self, name: str, **kwargs) -> ToolResult:
        """异步执行工具"""
        name = normalize_tool_name(name)

        if not self.policy.is_allowed(name):
            return ToolResult.error(
                f"Tool '{name}' is not allowed by current policy",
                status=403
            )

        tool = self.get_tool(name)
        if not tool:
            return ToolResult.error(f"Tool '{name}' not found", status=404)

        if not tool.check_gate():
            return ToolResult.error(
                f"Tool '{name}' is not available (gate check failed)",
                status=503
            )

        try:
            if isinstance(tool, AsyncTool):
                return await tool.execute(**kwargs)
            elif isinstance(tool, SyncTool):
                # 同步工具在异步上下文中执行
                return tool.execute(**kwargs)
            else:
                return ToolResult.error(f"Tool '{name}' has unknown type", status=500)
        except Exception as e:
            return ToolResult.error(f"Tool execution failed: {e}", status=500)

    def get_tools_prompt(self) -> str:
        """生成工具列表提示词（供 LLM 理解可用工具）"""
        tools = self.list_tools()
        if not tools:
            return "没有可用工具。"

        prompt_parts = ["## 可用工具\n"]
        for tool in tools:
            prompt_parts.append(self._format_tool_for_prompt(tool))

        return "\n".join(prompt_parts)

    def _format_tool_for_prompt(self, tool: Dict[str, Any]) -> str:
        """将工具格式化为提示词"""
        lines = [f"### {tool['name']}"]
        lines.append(tool['description'])
        lines.append("")

        # 参数
        schema = tool.get('input_schema', {})
        props = schema.get('properties', {})
        required = schema.get('required', [])

        if props:
            lines.append("**参数:**")
            for param_name, param_def in props.items():
                param_type = param_def.get('type', 'any')
                param_desc = param_def.get('description', '')
                is_required = param_name in required
                lines.append(f"  - `{param_name}` ({param_type}, {'required' if is_required else 'optional'}): {param_desc}")
            lines.append("")

        # 示例
        examples = tool.get('examples', [])
        if examples:
            lines.append("**示例:**")
            for ex in examples[:3]:  # 最多显示 3 个示例
                lines.append(f"  - {ex}")
            lines.append("")

        return "\n".join(lines)

    def apply_policy(self, policy: ToolPolicy):
        """应用新的工具策略"""
        self.policy = policy
        # 清理不再允许的工具
        self._cleanup_tools()

    def _cleanup_tools(self):
        """清理不再允许的工具"""
        to_remove = []
        for name in self._loaded_tools:
            if not self.policy.is_allowed(name):
                to_remove.append(name)

        for name in to_remove:
            self.unregister_tool(name)

    def get_stats(self) -> Dict[str, Any]:
        """获取工具管理器统计信息"""
        return {
            "total_tools": len(self._tools) + len(self._tool_classes),
            "loaded_tools": len(self._loaded_tools),
            "allowed_tools": len(self.list_tools()),
            "policy": self.policy.to_dict(),
        }


def create_tool_manager(
    agent_id: str,
    session_id: str = None,
    workspace_dir: str = ".",
    config: Dict = None,
    profile: str = "full",
    **kwargs
) -> ToolManager:
    """创建工具管理器的便捷函数

    Args:
        agent_id: Agent ID
        session_id: 会话 ID
        workspace_dir: 工作目录
        config: 配置对象
        profile: 工具策略 profile
        **kwargs: 其他上下文参数

    Returns:
        ToolManager: 工具管理器
    """
    context = ToolContext(
        agent_id=agent_id,
        session_id=session_id,
        workspace_dir=workspace_dir,
        config=config or {},
        **kwargs
    )
    policy = ToolPolicy.from_profile(profile)
    return ToolManager(context, policy)
