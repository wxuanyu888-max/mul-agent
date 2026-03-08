# Agent Team 配置指南

> 本项目 Agent 团队配置和模板说明

---

## 目录结构

```
agent-team/
├── .templates/             # 模板目录
│   ├── agent.yml          # 统一配置模板
│   ├── executor.md        # 执行者模板
│   ├── planner.md         # 规划师模板
│   └── coordinator.md     # 协调员模板
├── core_brain/            # 团队指挥官
│   ├── soul.md
│   ├── user.md
│   └── memory.md
├── alice/                 # 代码实现者
│   ├── soul.md
│   └── user.md
├── bob/                   # 技术规划师
│   ├── soul.md
│   └── user.md
└── wangyue/               # 日常助手
    ├── soul.md
    └── user.md
```

---

## 快速开始

### 创建新 Agent

```bash
# 1. 创建目录
mkdir -p wang/agent-team/new_agent

# 2. 选择模板
# executor.md    - 执行者（代码、文档等）
# planner.md     - 规划师（架构、设计）
# coordinator.md - 协调员（团队管理）

# 3. 复制模板
cp wang/agent-team/.templates/executor.md wang/agent-team/new_agent/agent.yml

# 4. 编辑配置
# 修改 agent_id, name, role 等字段
```

---

## Agent 类型

| 类型 | 用途 | LLM 温度 | 典型工具 |
|------|------|---------|---------|
| **Executor** | 执行者 | 0.3 | bash, file_edit |
| **Planner** | 规划师 | 0.5 | bash, file_edit, chat |
| **Coordinator** | 协调员 | 0.7 | 全部工具 |

---

## 配置格式

### 标准配置

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
  bash: true
  file_edit: true
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

---

## 现有 Agent

| Agent | 类型 | 职责 |
|-------|------|------|
| **core_brain** | Coordinator | 团队指挥官，负责任务分配和协调 |
| **alice** | Executor | 代码实现，Bug 修复 |
| **bob** | Planner | 任务规划，架构设计 |
| **wangyue** | Executor | 日常任务，问题解答 |

---

## 模板说明

### executor.md - 执行者

适用于：
- 代码实现
- 文档编写
- 数据处理
- 测试编写

特点：
- 温度较低 (0.3)，输出更精确
- 专注于具体执行

### planner.md - 规划师

适用于：
- 任务分解
- 架构设计
- 技术选型
- 项目分析

特点：
- 温度适中 (0.5)，平衡创造性和准确性
- 提供多方案对比

### coordinator.md - 协调员

适用于：
- 团队协调
- 任务分配
- 质量控制
- Agent 管理

特点：
- 温度较高 (0.7)，更强的灵活性
- 拥有全部工具权限

---

## 命名规范

| ✅ 正确 | ❌ 错误 |
|--------|--------|
| `alice`, `bob` | `coder`, `planner` |
| `xiaoming`, `awei` | `agent1`, `test` |
| 具体的人名 | 角色名/泛化名 |

---

## 最佳实践

1. **保持简洁** - 配置不要过于复杂
2. **职责单一** - 每个 Agent 专注于一个领域
3. **最小权限** - 只启用必要的工具
4. **清晰提示** - 提示词要具体明确

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 5.0 | 2026-03-08 | 统一配置格式，简化模板 |
| 4.0 | 2026-03-08 | 强制具体名字，禁止角色名 |
| 3.0 | 2026-03-08 | 精简为核心 4 路由 |
