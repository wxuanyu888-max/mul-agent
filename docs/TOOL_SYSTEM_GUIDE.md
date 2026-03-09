# 工具系统 (Tools)

> 参考 OpenClaw 的 tool kit 架构设计

mul-agent 的工具系统允许 Agent 通过标准接口与外部世界交互。本系统参考了 OpenClaw 的设计，包括：
- 统一的工具接口（SyncTool/AsyncTool）
- 工具策略和权限控制
- 工具门控（gating）机制
- 插件工具扩展

## 快速开始

### 使用工具管理器

```python
from mul_agent.tools.manager import ToolManager, ToolContext
from mul_agent.tools.policy import ToolPolicy

# 创建上下文
context = ToolContext(
    agent_id="wangyue",
    session_id="session-123",
    workspace_dir="/path/to/workspace",
    config={},
    sender_is_owner=True,
)

# 创建管理器（使用 coding profile）
policy = ToolPolicy.from_profile("coding")
manager = ToolManager(context, policy)

# 获取可用工具列表
tools = manager.list_tools()
print(f"可用工具：{[t['name'] for t in tools]}")

# 执行工具
result = manager.execute("bash", command="ls -la")
print(result.to_dict())
```

### 工具策略 (Policy)

工具策略控制哪些工具可用：

```python
from mul_agent.tools.policy import ToolPolicy, ToolGroup

# 使用预设 profile
minimal = ToolPolicy.from_profile("minimal")  # 仅 session_status
coding = ToolPolicy.from_profile("coding")    # 文件 + 运行时 + 会话
messaging = ToolPolicy.from_profile("messaging")  # 消息相关
full = ToolPolicy.from_profile("full")        # 所有工具

# 自定义策略
custom_policy = ToolPolicy(
    profile="full",
    allow={"bash", "read", "write"},
    deny={"exec"},  # 禁止 exec
    groups={"group:fs"},  # 允许所有文件操作
)

# 检查工具是否允许
if custom_policy.is_allowed("bash"):
    print("bash 工具可用")
```

### 工具组 (Tool Groups)

工具组是工具类别的简写：

| 组名 | 包含的工具 |
|------|-----------|
| `group:runtime` | exec, bash, process, kill, bg |
| `group:fs` | read, write, edit, apply_patch, ls, cat, glob |
| `group:sessions` | sessions_list, sessions_history, sessions_send |
| `group:memory` | memory_search, memory_get, memory_write |
| `group:web` | web_search, web_fetch, browse |
| `group:ui` | browser, canvas, screenshot |
| `group:code` | glob, grep, search, git, git_diff |

```python
policy = ToolPolicy(profile="full")
policy.add_group("group:fs")  # 添加文件操作工具
policy.remove_group("group:runtime")  # 移除运行时工具
```

## 可用工具列表

### 内置工具

| 工具名 | 描述 | 策略组 |
|--------|------|--------|
| `bash` | 执行 shell 命令 | group:runtime |
| `read` | 读取文件内容 | group:fs |
| `write` | 写入文件 | group:fs |
| `edit` | 编辑文件 | group:fs |
| `glob` | 文件模式匹配 | group:fs |
| `grep` | 文本搜索 | group:fs |
| `git_diff` | Git 差异查看 | group:code |

### Handler 工具（通过 Router 集成）

| 工具名 | Handler | 描述 |
|--------|---------|------|
| `bash` | BashHandler | 执行 shell 命令 |
| `file_edit` | FileEditHandler | 文件编辑（read/write/edit） |
| `memory` | MemoryHandler | 记忆管理 |
| `chat` | ChatHandler | Agent 对话 |
| `subagent` | SubagentHandler | 子代理委派 |
| `planner` | PlannerHandler | 任务规划 |

## 开发自定义工具

### 1. 继承 SyncTool 或 AsyncTool

```python
from mul_agent.tools.base import SyncTool, ToolMetadata, ToolResult, ToolGate

class MyTool(SyncTool):
    """我的自定义工具"""

    metadata = ToolMetadata(
        name="my_tool",
        description="我的工具描述",
        input_schema={
            "type": "object",
            "properties": {
                "param1": {
                    "type": "string",
                    "description": "参数 1 描述"
                },
                "param2": {
                    "type": "integer",
                    "description": "参数 2 描述",
                    "default": 42
                }
            },
            "required": ["param1"]
        },
        examples=[
            {"param1": "hello", "param2": 100},
        ],
        gate=ToolGate(
            bins=["my_binary"],  # 需要的二进制文件
            env=["MY_API_KEY"],  # 需要的环境变量
            os=["darwin", "linux"],  # 支持的操作系统
        ),
        tags=["custom", "my_category"],
    )

    def execute_sync(self, **kwargs) -> ToolResult:
        """执行工具"""
        param1 = kwargs.get("param1")
        param2 = kwargs.get("param2", 42)

        # 验证参数
        if not param1:
            return ToolResult.error("param1 is required")

        # 执行逻辑
        result = f"Result: {param1} x {param2}"

        return ToolResult.success(
            data={"result": result},
            message="执行成功",
            details={"extra_info": "可选的详细信息"}
        )
```

