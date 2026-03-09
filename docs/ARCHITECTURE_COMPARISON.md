# mul-agent 与 OpenClaw 架构对比

> 分析当前 mul-agent 架构与 OpenClaw 的差异，明确改进方向

---

## 一、架构概览对比

| 维度 | OpenClaw (TypeScript) | mul-agent (Python) | 对齐状态 |
|------|----------------------|-------------------|----------|
| **核心入口** | `src/index.ts` | `mul_agent/core/brain.py` | ✅ 已对齐 |
| **Agent 系统** | `src/agents/*.ts` | `mul_agent/core/agent.py` | ✅ 已对齐 |
| **Tools 系统** | `src/tools/` + `skills/*/SKILL.md` | `mul_agent/tools/` + `wang/agent-team/*/SKILL.md` | ✅ 已对齐 |
| **Hooks 系统** | `src/hooks/` | `mul_agent/hooks/` | ✅ 已对齐 |
| **Skills** | `skills/*/SKILL.md` | `wang/agent-team/*/SKILL.md` | ✅ 已对齐 |
| **Extensions** | `extensions/*/` | `mul_agent/extensions/` | ✅ 已对齐 |
| **Plugins** | `src/plugins/` + `src/plugin-sdk/` | `mul_agent/plugins/` | ✅ 已对齐 |
| **Commands** | `src/commands/` | `mul_agent/commands/` | ✅ 已对齐 |
| **Channels** | `src/channels/` + `src/telegram/` etc. | `mul_agent/network/` | ⚠️ 部分对齐 |
| **Memory** | `src/memory/` | `mul_agent/memory/` | ✅ 已对齐 |
| **Config** | `src/config/` | `mul_agent/brain/config_manager.py` | ⚠️ 部分对齐 |
| **Infra** | `src/infra/` | ❌ 缺失 | ⚠️ 需要创建 |
| **CLI** | `src/cli/` | `mul_agent/cli/` | ✅ 已对齐 |
| **Tests** | `*.test.ts` (colocated) | `tests/` (separate) | ⚠️ 需要调整 |

---

## 二、核心设计模式对比

### 1. 配置文件驱动

**OpenClaw**:
```yaml
# skills/coding-agent/SKILL.md
---
name: coding-agent
description: 'Delegate coding tasks to Codex, Claude Code, or Pi agents...'
metadata:
  openclaw:
    emoji: "🧩"
    requires:
      anyBins: ["claude", "codex", "opencode", "pi"]
---

# Skill 详细说明...
```

**mul-agent**:
```yaml
# wang/agent-team/core_brain/SKILL.md
---
name: core_brain
description: 团队指挥官和管理者...
metadata:
  mul_agent:
    emoji: "🧠"
    role: commander
    title: 团队指挥官
    tools:
      - chat
      - memory
      - file_edit
      - response
---

# Skill 详细说明...
```

**状态**: ✅ **已对齐** - 使用相同的 YAML frontmatter + Markdown 格式

---

### 2. 工具系统

**OpenClaw**:
- 工具定义在 `skills/*/SKILL.md` 中
- 使用 `bash pty:true command:"..."` 执行
- 工具门控检查（`requires.bins`, `requires.env` 等）

**mul-agent**:
```python
# mul_agent/tools/base.py
class SyncTool(ABC):
    metadata: ToolMetadata

    def execute_sync(self, **kwargs) -> ToolResult:
        pass

    def check_gate(self) -> bool:
        # 检查 ToolGate 条件
        pass

# ToolGate 定义
@dataclass
class ToolGate:
    bins: List[str] = field(default_factory=list)
    env: List[str] = field(default_factory=list)
    os: List[str] = field(default_factory=list)
    always: bool = False
```

**状态**: ✅ **已对齐** - ToolGate 设计完全参考 OpenClaw

---

### 3. Hook 系统

**OpenClaw**:
- Hook  phases: `pre_tool_use`, `post_tool_use`, `session_start`, etc.
- Hook priorities
- Hook 从配置文件加载

**mul-agent**:
```python
# mul_agent/hooks/base.py
class HookEvent(str, Enum):
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    SESSION_START = "session_start"
    SESSION_END = "session_end"

class HookPriority(int, Enum):
    HIGH = 1
    NORMAL = 5
    LOW = 10

class BaseHook(ABC):
    def execute(self, context: HookContext) -> Optional[Dict[str, Any]]:
        pass
```

**状态**: ✅ **已对齐** - 事件类型和优先级设计一致

---

### 4. 插件系统

**OpenClaw**:
```typescript
// src/plugin-sdk/api.ts
export class PluginAPI {
  registerTool(name, description, schema, handler) { }
  registerHook(phase, name, handler) { }
  registerCommand(name, description, handler) { }
}
```

**mul-agent**:
```python
# mul_agent/plugins/sdk.py
class PluginAPI:
    def register_tool(self, name, description, schema) -> Callable:
        pass

    def register_hook(self, phase, name, priority) -> Callable:
        pass

    def register_command(self, name, description, aliases) -> Callable:
        pass
```

**状态**: ✅ **已对齐** - 插件 API 设计一致

---

## 三、架构差异分析

### 1. 基础设施层 (Infra)

