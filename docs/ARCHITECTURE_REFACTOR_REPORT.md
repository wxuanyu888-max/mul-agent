# mul-agent 架构改造报告

**日期**: 2026-03-09
**参考**: OpenClaw 架构

---

## 一、改造概述

参考 OpenClaw 的成熟架构设计，对 mul-agent 进行了模块化重构。

### 改造目标

1. **模块化** - 高内聚、低耦合的模块设计
2. **插件化** - 支持独立扩展包
3. **标准化** - 统一的接口和类型定义
4. **可测试** - 测试代码与源代码共存

---

## 二、新架构结构

```
mul_agent/
├── mul_agent/                      # Python 包
│   │
│   ├── __init__.py                 # 包入口
│   ├── __main__.py                 # python -m 入口
│   │
│   ├── core/                       # 核心系统（新增）
│   │   ├── __init__.py
│   │   ├── agent.py                # Agent 核心类
│   │   └── brain.py                # 决策引擎
│   │
│   ├── plugins/                    # 插件系统（新增）
│   │   ├── __init__.py
│   │   ├── sdk.py                  # 插件 API
│   │   ├── types.py                # 类型定义
│   │   └── discovery.py            # 插件发现
│   │
│   ├── brain/                      # 原有大脑模块
│   │   ├── skill_loader.py         # 技能加载器
│   │   ├── router.py               # 路由系统
│   │   ├── llm.py                  # LLM 客户端
│   │   └── handlers/               # 处理器
│   │
│   ├── skills/                     # 技能系统
│   ├── tools/                      # 工具系统
│   ├── hooks/                      # Hook 系统
│   ├── commands/                   # 命令系统
│   ├── memory/                     # 记忆系统
│   ├── api/                        # API 层
│   └── config/                     # 配置系统
│
├── extensions/                     # 独立扩展包
├── skills/                         # 独立技能包
├── plugins/                        # 独立插件包
└── wang/                           # 项目配置
    └── agent-team/                 # Agent 配置 (SKILL.md)
```

---

## 三、核心模块设计

### 1. Core 模块

#### Agent 类

```python
from mul_agent.core import Agent

agent = Agent(
    agent_id="alice",
    name="Alice",
    role="代码工程师"
)
response = await agent.run("帮我实现一个加法函数")
```

#### Brain 类

```python
from mul_agent.core import Brain

brain = Brain(agent_id="alice")
response = await brain.process("帮我写代码")
```

### 2. Plugins 模块

#### 插件开发示例

```python
# extensions/my_plugin/__init__.py
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

#### 插件运行时

```python
from mul_agent.plugins import PluginRuntime

runtime = PluginRuntime(workspace_dir=Path("wang"))
plugins = runtime.load_all()

# 访问工具
tools = runtime.tool_registry.list()
hooks = runtime.hook_registry.list()
```

### 3. 类型系统

#### PluginManifest

```python
@dataclass
class PluginManifest:
    name: str
    version: str
    description: str
    author: str
    entry: str
    tools: List[str]
    hooks: List[str]
    commands: List[str]
    skills: List[str]
```

#### ToolRegistry

```python
@dataclass
class ToolEntry:
    name: str
    description: str
    schema: dict  # JSON Schema
    handler: Callable
    optional: bool
    enabled: bool
```

#### HookRegistry

```python
class HookPhase(str, Enum):
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    PRE_COMMAND = "pre_command"
    POST_COMMAND = "post_command"
    PRE_AGENT_RUN = "pre_agent_run"
    POST_AGENT_RUN = "post_agent_run"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
```

---

## 四、已完成工作

### 新增文件

| 文件 | 说明 |
|------|------|
| `mul_agent/core/__init__.py` | Core 模块入口 |
| `mul_agent/core/agent.py` | Agent 核心类 |
| `mul_agent/core/brain.py` | Brain 决策引擎 |
| `mul_agent/plugins/__init__.py` | Plugins 模块入口 |
| `mul_agent/plugins/sdk.py` | 插件 API SDK |
| `mul_agent/plugins/types.py` | 类型定义 |
| `mul_agent/plugins/discovery.py` | 插件发现和加载 |
| `mul_agent/cli/__init__.py` | CLI 模块入口 |
| `mul_agent/extensions/__init__.py` | Extensions 模块入口 |

### 保留模块

以下模块保留原有实现，逐步迁移：

- `mul_agent/brain/` - 原有大脑模块（包含 skill_loader.py）
- `mul_agent/skills/` - 技能系统
- `mul_agent/tools/` - 工具系统
- `mul_agent/hooks/` - Hook 系统
- `mul_agent/commands/` - 命令系统
- `mul_agent/memory/` - 记忆系统
- `mul_agent/api/` - API 层

---

## 五、与 OpenClaw 对照

| 组件 | OpenClaw | mul-agent (新) | 状态 |
|------|----------|----------------|------|
| **入口** | `openclaw.mjs` + `entry.ts` | `mul_agent/__main__.py` | 待实现 |
| **核心** | `src/agents/` | `mul_agent/core/` | ✅ 已实现骨架 |
| **插件** | `src/plugins/` + `plugin-sdk/` | `mul_agent/plugins/` | ✅ 已实现骨架 |
| **技能** | `skills/` + `src/agents/skills/` | `mul_agent/brain/skill_loader.py` | ✅ 已完成 |
| **工具** | `src/agents/tools/` | `mul_agent/tools/` | 待迁移 |
| **Hook** | `src/hooks/` | `mul_agent/hooks/` | 待迁移 |
| **命令** | `src/commands/` | `mul_agent/commands/` | 待迁移 |
| **配置** | `src/config/` | `mul_agent/config/` | 待迁移 |
| **扩展** | `extensions/` | `extensions/` | 目录已创建 |

---

## 六、下一步计划

### 阶段 1: 完成核心迁移 (Week 1)

- [ ] 迁移 `brain/router.py` 到 `core/router.py`
- [ ] 迁移 `brain/llm.py` 到 `core/llm.py`
- [ ] 更新所有导入路径
- [ ] 添加单元测试

### 阶段 2: 完善插件系统 (Week 2-3)

- [ ] 实现 Hook 系统
- [ ] 实现命令注册
- [ ] 创建示例插件
- [ ] 添加插件文档

### 阶段 3: 统一工具系统 (Week 4)

- [ ] 迁移现有工具到 `BaseTool` 类
- [ ] 实现 JSON Schema 验证
- [ ] 添加工具超时控制

### 阶段 4: 测试和文档 (Week 5-6)

- [ ] 完整的单元测试
- [ ] 插件开发指南
- [ ] API 文档
- [ ] 示例项目

---

## 七、参考文档

- [OpenClaw 架构分析](./ARCHITECTURE_REFACTOR_PLAN.md)
- [Agent SKILL.md 迁移](./AGENT_SKILL_MIGRATION.md)
- [OpenClaw Plugin SDK](../openclaw/src/plugin-sdk/core.ts)
- [OpenClaw Plugin Types](../openclaw/src/plugins/types.ts)