### 2. 注册到工具管理器

```python
# 在 mul_agent/tools/manager.py 的 _register_builtin_tools 中
from mul_agent.tools.builtins import MyTool
self.register_tool_class("my_tool", MyTool)
```

### 3. 添加到 __init__.py

```python
# mul_agent/tools/builtins/__init__.py
from mul_agent.tools.builtins.my_tool import MyTool

__all__ = [..., "MyTool"]
```

## 工具门控 (Gating)

门控条件决定工具何时可用：

```python
from mul_agent.tools.base import ToolGate

# 需要特定二进制文件
gate = ToolGate(
    bins=["git", "docker"],  # 所有都必须存在
)

# 需要任何二进制文件（至少一个）
gate = ToolGate(
    any_bins=["uv", "pip"],  # 有一个就行
)

# 需要环境变量
gate = ToolGate(
    env=["OPENAI_API_KEY", "ANTHROPIC_API_KEY"],
)

# 需要配置项
gate = ToolGate(
    config=["browser.enabled", "plugins.enabled"],
)

# 限制操作系统
gate = ToolGate(
    os=["darwin"],  # 仅 macOS
)

# 总是启用
gate = ToolGate(always=True)
```

## 工具结果格式

工具返回 `ToolResult` 对象：

```python
from mul_agent.tools.base import ToolResult

# 成功结果
result = ToolResult.success(
    data={"key": "value"},
    message="操作成功",
    details={"extra": "info"}
)

# 错误结果
result = ToolResult.error(
    error="错误信息",
    data={"partial": "data"}  # 可选的部分数据
)

# 转换为字典
result_dict = result.to_dict()

# 转换为可展示的内容
content = result.to_content()
# [
#   {"type": "text", "text": "操作成功"},
#   {"type": "text", "text": "{\"key\": \"value\"}"}
# ]
```

## 安全检查

BashTool 等工具内置安全检查：

```python
# 禁止的命令模式
FORBIDDEN_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "dd if=/dev/",
    ":(){:|:&};:",  # fork bomb
    "mkfs.",
    "wget.*\\|.*sh",
    "curl.*\\|.*sh",
]

# 禁止访问的路径
FORBIDDEN_PATHS = [
    "/etc/passwd",
    "/etc/shadow",
    "/etc/sudoers",
    "/root/.ssh",
    "/proc/",
]
```

## 与 Handler 集成

工具可以通过 Handler 暴露给 Router：

```python
# mul_agent/brain/handlers/bash.py
from mul_agent.tools.builtins import BashTool

class BashHandler:
    """Bash Handler"""

    def __init__(self, context):
        self.tool = BashTool(context=context)

    async def handle(self, params):
        """处理 bash 路由"""
        result = self.tool.execute(**params)
        return result.to_dict()
```

## 配置示例

在 `wang/settings.json` 中配置工具策略：

```json5
{
  "tools": {
    "profile": "coding",
    "allow": ["bash", "read", "write", "edit"],
    "deny": ["exec"],
    "groups": ["group:fs", "group:code"]
  },
  "skills": {
    "entries": {
      "github": {
        "enabled": true,
        "env": {
          "GITHUB_TOKEN": "your_token"
        }
      }
    }
  }
}
```

## 故障排查

### 工具找不到

1. 检查工具名是否正确（使用 `normalize_tool_name` 标准化）
2. 检查工具是否在策略的 allow 列表中
3. 检查工具门控条件是否满足

### 门控检查失败

```python
from mul_agent.tools.manager import ToolManager

manager = ToolManager(context)
tool = manager.get_tool("bash")
if tool:
    can_use = tool.check_gate()
    if not can_use:
        print("工具门控检查失败 - 可能缺少二进制文件或环境变量")
```

### 获取工具统计

```python
stats = manager.get_stats()
print(stats)
# {
#   "total_tools": 10,
#   "loaded_tools": 5,
#   "allowed_tools": 8,
#   "policy": {...}
# }
```

## 参考资料

- [OpenClaw Tools Documentation](https://docs.openclaw.ai/tools)
- [OpenClaw Tool Policy](https://docs.openclaw.ai/tools/tool-policy)
- [mul_agent/tools/base.py](/mul_agent/tools/base.py)
- [mul_agent/tools/policy.py](/mul_agent/tools/policy.py)
- [mul_agent/tools/manager.py](/mul_agent/tools/manager.py)