**OpenClaw 有**:
```
src/infra/
├── binaries.py      # 二进制文件检查
├── dotenv.py        # 环境变量加载
├── paths.py         # 路径管理
├── ports.py         # 端口管理
├── runtime-guard.py # 运行时检查
└── ...
```

**mul-agent 缺失**:
```
mul_agent/infra/  (目录存在但为空)
```

**建议**: 创建基础设施模块

---

### 2. 测试文件位置

**OpenClaw**:
```
src/
├── logger.test.ts       # 测试与源码并列
├── utils.test.ts
└── docker-setup.e2e.test.ts
```

**mul-agent**:
```
mul_agent/
├── src/                 # 源码
tests/                   # 测试分离
├── test_router.py
├── test_handlers.py
└── ...
```

**建议**: 将测试文件移动到源码旁边（可选，非必须）

---

### 3. 配置系统

**OpenClaw**:
```typescript
// src/config/config.ts
export async function loadConfig(): Promise<Config> {
  // 加载 ~/.openclaw/config.json
  // 合并环境变量
  // 处理 session 配置
}
```

**mul-agent**:
```python
# mul_agent/brain/config_manager.py
class ConfigManager:
    def load(self, agent_id, config_type):
        # 加载 wang/agent-team/{agent_id}/{type}.md
        pass
```

**差异**: OpenClaw 使用集中式配置，mul-agent 使用分散式配置（每个 agent 独立）

**建议**: 保持 mul-agent 设计，更符合多 Agent 场景

---

### 4. Channel 系统

**OpenClaw**:
```
src/
├── channels/            # Channel 抽象层
├── telegram/            # 具体 Channel 实现
├── discord/
├── slack/
├── signal/
└── web/                 # Web 渠道
```

**mul-agent**:
```
mul_agent/
├── network/             # 网络层
└── api/                 # API 服务器
```

**差异**: OpenClaw 有更多内置渠道实现

**建议**: 可选扩展，当前设计足够

---

## 四、已实现的核心功能

### ✅ 已完成

1. **Agent 核心** (`mul_agent/core/agent.py`, `mul_agent/core/brain.py`)
   - Agent 基类
   - Brain 决策引擎
   - 配置系统

2. **工具系统** (`mul_agent/tools/`)
   - SyncTool/AsyncTool 基类
   - ToolMetadata, ToolResult, ToolGate
   - ToolManager, ToolRegistry
   - 内置工具 (Bash, Read, Write, Edit)

3. **Hook 系统** (`mul_agent/hooks/`)
   - BaseHook, HookEvent, HookPriority
   - HookManager, HookRegistry
   - 内置 Hook (LogInvocation, FormatOutput, Permission)

4. **技能系统** (`mul_agent/skills/`)
   - BaseSkill
   - SkillManager
   - 配置文件格式 (SKILL.md)

5. **插件系统** (`mul_agent/plugins/`)
   - PluginAPI
   - PluginManifest, PluginContext
   - ToolRegistry, HookRegistry, CommandRegistry

6. **配置文件驱动**
   - AGENT.md / SKILL.md 格式
   - YAML frontmatter + Markdown 内容

---

## 五、待改进项目

### 高优先级

| 项目 | 描述 | 参考文件 |
|------|------|----------|
| **Infra 模块** | 创建基础设施层 | `openclaw/src/infra/` |
| **Config 简化** | 统一配置加载逻辑 | `openclaw/src/config/config.ts` |
| **工具提示词生成** | 从 SKILL.md 生成工具列表 | `openclaw/skills/*/SKILL.md` |

### 中优先级

| 项目 | 描述 | 参考文件 |
|------|------|----------|
| **测试文件位置** | 移动到源码旁边 | `openclaw/src/*.test.ts` |
| **Channel 抽象** | 定义 Channel 接口 | `openclaw/src/channels/` |
| **更多内置工具** | 参考 OpenClaw 工具集 | `openclaw/skills/` |

### 低优先级

| 项目 | 描述 | 参考文件 |
|------|------|----------|
| **Extensions** | 扩展示例 | `openclaw/extensions/` |
| **CLI 增强** | 丰富 CLI 命令 | `openclaw/src/cli/` |
| **文档完善** | 完善使用文档 | `openclaw/docs/` |

---

## 六、结论

### 架构对齐状态

mul-agent 已经在 **核心设计模式** 上与 OpenClaw 高度对齐：

1. ✅ **配置文件驱动** - SKILL.md 格式一致
2. ✅ **工具系统** - ToolGate 设计一致
3. ✅ **Hook 系统** - 事件和优先级设计一致
4. ✅ **插件系统** - PluginAPI 设计一致
5. ✅ **核心引擎** - Agent/Brain 分层清晰

### 主要差异

1. **Infra 模块** - 需要补充基础设施
2. **测试位置** - 可选调整
3. **Channel 系统** - 可选扩展

### 建议

保持当前架构，按优先级逐步补充缺失模块。当前设计已经足够支持多 Agent 协作场景。

---

## 七、参考资源

- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [OpenClaw AGENTS.md](https://github.com/openclaw/openclaw/blob/main/AGENTS.md)
- [mul-agent 架构文档](./ARCHITECTURE.md)
- [重构计划](./REFACTOR_PLAN.md)
