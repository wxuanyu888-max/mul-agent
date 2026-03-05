# Configuration Specification - 配置文件规范

> 详细说明每个配置文件的作用、字段和用法
>
> **注意**: 配置文件使用 **Markdown格式** (.md)，而非JSON格式。

---

## 1. 配置文件总览

| 文件 | 作用 | 格式 | 管理者 |
|------|------|------|--------|
| `soul.md` | Agent的灵魂/核心特质 | Markdown | 核心大脑 |
| `user.md` | Agent的用户配置/角色 | Markdown | 核心大脑 |
| `skill.md` | Agent的技能配置 | Markdown | 核心大脑 |
| `memory.md` | 记忆系统配置 | Markdown | 核心大脑 |

---

## 2. soul.md (灵魂配置)

### 作用
定义Agent的核心特质、价值观、行为准则。这是最底层的"性格"定义。

### 文件格式

```markdown
---
version: 1.0
name: core_brain
description: 一个能够自我进化的多Agent系统
role: AI自我进化分析助手
---

# Soul 配置

- **version**: 1.0
- **name**: core_brain
- **description**: 一个能够自我进化的多Agent系统

## Core_Traits
- **personality**: Adaptive and self-improving
- **values**: ['efficiency', 'growth', 'autonomy']
- **goals**: ['continuous_improvement', 'team_coordination']

## Behavior_Patterns
- **decision_making**: data_driven
- **problem_solving**: systematic
- **communication**: collaborative

## Evolution_Rules
- **can_modify_self**: True
- **modification_scope**: ['soul', 'user', 'skill', 'memory']
- **snapshot_before_change**: True
- **self_check_required**: False

## Constraints
- **boundaries**: ['safe_execution', 'no_destructive_actions']
- **forbidden_actions**: []
- **role**: AI自我进化分析助手
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| version | string | 是 | 配置版本号 |
| name | string | 是 | Agent名称 |
| description | string | 否 | 描述信息 |
| role | string | 否 | 角色名称 |
| Core_Traits | section | 是 | 核心特质 (personality, values, goals) |
| Behavior_Patterns | section | 是 | 行为模式 (decision_making, problem_solving, communication) |
| Evolution_Rules | section | 是 | 进化规则 |
| Constraints | section | 否 | 约束边界 |

---

## 3. user.md (用户配置)

### 作用
定义Agent的角色定位、能力边界、可用工具和路由等。

### 文件格式

```markdown
---
name: agent_name
---

## 工具使用和路由

### bash：
只要不触碰系统文件都可以去用

### mcp：
目前支持：谷歌mcp，浏览器mcp

### 环境路由：
⏺ 本系统为 core_brain 提供了 6 种路由：
  路由名称: create_user
  处理器: CreateUserHandler
  功能描述: 创建新 Agent 成员
  ────────────────────────────────────────
  路由名称: bash
  处理器: BashHandler
  功能描述: 执行 shell 命令
  ...
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | Agent名称 |
| bash | section | 是 | Bash工具使用规则 |
| mcp | section | 是 | MCP工具配置 |
| 环境路由 | section | 是 | 可用路由列表 |

---

## 4. skill.md (技能配置)

### 作用
定义Agent能使用的具体技能和能力。

### 文件格式

```markdown
---
version: 1.0
---

## Skills

### skill_code
- **id**: skill_code
- **name**: 代码编写
- **description**: 编写和修改代码的能力
- **enabled**: true
- **parameters**:
  - languages: python, javascript, typescript
  - frameworks: fastapi, react, vue
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| version | string | 是 | 配置版本号 |
| Skills | section | 是 | 技能列表 |

---

## 5. memory.md (记忆配置)

### 作用
定义记忆的存储策略、读取规则、更新机制。

### 文件格式

```markdown
---
version: 1.0
---

## Memory Strategy

### Short-term
- storage: session
- max_size: 10MB
- ttl_seconds: 3600

### Long-term
- storage: file
- path: storage/memory/long_term
- compression: false
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| version | string | 是 | 配置版本号 |
| Short-term | section | 是 | 短期记忆配置 |
| Long-term | section | 是 | 长期记忆配置 |

---

## 6. Agent实例配置

### 目录结构
```
storage/
└── agents/
    └── {agent_id}/
        ├── soul.md
        ├── user.md
        ├── skill.md
        └── memory.md
```

### 创建新Agent

通过 `create_user` 路由创建新Agent时，会在 `storage/agents/{agent_id}/` 目录下创建完整的配置文件。

---

## 7. 版本控制

每个配置文件都包含 `version` 字段（在YAML front matter中），用于版本追踪和兼容处理。

### 版本号规则
- 格式: `主版本.次版本` (如 `1.0`, `1.1`, `2.0`)
- 主版本: 不兼容的API变更
- 次版本: 向后兼容的功能新增

---

## 8. 配置加载

配置文件通过 `ConfigManager` 类加载，使用 Python 的 `python-frontmatter` 或自定义解析器解析 Markdown 格式。

### 加载方式
```python
from mul_agent.brain.config_manager import ConfigManager

config_manager = ConfigManager("storage")
config = config_manager.load_all("core_brain")  # 加载所有配置
soul = config_manager.load("core_brain", "soul")  # 加载单个配置
```

---

## 9. 版本快照

每次修改配置前，系统会自动创建版本快照，存储在 `storage/snapshots/` 目录下。

### 快照格式
```
storage/snapshots/
└── {agent_id}_{config_type}_{timestamp}.md
```
