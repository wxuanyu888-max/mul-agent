"""Tools layer - 工具系统

参考 OpenClaw 的 tool kit 架构设计：
1. 统一的工具接口 (SyncTool/AsyncTool)
2. 工具策略和权限控制 (ToolPolicy)
3. 工具管理器 (ToolManager)
4. 工具门控机制 (ToolGate)

使用方式 1 - 使用工具管理器:
    from mul_agent.tools import ToolManager, ToolContext, ToolPolicy

    context = ToolContext(agent_id="wangyue", workspace_dir=".")
    policy = ToolPolicy.from_profile("coding")
    manager = ToolManager(context, policy)

    # 执行工具
    result = manager.execute("bash", command="ls -la")
    print(result.to_dict())

使用方式 2 - 直接使用工具类:
    from mul_agent.tools.builtins import BashTool

    tool = BashTool(context={"workspace_dir": "."})
    result = tool.execute(command="ls -la")
    print(result.to_dict())

工具系统架构:
- mul_agent.tools.base - 工具基类 (SyncTool, AsyncTool, ToolResult)
- mul_agent.tools.policy - 工具策略 (ToolPolicy, ToolGroup)
- mul_agent.tools.manager - 工具管理器 (ToolManager)
- mul_agent.tools.builtins - 内置工具 (BashTool, ReadTool, etc.)
"""

# 基础类
from mul_agent.tools.base import (
    SyncTool,
    AsyncTool,
    ToolMetadata,
    ToolResult,
    ToolGate,
    ToolInputError,
    ToolAuthorizationError,
    AnyTool,
)

# 策略系统
from mul_agent.tools.policy import (
    ToolPolicy,
    ToolGroup,
    AgentToolPolicy,
    resolve_tool_groups,
    normalize_tool_name,
)

# 管理器
from mul_agent.tools.manager import (
    ToolManager,
    ToolContext,
    create_tool_manager,
)

# 内置工具
from mul_agent.tools.builtins import (
    BashTool,
    ReadTool,
    WriteTool,
    EditTool,
)

__all__ = [
    # 基础类
    "SyncTool",
    "AsyncTool",
    "ToolMetadata",
    "ToolResult",
    "ToolGate",
    "ToolInputError",
    "ToolAuthorizationError",
    "AnyTool",

    # 策略系统
    "ToolPolicy",
    "ToolGroup",
    "AgentToolPolicy",
    "resolve_tool_groups",
    "normalize_tool_name",

    # 管理器
    "ToolManager",
    "ToolContext",
    "create_tool_manager",

    # 内置工具
    "BashTool",
    "ReadTool",
    "WriteTool",
    "EditTool",
]
