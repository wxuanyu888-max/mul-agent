# mul-agent 架构重构方案

> 基于 OpenClaw 实际架构的 Python 版本设计

---

## 一、OpenClaw 架构分析

### 核心特点

1. **扁平化文件系统**
   - `skills/` - 每个技能是一个独立目录，包含 SKILL.md
   - `extensions/` - 每个扩展是一个独立目录
   - `agents/` - 每个 agent 是一个独立目录

2. **配置文件驱动**
   - SKILL.md 包含 YAML frontmatter + Markdown 内容
   - 配置与代码共存

3. **src/ 核心代码**
   - 大量具体实现文件
   - 无抽象的 manager/registry 层
   - 通过文件系统直接加载

4. **插件 SDK**
   - `plugin-sdk/` 定义接口
   - `plugins/` 包含具体插件实现

---

## 二、mul-agent 新架构设计

### 目录结构

```
mul-agent/
├── mul_agent/                  # Python 包
│   ├── __init__.py
│   ├── core/                   # 核心引擎
│   │   ├── __init__.py
│   │   ├── brain.py           # 主大脑（类似 src/index.ts）
│   │   ├── agent.py           # Agent 基类
│   │   ├── config.py          # 配置系统
│   │   ├── sessions.py        # 会话管理
│   │   └── types.py           # 核心类型定义
│   │
│   ├── tools/                  # 工具系统
│   │   ├── __init__.py
│   │   ├── base.py            # 工具基类
│   │   ├── builtin/           # 内置工具
│   │   │   ├── bash.py
│   │   │   ├── file_edit.py
│   │   │   ├── read.py
│   │   │   └── write.py
│   │   └── registry.py        # 工具注册（从文件加载）
│   │
│   ├── hooks/                  # Hook 系统
│   │   ├── __init__.py
│   │   ├── base.py            # Hook 基类
│   │   └── builtin/           # 内置 hooks
│   │
│   ├── commands/               # 命令系统
│   │   ├── __init__.py
│   │   ├── base.py            # 命令基类
│   │   └── builtin/           # 内置命令
│   │
│   ├── channels/               # 通信渠道
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── web.py             # Web 渠道
│   │
│   ├── memory/                 # 记忆系统
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── long_term.py
│   │
│   ├── plugins/                # 插件目录
│   │   ├── __init__.py
│   │   └── sdk/               # 插件 SDK
│   │       ├── __init__.py
│   │       ├── api.py
│   │       └── types.py
│   │
│   └── infra/                  # 基础设施
│       ├── __init__.py
│       ├── binaries.py        # 二进制检查
│       ├── dotenv.py          # 环境变量
│       ├── paths.py           # 路径管理
│       └── logging.py         # 日志系统
│
├── agents/                     # Agent 定义（类似 openclaw/skills）
│   ├── core_brain/
│   │   ├── AGENT.md           # Agent 配置文件
│   │   └── prompt.md          # 提示词
│   ├── alice/
│   │   ├── AGENT.md
│   │   └── prompt.md
│   └── bob/
│       ├── AGENT.md
│       └── prompt.md
│
├── skills/                     # 技能定义
│   ├── coding-agent/
│   │   └── SKILL.md
│   ├── bash-tool/
│   │   └── SKILL.md
│   └── memory-core/
│       └── SKILL.md
│
├── extensions/                 # 扩展模块
│   ├── discord/
│   │   └── EXTENSION.md
│   └── feishu/
│       └── EXTENSION.md
│
├── cli/                        # CLI 入口
│   ├── __init__.py
│   └── main.py
│
├── tests/                      # 测试
│   ├── test_brain.py
│   ├── test_agent.py
│   └── ...
│
└── docs/                       # 文档
    ├── ARCHITECTURE.md
    └── ...
```

---

## 三、核心设计

### 1. AGENT.md 配置文件格式

```yaml
---
agent_id: core_brain
name: Core Brain
role:
  type: supervisor
  title: 团队指挥官
  responsibilities:
    - 任务分配
    - 团队协调
tools:
  bash: true
  chat: true
  memory: true
llm:
  enabled: true
  model: claude-sonnet-4-20250514
  temperature: 0.3
---

# prompt.md

你是团队的核心大脑，负责...
```

### 2. SKILL.md 配置文件格式

```yaml
---
skill_id: bash_tool
name: Bash Tool
description: 执行 shell 命令
metadata:
  requires:
    bins: ["bash"]
  os: ["darwin", "linux"]
---

# 技能说明

使用 bash 工具执行命令...
```

### 3. 核心代码组织

```python
# mul_agent/core/brain.py
"""
主大脑 - 类似 OpenClaw 的 src/index.ts
"""
from mul_agent.core.agent import Agent
from mul_agent.core.config import load_config
from mul_agent.tools.registry import load_tools
from mul_agent.hooks.registry import load_hooks
from mul_agent.infra.logging import setup_logging

def main():
    setup_logging()
    config = load_config()
    agent = Agent(config)

    # 从文件加载工具和 hooks
    tools = load_tools("skills/")
    hooks = load_hooks("hooks/builtin/")

    # 运行
    agent.run()

if __name__ == "__main__":
    main()
```

---

## 四、与当前架构的差异

| 当前架构 | OpenClaw 架构 | 新架构 |
|---------|-------------|-------|
| src/agents/base.py | src/agents/*.ts | core/agent.py |
| src/agents/manager.py | 无 manager | 文件系统加载 |
| src/agents/registry.py | 无 registry | tools/registry.py |
| src/tools/manager.py | 无 manager | 直接调用 |
| skills/base.py | skills/*/SKILL.md | skills/*/SKILL.md |
| 复杂的管理器类 | 简单文件加载 | 简化加载逻辑 |

---

## 五、实施步骤

### 阶段 1: 核心重构
1. 删除现有的 manager/registry 抽象层
2. 创建 `core/` 目录，包含 brain.py, agent.py, config.py
3. 创建 `infra/` 目录，包含基础设施代码

### 阶段 2: 工具系统
1. 简化 `tools/` 为 base.py + builtin/ + registry.py
2. 将现有工具迁移到 `tools/builtin/`

### 阶段 3: 配置文件驱动
1. 将现有 agents 迁移到 `agents/*/AGENT.md` 格式
2. 创建 `skills/*/SKILL.md` 配置文件

### 阶段 4: 扩展系统
1. 创建 `extensions/` 目录
2. 定义扩展配置格式

---

## 六、关键设计原则

1. **文件即配置**: 使用 AGENT.md, SKILL.md 等配置文件
2. **简单加载**: 通过文件系统遍历加载，而非复杂注册表
3. **代码与配置共存**: 每个模块有自己的目录
4. **扁平化**: 减少抽象层，增加可读性
