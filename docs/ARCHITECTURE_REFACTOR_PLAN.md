# OpenClaw 架构分析与 mul-agent 改造计划

## 一、OpenClaw 核心架构分析

### 1. 整体架构

```
openclaw/
├── openclaw.mjs              # CLI 入口（版本检查 + 加载 dist）
├── package.json              # 项目配置 + exports
├── src/                      # 核心源代码
│   ├── entry.ts              # 主入口（初始化 + CLI 启动）
│   ├── index.ts              # 公共导出 + 工具函数
│   │
│   ├── agents/               # Agent 系统（核心）
│   │   ├── skills/           # 技能加载器
│   │   ├── tools/            # Agent 工具
│   │   ├── auth-profiles/    # 认证配置
│   │   └── ...
│   │
│   ├── gateway/              # API 网关（HTTP server）
│   │   ├── server-methods/   # 网关处理方法
│   │   ├── agent-prompt.ts   # Agent 提示词构建
│   │   └── ...
│   │
│   ├── plugins/              # 插件运行时
│   │   ├── runtime/          # 插件运行时
│   │   ├── discovery.ts      # 插件发现
│   │   ├── types.ts          # 插件类型定义
│   │   └── ...
│   │
│   ├── plugin-sdk/           # 插件 SDK（公开 API）
│   │   ├── core.ts           # 核心导出
│   │   ├── provider-auth-result.ts
│   │   └── run-command.ts
│   │
│   ├── channels/             # 消息渠道
│   │   ├── plugins/          # 渠道插件
│   │   ├── dock.ts           # 渠道对接
│   │   └── ...
│   │
│   ├── commands/             # 命令系统
│   ├── cli/                  # CLI 实现
│   ├── config/               # 配置系统
│   ├── hooks/                # Hook 系统
│   ├── skills/               # 技能系统
│   ├── infra/                # 基础设施
│   └── shared/               # 共享工具
│
├── extensions/               # 扩展/插件包
│   ├── discord/              # Discord 扩展
│   ├── telegram/             # Telegram 扩展
│   ├── voice-call/           # 语音通话扩展
│   └── ...
│
└── skills/                   # 独立技能包
    ├── github/
    ├── skill-creator/
    └── ...
```

### 2. 核心设计模式

#### 2.1 插件系统

```typescript
// 插件定义 (package.json)
{
  "name": "@openclaw/voice-call",
  "openclaw": {
    "extensions": ["./index.ts"]  // 插件入口
  }
}

// 插件实现 (index.ts)
export default function(api: OpenClawPluginApi) {
  // 注册工具
  api.registerTool({
    name: "voice_call",
    description: "Make a voice call",
    parameters: Type.Object({ ... }),
    async execute(id, params) { ... }
  });

  // 注册 Hook
  api.registerHook({ name: "...", handler: ... });

  // 注册网关方法
  api.registerGatewayMethod({
    method: "voice.call",
    handler: ...
  });
}
```

#### 2.2 技能系统

```typescript
// 技能目录结构
skills/github/
├── SKILL.md          # 技能定义 (frontmatter + markdown)
└── scripts/          # 可选资源

// SKILL.md frontmatter
---
name: github
description: "GitHub operations..."
metadata:
  openclaw:
    requires: { bins: ["gh"] }
    install: [{ kind: "brew", formula: "gh" }]
---

// 技能加载流程
1. scanDirectoryWithLimits() 扫描技能目录
2. loadSkillsFromDir() 解析 SKILL.md
3. filterSkillEntries() 过滤 (enabled/os/bins)
4. buildWorkspaceSkillsPrompt() 构建提示词
```

#### 2.3 Agent 工具系统

```typescript
// 工具注册
api.registerTool(toolDef, options?)

// 工具定义
interface AnyAgentTool {
  name: string;
  description: string;
  parameters: Type.Box<any>;  // JSON Schema
  execute: (id: string, params: any) => Promise<ToolResult>;
}

// 可选工具（需要用户显式启用）
api.registerTool(toolDef, { optional: true })
```

#### 2.4 提示词构建

```typescript
// gateway/agent-prompt.ts
export function buildAgentPrompt(options): string {
  // 1. 加载 SKILL.md
  const skills = loadSkills(workspaceDir);

  // 2. 过滤启用的技能
  const eligible = filterSkills(skills, config);

  // 3. 构建提示词
  const prompt = formatSkillsForPrompt(eligible);

  // 4. 限制长度
  const limited = applySkillsPromptLimits(prompt);

  return limited;
}
```

