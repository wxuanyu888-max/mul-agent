# mul-agent 架构重构总结

> 基于 OpenClaw 架构的 Python 多 Agent 系统重构

---

## 重构概述

本次重构将 mul-agent 按照 [OpenClaw](https://github.com/anthropics/openclaw) 的文件架构进行了全面改造，建立了清晰的模块化结构。

---

## 创建的核心文件

### 1. Agent 系统 (`mul_agent/src/agents/`)

| 文件 | 说明 | 行数 |
|------|------|------|
| `base.py` | Agent 基类、AgentConfig、AgentState、AgentType | ~190 行 |
| `registry.py` | Agent 注册表，支持类/实例注册和目录加载 | ~180 行 |
| `manager.py` | Agent 生命周期管理，创建/激活/执行 | ~220 行 |
| `__init__.py` | 模块导出 | |

**核心类**:
- `Agent` - 所有 Agent 的抽象基类
- `AgentConfig` - Agent 配置（模型、温度、能力等）
- `AgentState` - 状态枚举（IDLE, THINKING, EXECUTING, WAITING, ERROR）
- `AgentType` - 类型枚举（ASSISTANT, WORKER, SUPERVISOR, SPECIALIST）
- `AgentManager` - Agent 管理器
- `AgentRegistry` - Agent 注册表

---

### 2. Tool 系统 (`mul_agent/src/tools/`)

| 文件 | 说明 | 行数 |
|------|------|------|
| `base.py` | SyncTool/AsyncTool、ToolGate、ToolResult | ~370 行 |
| `registry.py` | Tool 注册表，支持目录加载 | ~180 行 |
| `manager.py` | Tool 执行管理，集成 Hook 系统 | ~250 行 |
| `__init__.py` | 模块导出 | |

**核心类**:
- `SyncTool` / `AsyncTool` - 同步/异步工具基类
- `ToolGate` - 工具门条件（bins, env, config, os 检查）
- `ToolMetadata` - 工具元数据
- `ToolResult` - 工具执行结果（含 content/details 分离）
- `ToolManager` - Tool 管理器
- `ToolRegistry` - Tool 注册表

---

### 3. Skill 系统 (`mul_agent/src/skills/`)

| 文件 | 说明 | 行数 |
|------|------|------|
| `base.py` | BaseSkill 基类 | ~140 行 |
| `registry.py` | Skill 注册表，支持标签检索 | ~200 行 |
| `manager.py` | Skill 执行管理 | ~180 行 |
| `__init__.py` | 模块导出 | |

**核心类**:
- `BaseSkill` - 所有 Skill 的抽象基类
- `SkillManager` - Skill 管理器
- `SkillRegistry` - Skill 注册表（支持按标签检索）

---

### 4. Hook 系统 (`mul_agent/src/hooks/`)

| 文件 | 说明 | 行数 |
|------|------|------|
| `base.py` | BaseHook、HookEvent、HookPriority、HookContext | ~290 行 |
| `registry.py` | Hook 注册表，按事件索引 | ~220 行 |
| `manager.py` | Hook 触发管理 | ~180 行 |
| `__init__.py` | 模块导出 | |

**核心类**:
- `BaseHook` - 所有 Hook 的抽象基类
- `HookEvent` - 事件类型枚举（10 种事件）
- `HookPriority` - 优先级枚举（HIGH=1, NORMAL=5, LOW=10）
- `HookContext` - Hook 上下文
- `HookManager` - Hook 管理器
- `HookRegistry` - Hook 注册表

**便捷基类**:
- `PreToolUseHook` - 工具执行前 Hook
- `PostToolUseHook` - 工具执行后 Hook
- `SessionStartHook` - 会话开始 Hook
- `SessionEndHook` - 会话结束 Hook

---

## 文档文件

| 文件 | 说明 |
|------|------|
| `docs/ARCHITECTURE.md` | 完整架构设计文档 |
| `mul_agent/src/README.md` | src 目录使用说明 |
| `docs/ARCHITECTURE_REFACTOR_SUMMARY.md` | 本总结文档 |

---

## 设计特点

### 1. 受 OpenClaw 启发的设计

- **ToolGate**: 工具可用性条件检查
  ```python
  ToolGate(
      bins=["git"],           # 必需的二进制文件
      any_bins=["npm", "yarn"], # 至少需要一个
      env=["API_KEY"],        # 必需的环境变量
      os=["darwin", "linux"], # 支持的操作系统
      always=False            # 总是可用
  )
  ```

- **ToolResult**: 统一的结果格式
  ```python
  ToolResult.success(data=..., details=...)
  ToolResult.error(message, status=...)
  ```

- **Hook 系统**: 事件驱动的拦截器模式
  - 优先级控制
  - 按事件订阅
  - 支持修改参数/结果

### 2. Python 风格实现

- 使用 `dataclass` 进行数据建模
- 全面的类型提示
- 符合 PEP 8 的代码风格
- 使用枚举进行状态管理

### 3. 模块化设计

每个系统独立封装：
```
系统 = 基类 + 注册表 + 管理器
```

- **基类**: 定义接口和规范
- **注册表**: 负责注册和发现
- **管理器**: 负责生命周期和执行

---

## 使用示例

### 快速开始

```python
from mul_agent import (
    AgentManager, ToolManager, SkillManager, HookManager,
    Agent, AgentConfig,
    SyncTool, ToolMetadata, ToolResult,
    BaseSkill,
    PreToolUseHook, HookEvent, HookPriority, HookContext
)

# 创建管理器
agent_manager = AgentManager()
tool_manager = ToolManager()
skill_manager = SkillManager()
hook_manager = HookManager()
```

### 创建 Agent

```python
class AssistantAgent(Agent):
    agent_id = "assistant"

    def process(self, message: str, **kwargs) -> str:
        return f"收到：{message}"

    def think(self, context: dict) -> dict:
        return {"action": "respond"}

# 注册
config = AgentConfig(
    agent_id="assistant",
    name="Assistant",
    role="通用助手"
)
agent = AssistantAgent(config)
agent_manager.register_agent_instance(agent, "assistant")
```

### 创建 Tool

```python
class BashTool(SyncTool):
    metadata = ToolMetadata(
        name="bash",
        description="执行 bash 命令",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"}
            },
            "required": ["command"]
        },
        gate=ToolGate(bins=["bash"]),
        sandbox_safe=False,
    )

    def execute_sync(self, command: str) -> ToolResult:
        import subprocess
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return ToolResult.success(
            data=result.stdout,
            details={"stderr": result.stderr}
        )

# 注册
tool_manager.register_tool(BashTool)
```

### 创建 Hook

```python
class LogHook(PreToolUseHook):
    hook_id = "log_invocation"
    hook_name = "Log Invocation"
    events = [HookEvent.PRE_TOOL_USE]
    priority = HookPriority.NORMAL

    def _initialize(self):
        pass

    def on_pre_tool_use(self, context: HookContext) -> dict:
        print(f"Tool: {context.get('tool_name')}")
        return None

# 注册
hook_manager.register_hook(LogHook)
```

---

## 目录结构总览

```
mul-agent/
├── mul_agent/
│   ├── __init__.py              # 导出所有核心组件
│   ├── src/
│   │   ├── agents/              # Agent 系统
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   ├── manager.py
│   │   │   └── __init__.py
│   │   ├── tools/               # Tool 系统
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   ├── manager.py
│   │   │   └── __init__.py
│   │   ├── skills/              # Skill 系统
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   ├── manager.py
│   │   │   └── __init__.py
│   │   ├── hooks/               # Hook 系统
│   │   │   ├── base.py
│   │   │   ├── registry.py
│   │   │   ├── manager.py
│   │   │   └── __init__.py
│   │   ├── commands/            # Command 系统
│   │   ├── channels/            # Channel 系统
│   │   ├── memory/              # Memory 系统
│   │   ├── plugins/             # 插件目录
│   │   ├── plugin_sdk/          # 插件 SDK
│   │   ├── config/              # 配置管理
│   │   ├── logging/             # 日志系统
│   │   ├── shared/              # 共享工具
│   │   ├── types/               # 类型定义
│   │   ├── routing/             # 路由系统
│   │   ├── sessions/            # 会话管理
│   │   ├── gateway/             # API 网关
│   │   ├── infra/               # 基础设施
│   │   ├── context_engine/      # 上下文引擎
│   │   └── cli/                 # CLI 入口
│   ├── api/                     # API 服务器
│   ├── brain/                   # 原有大脑实现
│   ├── handlers/                # 原有处理器
│   └── tools/                   # 原有工具
│
├── extensions/                  # 扩展模块
├── skills/                      # 独立 Skills
├── packages/                    # 独立 Packages
├── tests/                       # 测试
├── docs/
│   ├── ARCHITECTURE.md          # 架构详解
│   └── ARCHITECTURE_REFACTOR_SUMMARY.md  # 重构总结
└── storage/                     # 存储
```

---

## 后续工作

### 已完成
- [x] 创建 agents 基类和管理器
- [x] 创建 tools 基类和管理器
- [x] 创建 skills 基类和管理器
- [x] 创建 hooks 基类和管理器
- [x] 创建文档

### 待完成
- [ ] 迁移原有 brain/ 代码到新架构
- [ ] 迁移原有 handlers/ 代码到新架构
- [ ] 迁移原有 tools/ 代码到新架构
- [ ] 实现 commands 系统
- [ ] 实现 channels 系统
- [ ] 编写单元测试（80%+ 覆盖率）
- [ ] 创建内置工具集
- [ ] 创建内置 Skills

---

## 参考资源

- [OpenClaw GitHub](https://github.com/anthropics/openclaw)
- [mul-agent 架构文档](docs/ARCHITECTURE.md)
- [src 目录说明](mul_agent/src/README.md)
