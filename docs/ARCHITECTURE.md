# mul-agent 架构文档

> Multi-Agent Collaboration System - 架构设计文档

---

## 一、项目结构

```
mul-agent/
├── mul_agent/                 # 核心代码包
│   ├── __init__.py           # 包入口，导出所有核心组件
│   ├── src/                  # 核心源代码
│   │   ├── __init__.py
│   │   ├── agents/           # Agent 系统
│   │   │   ├── __init__.py
│   │   │   ├── base.py       # Agent 基类、配置、状态
│   │   │   ├── registry.py   # Agent 注册表
│   │   │   └── manager.py    # Agent 管理器
│   │   ├── tools/            # Tool 系统
│   │   │   ├── __init__.py
│   │   │   ├── base.py       # SyncTool/AsyncTool、ToolGate、ToolResult
│   │   │   ├── registry.py   # Tool 注册表
│   │   │   └── manager.py    # Tool 管理器（含 Hook 集成）
│   │   ├── skills/           # Skill 系统
│   │   │   ├── __init__.py
│   │   │   ├── base.py       # BaseSkill 基类
│   │   │   ├── registry.py   # Skill 注册表
│   │   │   └── manager.py    # Skill 管理器
│   │   ├── hooks/            # Hook 系统
│   │   │   ├── __init__.py
│   │   │   ├── base.py       # BaseHook、HookEvent、HookPriority
│   │   │   ├── registry.py   # Hook 注册表
│   │   │   └── manager.py    # Hook 管理器
│   │   ├── commands/         # Command 系统
│   │   ├── channels/         # 通信渠道
│   │   ├── memory/           # 记忆系统
│   │   ├── plugins/          # 插件目录
│   │   ├── plugin_sdk/       # 插件开发 SDK
│   │   ├── config/           # 配置管理
│   │   ├── logging/          # 日志系统
│   │   ├── shared/           # 共享工具
│   │   ├── types/            # 类型定义
│   │   ├── routing/          # 路由系统
│   │   ├── sessions/         # 会话管理
│   │   ├── gateway/          # API 网关
│   │   ├── infra/            # 基础设施
│   │   ├── context_engine/   # 上下文引擎
│   │   └── cli/              # CLI 入口
│   ├── api/                  # API 服务器（FastAPI）
│   ├── brain/                # Agent 大脑（保留原有实现）
│   ├── handlers/             # 路由处理器（保留原有实现）
│   └── tools/                # 内置工具（保留原有实现）
│
├── extensions/               # 扩展模块（独立可选组件）
├── skills/                   # 独立 Skills（可动态加载）
├── packages/                 # 独立 Packages
├── tests/                    # 测试文件
│   ├── test_agents.py
│   ├── test_tools.py
│   ├── test_skills.py
│   └── test_hooks.py
├── docs/                     # 文档
└── storage/                  # 存储数据
```

---

## 二、核心系统设计

### 1. Agent 系统

**职责**: Agent 是系统的核心执行单元，负责接收用户输入、调用工具、管理对话历史。

**核心组件**:
- `Agent`: 所有 Agent 的抽象基类
- `AgentConfig`: Agent 配置（模型、温度、能力等）
- `AgentState`: Agent 状态（IDLE, THINKING, EXECUTING, WAITING, ERROR）
- `AgentType`: Agent 类型（ASSISTANT, WORKER, SUPERVISOR, SPECIALIST）
- `AgentManager`: Agent 生命周期管理
- `AgentRegistry`: Agent 注册和发现

**使用示例**:
```python
from mul_agent import Agent, AgentConfig, AgentManager

# 创建配置
config = AgentConfig(
    agent_id="assistant",
    name="Assistant",
    role="通用助手",
    model="claude-sonnet-4-20250514",
)

# 创建管理器并注册 Agent
manager = AgentManager()
manager.register_agent_instance(my_agent, "assistant")

# 获取并执行
agent = manager.get_agent("assistant")
response = agent.process("你好！")
```

---

### 2. Tool 系统

**职责**: Tool 是系统的能力单元，提供具体的功能实现（文件操作、命令执行、API 调用等）。

**设计灵感**: 参考 OpenClaw 的 ToolGate 设计，支持条件检查（二进制、环境变量、操作系统等）。

**核心组件**:
- `SyncTool`: 同步工具基类
- `AsyncTool`: 异步工具基类
- `ToolGate`: 工具门条件（bins, env, config, os, always）
- `ToolMetadata`: 工具元数据（名称、描述、输入 schema）
- `ToolResult`: 工具执行结果（success, data, error, content, details）
- `ToolManager`: Tool 执行管理（支持 Hook 集成）
- `ToolRegistry`: Tool 注册和发现

**使用示例**:
```python
from mul_agent import SyncTool, ToolMetadata, ToolGate, ToolResult

class BashTool(SyncTool):
    metadata = ToolMetadata(
        name="bash",
        description="执行 bash 命令",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的命令"}
            },
            "required": ["command"]
        },
        gate=ToolGate(bins=["bash"], os=["darwin", "linux"]),
        sandbox_safe=False,
    )

    def execute_sync(self, command: str) -> ToolResult:
        import subprocess
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return ToolResult.success(
            data=result.stdout,
            details={"stderr": result.stderr, "returncode": result.returncode}
        )
```