### 3. 运行时架构

```
┌─────────────────────────────────────────────────────┐
│                   CLI (entry.ts)                    │
│  - 版本检查 / 环境初始化 / 参数解析                  │
└─────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────┐
│               Gateway (HTTP Server)                 │
│  - POST /chat - Agent 对话                          │
│  - POST /agent/run - 运行 Agent                      │
│  - GET /status - 状态查询                           │
└─────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   Agents      │ │   Plugins     │ │   Channels    │
│  - Skills     │ │  - Tools      │ │  - Telegram   │
│  - Tools      │ │  - Hooks      │ │  - Discord    │
│  - Memory     │ │  - Runtime    │ │  - WhatsApp   │
└───────────────┘ └───────────────┘ └───────────────┘
```

---

## 二、mul-agent 当前架构

### 1. 当前结构

```
mul_agent/
├── mul_agent/                  # Python 包
│   ├── main.py                 # 主入口
│   ├── brain/                  # Agent 大脑
│   │   ├── brain.py            # Brain 主类
│   │   ├── brain_v2.py         # 新版本 Brain
│   │   ├── router.py           # 路由系统
│   │   ├── llm.py              # LLM 客户端
│   │   ├── skill_loader.py     # 技能加载器 (新增)
│   │   ├── handlers/           # 路由处理器
│   │   └── ...
│   │
│   ├── skills/                 # 技能系统
│   ├── commands/               # 命令系统
│   ├── hooks/                  # Hook 系统
│   ├── tools/                  # 工具系统
│   ├── memory/                 # 记忆系统
│   ├── repositories/           # 数据仓库
│   └── api/                    # API 层
│       ├── routes/
│       └── server.py
│
├── wang/                       # 配置和数据
│   ├── agent-team/             # Agent 配置
│   │   ├── alice/
│   │   ├── bob/
│   │   └── core_brain/
│   ├── rules/                  # 规则
│   └── skills/                 # 技能
│
├── frontend/                   # Web UI
└── storage/                    # 存储
```

### 2. 与 OpenClaw 的对比

| 维度 | OpenClaw | mul-agent (当前) | mul-agent (目标) |
|------|----------|------------------|------------------|
| **语言** | TypeScript (Node.js) | Python | Python |
| **入口** | openclaw.mjs + entry.ts | main.py | mul-agent CLI + API |
| **插件系统** | ✅ 完整的 plugin-sdk | ❌ 无 | ✅ 需要实现 |
| **技能系统** | ✅ SKILL.md 格式 | ⚠️ 部分实现 | ✅ 已完成 |
| **工具系统** | ✅ JSON Schema 定义 | ⚠️ Python 函数 | ✅ 需要统一 |
| **Hook 系统** | ✅ 完整生命周期 | ⚠️ 基础实现 | ✅ 需要增强 |
| **命令系统** | ✅ Commander.js | ⚠️ 基础实现 | ✅ 需要增强 |
| **渠道系统** | ✅ 多渠道支持 | ❌ 无 | ⚠️ 可选 |
| **网关** | ✅ HTTP API | ⚠️ FastAPI | ✅ 保留 |
| **配置系统** | ✅ config/config.ts | ✅ config_manager.py | ✅ 保留 |

---

## 三、mul-agent 架构改造计划

### 改造目标

1. **模块化** - 高内聚、低耦合的模块设计
2. **插件化** - 支持独立扩展包
3. **标准化** - 统一的接口和类型定义
4. **可测试** - 测试代码与源代码共存

### 目标架构

