# Wang 文件夹规范

> 与 `~/.claude` 结构保持一致的项目级配置和数据存储

---

## 一、核心原则

1. **结构一致**: 与 `~/.claude` 文件夹结构保持一致
2. **项目优先**: 项目级配置优先级高于全局配置
3. **Agent 团队**: `agent-team/` 存储本项目专属的 Agent 配置

---

## 二、目录结构

```
wang/
├── settings.json          # 项目设置（对应 ~/.claude/settings.json）
├── agent-team/            # 项目 Agent 团队配置（项目特有）
│   ├── core_brain/
│   │   ├── soul.md
│   │   ├── user.md
│   │   └── skill.md
│   └── ...
├── commands/              # 自定义命令（对应 ~/.claude/commands）
├── skills/                # 技能库（对应 ~/.claude/skills）
├── rules/                 # 规则库（对应 ~/.claude/rules）
├── mcp-configs/           # MCP 配置（对应 ~/.claude/mcp-configs）
├── hooks/                 # Hooks 配置（对应 ~/.claude/hooks）
├── workspace/             # 工作区数据
├── todos/                 # Todo 数据（对应 ~/.claude/todos）
├── history/               # 历史记录（对应 ~/.claude/history.jsonl）
├── projects/              # 项目数据（对应 ~/.claude/projects）
├── file-history/          # 文件历史（对应 ~/.claude/file-history）
├── tasks/                 # 任务数据（对应 ~/.claude/tasks）
├── cache/                 # 缓存数据（对应 ~/.claude/cache）
├── paste-cache/           # 粘贴缓存（对应 ~/.claude/paste-cache）
├── session-env/           # 会话环境（对应 ~/.claude/session-env）
├── debug/                 # 调试数据（对应 ~/.claude/debug）
├── backups/               # 备份数据（对应 ~/.claude/backups）
└── agents/                # Agent 配置（对应 ~/.claude/agents）
```

### 与 ~/.claude 对照表

| Wang 文件夹 | ~/.claude 对应 | 说明 |
|------------|---------------|------|
| `settings.json` | `settings.json` | 项目级设置 |
| `agent-team/` | (无) | **项目特有** - Agent 团队配置 |
| `commands/` | `commands/` | 自定义命令 |
| `skills/` | `skills/` | 技能库 |
| `rules/` | `rules/` | 规则库 |
| `mcp-configs/` | `mcp-configs/` | MCP 服务器配置 |
| `hooks/` | `hooks/` | Hooks 配置 |
| `todos/` | `todos/` | Todo 数据 |
| `history/` | `history.jsonl` | 对话历史 |
| `projects/` | `projects/` | 项目数据 |
| `file-history/` | `file-history/` | 文件修改历史 |
| `tasks/` | `tasks/` | 任务数据 |
| `cache/` | `cache/` | 缓存数据 |
| `paste-cache/` | `paste-cache/` | 粘贴缓存 |
| `session-env/` | `session-env/` | 会话环境变量 |
| `debug/` | `debug/` | 调试日志 |
| `backups/` | `backups/` | 备份文件 |
| `agents/` | `agents/` | Agent 定义 |

---

## 三、同步命令

### 从全局同步到项目

```bash
# 同步技能库
cp -r ~/.claude/skills/* wang/skills/

# 同步规则库
cp -r ~/.claude/rules/* wang/rules/

# 同步命令
cp -r ~/.claude/commands/* wang/commands/

# 同步 MCP 配置
cp -r ~/.claude/mcp-configs/* wang/mcp-configs/

# 同步 Hooks
cp -r ~/.claude/hooks/* wang/hooks/
```

### 从项目同步到全局

```bash
# 同步项目技能到全局
cp -r wang/skills/* ~/.claude/skills/

# 同步项目规则到全局
cp -r wang/rules/* ~/.claude/rules/
```

---

## 四、配置优先级

配置加载优先级（从高到低）：

1. **项目级配置** (`wang/`) - 最高优先级
2. **全局配置** (`~/.claude/`) - 中等优先级
3. **默认配置** - 最低优先级

---

## 五、Agent 团队配置

`agent-team/` 目录存储本项目专属的 Agent 配置，每个 Agent 包含：

```
agent-team/{agent_id}/
├── soul.md           # Agent 核心特质、行为模式
├── user.md           # 职责、能力、LLM 配置
├── skill.md          # 可用技能列表
└── memory.md         # 记忆配置（可选）
```

### 示例：core_brain Agent

```yaml
# soul.md
---
version: '1.0'
name: core_brain
description: 核心大脑 - 本地运行的 AI 助手
role: 核心协调器
core_traits:
  personality: 冷静、分析型、协作导向
  values: [效率，协作，透明]
  goals: [协调多 Agent 合作，优化任务分配]
---

# Core Brain Soul
这是运行在你本地电脑上的 AI 助手...
```

```yaml
# user.md
---
version: '1.0'
agent_id: core_brain
role:
  type: coordinator
  title: Core Brain
  responsibilities:
  - 任务分析与分解
  - Agent 协调与合作
capabilities:
  max_team_size: 10
  can_create_agent: true
  can_execute_tools: true
llm:
  enabled: true
  max_tokens: 2048
---

# 重要说明
## 运行环境
- 我是本地 AI 助手，运行在用户的电脑上
- 我可以直接执行命令，不需要用户手动操作
...
```

---

## 六、快速开始

### 1. 初始化项目配置

```bash
# 复制全局配置到项目
mkdir -p wang/{commands,skills,rules,mcp-configs,hooks}
cp -r ~/.claude/skills/* wang/skills/
cp -r ~/.claude/rules/* wang/rules/
cp -r ~/.claude/commands/* wang/commands/
```

### 2. 创建 Agent 团队

```bash
# 创建新 Agent
mkdir -p wang/agent-team/my_agent
cp storage/agent_templates/devops_engineer/*.md wang/agent-team/my_agent/
```

### 3. 配置项目设置

编辑 `wang/settings.json` 以覆盖全局设置。

---

## 七、常见问题

### Q: 为什么要与 ~/.claude 结构保持一致？

**A**: 便于理解和维护，用户可以轻松在项目和全局之间同步配置。

### Q: agent-team 和 storage/agents 有什么区别？

**A**:
- `wang/agent-team/` 是项目级 Agent 配置，优先加载
- `storage/agents/` 是全局/共享 Agent 配置，作为回退

### Q: 如何添加项目专属的技能？

**A**: 在 `wang/skills/` 目录下创建新的 `.md` 文件，项目会优先加载。

### Q: 如何同步全局技能到项目？

**A**: 使用 `cp -r ~/.claude/skills/* wang/skills/` 命令同步。