---

### 3. Skill 系统

**职责**: Skill 是可动态加载的能力单元，比 Tool 更高级，可以组合多个 Tool。

**核心组件**:
- `BaseSkill`: 所有 Skill 的抽象基类
- `SkillManager`: Skill 执行管理
- `SkillRegistry`: Skill 注册和发现（支持按标签检索）

**使用示例**:
```python
from mul_agent import BaseSkill

class CodeReviewSkill(BaseSkill):
    skill_id = "code_review"
    skill_name = "Code Review"
    skill_description = "代码审查技能"
    skill_tags = ["code", "review", "quality"]
    priority = 7

    def _initialize(self):
        pass

    def execute(self, code: str, language: str = "python") -> dict:
        # 执行代码审查逻辑
        return {"issues": [], "suggestions": []}
```

---

### 4. Hook 系统

**职责**: Hook 是事件驱动的拦截器，用于在特定时机执行逻辑（权限检查、日志记录、结果格式化等）。

**核心组件**:
- `BaseHook`: 所有 Hook 的抽象基类
- `HookEvent`: 事件类型（PRE_TOOL_USE, POST_TOOL_USE, SESSION_START 等）
- `HookPriority`: 优先级（HIGH=1, NORMAL=5, LOW=10）
- `HookContext`: Hook 上下文
- `HookManager`: Hook 触发管理
- `HookRegistry`: Hook 注册和发现

**使用示例**:
```python
from mul_agent import PreToolUseHook, HookEvent, HookPriority, HookContext

class LogInvocationHook(PreToolUseHook):
    hook_id = "log_invocation"
    hook_name = "Log Invocation"
    events = [HookEvent.PRE_TOOL_USE]
    priority = HookPriority.NORMAL

    def _initialize(self):
        pass

    def on_pre_tool_use(self, context: HookContext) -> dict:
        tool_name = context.get("tool_name")
        params = context.get("params")
        print(f"Tool invoked: {tool_name} with params: {params}")
        return None  # 不修改参数，不阻止执行
```

---

## 三、系统交互流程

```
用户输入
    │
    ▼
Agent (接收输入)
    │
    ▼
[Hook: PRE_MESSAGE]
    │
    ▼
Router (路由分发)
    │
    ├──► Tool 执行 ──► [Hook: PRE_TOOL_USE] ──► [Hook: POST_TOOL_USE]
    │
    ├──► Skill 执行 ──► [Hook: PRE_SKILL_EXECUTE] ──► [Hook: POST_SKILL_EXECUTE]
    │
    └──► Agent 对话
    │
    ▼
[Hook: POST_MESSAGE]
    │
    ▼
返回结果
```

---

## 四、设计原则

### 1. 模块化 (Modularity)
- 每个系统独立封装（Agent, Tool, Skill, Hook）
- 清晰的接口边界
- 支持独立测试和替换

### 2. 可扩展性 (Extensibility)
- 所有核心组件支持动态注册
- 支持从目录自动加载
- 插件 SDK 支持第三方扩展

### 3. 可测试性 (Testability)
- 所有基类设计便于 mock
- 支持单元测试和集成测试
- 测试文件与源码并列放置

### 4. 类型安全 (Type Safety)
- 全面的类型提示
- 使用 dataclass 进行结构化数据
- 枚举类型用于状态和事件

### 5. 文档化 (Documentation)
- 所有公共 API 有 docstring
- 使用示例嵌入文档
- 维护架构文档

---

## 五、与 OpenClaw 的对应关系

| OpenClaw (TypeScript) | mul-agent (Python) |
|-----------------------|-------------------|
| `src/agents/` | `mul_agent/src/agents/` |
| `src/tools/` | `mul_agent/src/tools/` |
| `src/skills/` | `mul_agent/src/skills/` |
| `src/hooks/` | `mul_agent/src/hooks/` |
| `src/commands/` | `mul_agent/src/commands/` |
| `src/memory/` | `mul_agent/src/memory/` |
| `extensions/` | `extensions/` |
| `skills/` | `skills/` |
| `packages/` | `packages/` |
| `ToolGate` | `ToolGate` |
| `ToolResult` | `ToolResult` |
| `HookEvent` | `HookEvent` |
| `HookPriority` | `HookPriority` |

---

## 六、后续开发计划

### 阶段 1: 核心系统完善
- [ ] 完成 Command 系统设计
- [ ] 完成 Channel 系统设计
- [ ] 实现内置工具集
- [ ] 实现内置 Skills

### 阶段 2: 插件系统
- [ ] 完善 Plugin SDK
- [ ] 实现插件加载器
- [ ] 创建示例插件

### 阶段 3: 迁移现有代码
- [ ] 迁移 brain/ 到新架构
- [ ] 迁移 handlers/ 到新架构
- [ ] 迁移 tools/ 到新架构

### 阶段 4: 测试与文档
- [ ] 编写单元测试（80%+ 覆盖率）
- [ ] 编写集成测试
- [ ] 完善 API 文档
- [ ] 创建使用示例