```
mul_agent/
├── mul_agent/                  # Python 包
│   │
│   ├── __init__.py             # 包入口 + 公共导出
│   ├── __main__.py             # python -m mul_agent 入口
│   │
│   ├── cli/                    # CLI 系统
│   │   ├── __init__.py
│   │   ├── main.py             # CLI 主入口
│   │   ├── commands/           # CLI 命令
│   │   │   ├── agent.py        # agent 命令
│   │   │   ├── skill.py        # skill 命令
│   │   │   └── ...
│   │   └── profile.py          # CLI profile
│   │
│   ├── core/                   # 核心系统（原 brain）
│   │   ├── __init__.py
│   │   ├── agent.py            # Agent 主类
│   │   ├── brain.py            # 决策引擎
│   │   ├── router.py           # 路由系统
│   │   ├── llm.py              # LLM 客户端
│   │   └── context.py          # 上下文构建
│   │
│   ├── skills/                 # 技能系统
│   │   ├── __init__.py
│   │   ├── loader.py           # 技能加载器
│   │   ├── manager.py          # 技能管理器
│   │   ├── types.py            # 技能类型
│   │   └── evolution.py        # 技能进化
│   │
│   ├── tools/                  # 工具系统
│   │   ├── __init__.py
│   │   ├── registry.py         # 工具注册表
│   │   ├── base.py             # 工具基类
│   │   ├── types.py            # 工具类型
│   │   └── builtins/           # 内置工具
│   │
│   ├── plugins/                # 插件系统（新增）
│   │   ├── __init__.py
│   │   ├── sdk.py              # 插件 SDK
│   │   ├── runtime.py          # 插件运行时
│   │   ├── discovery.py        # 插件发现
│   │   └── types.py            # 插件类型
│   │
│   ├── hooks/                  # Hook 系统
│   │   ├── __init__.py
│   │   ├── manager.py          # Hook 管理器
│   │   ├── types.py            # Hook 类型
│   │   └── builtin/            # 内置 Hook
│   │
│   ├── commands/               # 命令系统
│   │   ├── __init__.py
│   │   ├── manager.py          # 命令管理器
│   │   ├── base.py             # 命令基类
│   │   └── builtin/            # 内置命令
│   │
│   ├── memory/                 # 记忆系统
│   │   ├── __init__.py
│   │   ├── base.py             # 记忆基类
│   │   ├── short_term.py       # 短期记忆
│   │   ├── long_term.py        # 长期记忆
│   │   └── manager.py          # 记忆管理器
│   │
│   ├── api/                    # API 层
│   │   ├── __init__.py
│   │   ├── server.py           # FastAPI 服务器
│   │   └── routes/             # API 路由
│   │
│   ├── config/                 # 配置系统
│   │   ├── __init__.py
│   │   ├── manager.py          # 配置管理器
│   │   └── types.py            # 配置类型
│   │
│   ├── extensions/             # 扩展系统（原 packages）
│   │   └── ...
│   │
│   └── utils/                  # 工具函数
│       ├── logging.py
│       ├── errors.py
│       └── helpers.py
│
├── extensions/                 # 独立扩展包
│   ├── wechat/                 # 微信扩展
│   ├── dingtalk/               # 钉钉扩展
│   └── ...
│
├── skills/                     # 独立技能包
│   ├── github/
│   ├── code-review/
│   └── ...
│
├── plugins/                    # 独立插件包
│   ├── auth-oauth/
│   ├── storage-s3/
│   └── ...
│
├── wang/                       # 项目配置
│   ├── agent-team/             # Agent 配置 (SKILL.md)
│   ├── rules/                  # 规则
│   └── skills/                 # 技能
│
├── tests/                      # 测试（部分与源代码共存）
│   ├── test_cli.py
│   ├── test_skills.py
│   └── ...
│
├── mul-agent                   # CLI 入口脚本
├── pyproject.toml              # 项目配置
└── README.md
```

### 核心接口设计

#### 1. 插件 SDK

```python
# mul_agent/plugins/sdk.py
from typing import Any, Callable, Protocol
from dataclasses import dataclass

class PluginAPI(Protocol):
    """插件 API 接口"""

    def register_tool(self, name: str, description: str,
                      schema: dict, handler: Callable) -> None:
        """注册工具"""
        ...

    def register_hook(self, name: str, handler: Callable,
                      priority: int = 0) -> None:
        """注册 Hook"""
        ...

    def register_command(self, name: str, handler: Callable,
                         description: str) -> None:
        """注册命令"""
        ...

    def register_skill(self, skill_id: str, skill_path: str) -> None:
        """注册技能"""
        ...

@dataclass
class PluginManifest:
    """插件清单"""
    name: str
    version: str
    description: str
    author: str
    entry: str  # 入口模块
    tools: list[str] = None
    hooks: list[str] = None
    commands: list[str] = None
    skills: list[str] = None

# 插件入口格式
def plugin_init(api: PluginAPI) -> PluginManifest:
    """插件初始化函数"""
    ...
```

