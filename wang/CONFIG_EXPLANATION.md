# Wang 目录配置说明

本文档说明 `wang/` 目录中的配置文件结构和用途。

## 目录结构

```
wang/
├── .agent.config              # 工作区配置
├── mcp/                       # MCP 服务器配置
│   └── mcp-servers.json       # MCP 服务器定义
├── skill/                     # 技能定义
│   ├── coding-standards.md    # 编码标准
│   └── tdd-workflow.md        # TDD 工作流
├── rule/                      # 规则定义
│   ├── security.md            # 安全指南
│   └── performance.md         # 性能优化
├── hook/                      # Hook 定义 (待配置)
└── agent-team/                # Agent 团队配置
    └── {agent_name}/
        ├── soul.md           # Agent 核心特质
        ├── user.md           # 工具使用、路由规则
        └── skill.md          # 技能定义
```

## 配置文件说明

### MCP 配置 (`mcp/mcp-servers.json`)

定义可用的 MCP (Model Context Protocol) 服务器:

| MCP 服务器 | 用途 | 何时调用 |
|-----------|------|---------|
| `github` | GitHub 操作 (PRs, issues, repos) | 创建 PR、查看 issues、操作仓库时 |
| `firecrawl` | 网页抓取和爬取 | 需要获取网页内容时 |
| `memory` | 跨会话持久记忆 | 需要记住跨会话信息时 |
| `sequential-thinking` | 链式思考推理 | 需要复杂推理分析时 |
| `filesystem` | 文件系统操作 | 读写项目文件时 |
| `chrome-devtools` | Chrome 浏览器自动化 | E2E 测试、浏览器调试时 |

**注意**: MCP 配置来自 `~/.claude/mcp-configs/mcp-servers.json`

### Skill 配置 (`skill/*.md`)

定义 Agent 可以调用的技能:

| Skill | 触发场景 | 来源 |
|-------|---------|------|
| `coding-standards` | 写代码、代码审查、重构时 | `~/.claude/skills/coding-standards/` |
| `tdd-workflow` | 新功能、bug 修复、重构时 | `~/.claude/commands/tdd.md` |

**注意**: Skill 是从 `~/.claude/skills/` 和 `~/.claude/commands/` 复制的

### Rule 配置 (`rule/*.md`)

定义编码规则和安全指南:

| Rule | 用途 | 何时应用 |
|------|------|---------|
| `security` | 安全检查清单 | 任何提交之前 |
| `performance` | 性能优化指南 | 性能敏感代码 |

**注意**: Rule 是从 `~/.claude/rules/` 复制的

## Agent 是否会调用 MCP 和 Skill?

### 是的，会调用!

查看 `agent-team/wangyue/user.md`:

```yaml
tools:
  enabled:
    - bash
    - mcp          # ← MCP 已启用
    - memory
  mcp:
    enabled: true
    providers:
      - google_mcp
      - browser_mcp
```

**MCP 调用条件:**
1. Agent 的 `user.md` 中 `tools.mcp.enabled: true`
2. 指定了 MCP providers
3. 任务需要 MCP 提供的能力

**Skill 调用条件:**
1. Agent 的 `skill.md` 中定义了技能
2. 任务场景匹配技能的触发条件
3. 用户显式调用 (如 `/plan`, `/tdd`)

## 实际调用示例

### MCP 调用示例

当用户说 "帮我抓取这个网页的内容" 时:

```
用户：请抓取 https://example.com 的内容

Agent (wangyue):
检测到需要网页抓取，调用 firecrawl MCP...

[MCP: firecrawl]
→ scrape(url="https://example.com")
← {content: "...", title: "..."}

这是网页内容：...
```

### Skill 调用示例

当用户说 "请帮我规划这个功能" 时:

```
用户：我想添加实时通知功能

Agent (wangyue):
调用 planner skill 进行分析...

[Skill: planner]
→ analyze_requirements("实时通知功能")
→ create_implementation_plan()

# 实施计划：实时通知功能

## 需求重述
- 当市场解决时向用户发送通知
- 支持多种通知渠道...

## 实施步骤
### 第 1 阶段：数据库模式
...
```

## 配置同步

这些配置是从全局 `~/.claude/` 目录复制到项目特定的 `wang/` 目录的:

| 源目录 | 目标目录 | 说明 |
|-------|---------|------|
| `~/.claude/mcp-configs/` | `wang/mcp/` | MCP 服务器配置 |
| `~/.claude/skills/` | `wang/skill/` | 技能定义 |
| `~/.claude/commands/` | `wang/skill/` | 命令定义 |
| `~/.claude/rules/` | `wang/rule/` | 规则定义 |
| `~/.claude/agents/` | `wang/agent-team/` | Agent 定义 |

## 添加新配置

### 添加新的 MCP 服务器

编辑 `wang/mcp/mcp-servers.json`:

```json
{
  "mcpServers": {
    "new-mcp": {
      "command": "npx",
      "args": ["-y", "@scope/package"],
      "description": "Description of what it does"
    }
  }
}
```

### 添加新的 Skill

创建 `wang/skill/my-skill.md`:

```markdown
---
name: my-skill
description: Description of the skill
---

# My Skill

## When to Activate

- Scenario 1
- Scenario 2

## How It Works

Skill implementation...
```

### 添加新的 Rule

创建 `wang/rule/my-rule.md`:

```markdown
---
name: my-rule
description: Description of the rule
---

# My Rule

## Checklist

- [ ] Check 1
- [ ] Check 2

## Examples

Code examples...
```

## 验证配置

运行以下命令验证配置是否生效:

```bash
# 验证 MCP 配置
cat wang/mcp/mcp-servers.json | jq '.mcpServers | keys'

# 验证 Skill 配置
ls -la wang/skill/

# 验证 Rule 配置
ls -la wang/rule/

# 验证 Agent 配置
ls -la wang/agent-team/
```

## 故障排除

### MCP 未调用

1. 检查 Agent 的 `user.md` 中 `tools.mcp.enabled` 是否为 `true`
2. 检查 MCP 服务器配置是否正确
3. 确认 MCP 工具在权限列表中

### Skill 未调用

1. 检查技能文件是否在 `wang/skill/` 目录
2. 确认技能描述与任务场景匹配
3. 检查用户是否使用正确的命令调用 (如 `/plan`)

---

**最后更新**: 2026-03-06
