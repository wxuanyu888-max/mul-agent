# 项目指南 - mul-agent

> 一个自主的多 Agent 协作系统

---

## 快速开始

### 启动 Agent 服务

```bash
# 激活虚拟环境（如果有）
source .venv/bin/activate

# 启动核心大脑
python -m mul_agent.main
```

### 创建新 Agent

```bash
# 方法 1：使用模板
mkdir -p wang/agent-team/new_agent

# 复制模板（选择适合的角色）
cp wang/agent-team/.templates/executor.md wang/agent-team/new_agent/agent.yml

# 编辑配置
# 修改 agent_id, name, role 等字段
```

### 与 Agent 交互

```bash
# 直接对话
你好，帮我分析一下这个项目

# 执行命令
$ ls -la

# 委派任务
把这个功能交给 alice 实现
```

---

## 项目结构

```
mul-agent/
├── mul_agent/              # 核心代码
│   ├── api/                # API 服务器
│   ├── brain/              # Agent 核心大脑
│   │   ├── brain.py        # Agent 主类
│   │   ├── llm.py          # LLM 客户端
│   │   ├── router.py       # 路由分发器
│   │   └── config_manager.py
│   ├── handlers/           # 路由处理器
│   ├── skills/             # 技能系统
│   ├── commands/           # 命令系统
│   └── hooks/              # 钩子系统
│
├── wang/                   # 项目配置和数据
│   ├── agent-team/         # Agent 团队配置
│   │   ├── core_brain/     # 团队指挥官
│   │   ├── alice/          # 代码实现者
│   │   ├── bob/            # 技术规划师
│   │   └── .templates/     # Agent 模板
│   ├── rules/              # 项目规则
│   ├── skills/             # 技能库
│   ├── commands/           # 自定义命令
│   └── settings.json       # 项目设置
│
├── storage/                # 全局存储
│   ├── memory/             # 记忆数据
│   └── token_usage/        # Token 使用统计
│
└── frontend/               # Web UI (可选)
    ├── src/
    ├── public/
    └── package.json
```

---

## Agent 团队

| Agent | 职责 | 何时使用 |
|-------|------|----------|
| **core_brain** | 团队指挥官 | 复杂任务、任务分配、团队协调 |
| **alice** | 代码实现 | 写代码、修 bug、代码审查 |
| **bob** | 技术规划 | 架构设计、技术选型、任务规划 |
| **wangyue** | 日常助手 | 日常咨询、文档编写、简单任务 |

---

## 常用命令

### 对话命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `$ 命令` | 执行 shell 命令 | `$ ls -la` |
| `# chat agent_id:xxx` | 与其他 Agent 对话 | `# chat agent_id:alice message:帮我写代码` |
| `# memory` | 管理记忆 | `# memory action:list` |
| `# heart` | Agent 自省 | `# heart` |

### 系统命令

| 命令 | 说明 |
|------|------|
| `/test` | 运行测试 |
| `/deploy` | 部署应用 |
| `/clean` | 清理缓存 |

---

## 路由系统

| 路由 | 说明 | 示例 |
|------|------|------|
| `bash` | 执行 shell 命令 | `# bash ls -la` |
| `file_edit` | 文件编辑 | `# file_edit path:main.py` |
| `chat` | Agent 对话 | `# chat agent_id:alice message:hi` |
| `memory` | 记忆管理 | `# memory action:write content:...` |
| `create_user` | 创建 Agent | `# create_user name:coder` |
| `create_team` | 创建团队 | `# create_team name:dev-team` |
| `heart` | 自省进化 | `# heart` |
| `response` | 直接回复 | `# response 你好！` |

---

## 配置文件

### Agent 配置格式

```yaml
---
version: "1.0"
agent_id: alice
name: Alice
role:
  type: executor
  title: 代码工程师
  responsibilities:
    - 代码实现
    - Bug 修复
tools:
  file_edit: true
  bash: true
  memory: true
  chat: true
llm:
  enabled: true
  model: claude-sonnet-4-20250514
  temperature: 0.3
---

# prompt.md
你是 Alice，一名专业的软件工程师...
```

### 项目设置

编辑 `wang/settings.json`：

```json
{
  "llm": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514"
  },
  "agent": {
    "default_agent": "core_brain"
  }
}
```

---

## 开发指南

### 添加新 Agent

1. 创建目录
```bash
mkdir -p wang/agent-team/new_agent
```

2. 复制模板
```bash
cp wang/agent-team/.templates/executor.md wang/agent-team/new_agent/agent.yml
```

3. 编辑配置
```yaml
---
agent_id: new_agent
name: New Agent
role:
  type: worker
  title: 新角色
---
```

### 添加新技能

1. 创建技能文件
```python
# wang/skills/my_skill.py
from mul_agent.skills.base import BaseSkill

class MySkill(BaseSkill):
    skill_id = "my_skill"
    skill_name = "My Skill"
    skill_description = "Description"

    def execute(self, **kwargs):
        return {"result": "success"}
```

2. 注册技能
```python
brain.skill_manager.register_skill(MySkill)
```

---

## 规则与规范

- [代码规范](wang/rules/coding-standards.md)
- [Git 工作流](wang/rules/git-workflow.md)
- [安全规则](wang/rules/security.md)

---

## 调试

### 查看日志

```bash
# 查看最近的 Agent 输出
tail -f storage/logs/agent.log

# 查看 token 使用
cat storage/token_usage/core_brain.json
```

### 常见问题

**Q: Agent 无法响应？**
- 检查 LLM 配置是否正确
- 检查 API 密钥是否有效

**Q: 命令执行失败？**
- 检查命令权限
- 查看 `wang/agent-team/{agent_id}/user.md` 中的工具配置

**Q: 如何重置 Agent？**
```bash
rm -rf storage/memory/long_term/{agent_id}/*
```

---

## 相关资源

- [技能系统详解](docs/SKILL_HOOK_COMMAND_GUIDE.md)
- [Agent 配置说明](wang/agent-team/README.md)
- [项目规范](docs/README.md)