#### 2. 工具系统

```python
# mul_agent/tools/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional

@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    content: Any
    error: Optional[str] = None
    metadata: dict = None

class BaseTool(ABC):
    """工具基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        ...

    @property
    @abstractmethod
    def schema(self) -> dict:
        """JSON Schema 参数定义"""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        ...

# 可选工具
class OptionalTool(BaseTool):
    """可选工具基类（需要用户显式启用）"""
    optional: bool = True
```

#### 3. 技能系统

```python
# mul_agent/skills/types.py
from dataclasses import dataclass, field
from typing import Optional, Any
from pathlib import Path
from enum import Enum

class SkillOrigin(Enum):
    """技能来源"""
    BUNDLED = "bundled"      # 内置技能
    WORKSPACE = "workspace"  # 工作区技能
    MANAGED = "managed"      # 管理的技能
    PLUGIN = "plugin"        # 插件技能

@dataclass
class SkillMetadata:
    """技能元数据"""
    name: str
    description: str
    emoji: str = ""
    role: str = ""
    title: str = ""
    tools: list[str] = field(default_factory=list)
    os: list[str] = field(default_factory=list)
    requires: dict = field(default_factory=dict)

@dataclass
class SkillEntry:
    """技能条目"""
    skill_id: str
    name: str
    base_dir: Path
    file_path: Path  # SKILL.md 路径
    metadata: SkillMetadata
    content: str  # Markdown 正文
    origin: SkillOrigin
    enabled: bool = True
```

#### 4. Hook 系统

```python
# mul_agent/hooks/types.py
from typing import Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum

class HookPhase(Enum):
    """Hook 阶段"""
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    PRE_COMMAND = "pre_command"
    POST_COMMAND = "post_command"
    PRE_AGENT_RUN = "pre_agent_run"
    POST_AGENT_RUN = "post_agent_run"
    SESSION_START = "session_start"
    SESSION_END = "session_end"

@dataclass
class HookContext:
    """Hook 上下文"""
    phase: HookPhase
    agent_id: str
    session_id: str
    data: dict = field(default_factory=dict)
    result: Any = None
    error: Exception = None

@dataclass
class HookEntry:
    """Hook 条目"""
    name: str
    phase: HookPhase
    handler: Callable[[HookContext], Awaitable[HookContext]]
    priority: int = 0  # 高优先级先执行
    enabled: bool = True
```

---

## 四、实施步骤

### 阶段 1: 基础重构 (Week 1-2)

1. **重新组织目录结构**
   - 移动 brain/ 到 core/
   - 创建 plugins/ 目录
   - 创建 extensions/ 目录

2. **定义核心接口**
   - 完成 PluginAPI 定义
   - 完成 BaseTool 定义
   - 完成 Hook 系统定义

3. **迁移现有代码**
   - 迁移 skill_loader.py 到 skills/loader.py
   - 迁移 tools/ 到新结构
   - 迁移 hooks/ 到新结构

### 阶段 2: 插件系统 (Week 3-4)

1. **实现插件 SDK**
   - 完成 PluginAPI 实现
   - 完成插件发现机制
   - 完成插件运行时

2. **创建示例插件**
   - 创建 auth-oauth 插件
   - 创建 storage-local 插件

3. **集成到核心**
   - 在 core/agent.py 中加载插件
   - 在 API 中暴露插件端点

### 阶段 3: 工具系统 (Week 5-6)

1. **统一工具定义**
   - 迁移现有工具到 BaseTool
   - 添加工具注册表
   - 实现可选工具机制

2. **添加工具验证**
   - JSON Schema 验证
   - 工具执行超时
   - 工具沙箱

### 阶段 4: 完善和测试 (Week 7-8)

1. **添加测试**
   - 单元测试
   - 集成测试
   - E2E 测试

2. **文档**
   - 插件开发指南
   - 工具开发指南
   - API 文档

3. **示例项目**
   - 完整示例插件
   - 完整示例技能

---

## 五、参考文档

- [OpenClaw Plugin SDK](../openclaw/src/plugin-sdk/core.ts)
- [OpenClaw Skills System](../openclaw/src/agents/skills/workspace.ts)
- [OpenClaw Plugin Types](../openclaw/src/plugins/types.ts)
- [OpenClaw Plugin Discovery](../openclaw/src/plugins/discovery.ts)
