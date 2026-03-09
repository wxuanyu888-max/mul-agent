# Agent 提示词系统改造报告

参考 OpenClaw 的 SKILL.md 设计，完成了 mul-agent 提示词系统的改造。

## 一、改造内容

### 1. 新增 SKILL.md 文件格式

为每个 Agent 创建了符合 OpenClaw 格式的 `SKILL.md` 文件：

```
wang/agent-team/
├── alice/
│   └── SKILL.md          ← 新增
├── bob/
│   └── SKILL.md          ← 新增
├── core_brain/
│   └── SKILL.md          ← 新增
└── wangyue/
    └── SKILL.md          ← 新增
```

### 2. SKILL.md 文件结构

采用 OpenClaw 的 frontmatter + Markdown 格式：

```yaml
---
name: alice
description: 代码实现与审查。当需要：(1) 编写新功能代码 (2) 修复 Bug (3) 代码审查和优化 (4) 运行测试和验证 时触发。
metadata:
  mul_agent:
    emoji: "👩‍💻"
    role: executor
    title: 代码工程师
    tools:
      - file_edit
      - bash
      - memory
      - chat
---

# Alice - 代码工程师

## 何时使用 (When to Use)
✅ 使用 Alice 当：...
❌ 不使用 Alice 当：...

## 核心职责
...

## 路由规则
...

## 行为准则
...

## 工作示例
...
```

### 3. 新增 Skill Loader 模块

创建了 `mul_agent/brain/skill_loader.py` 模块，实现：

| 功能 | 说明 |
|------|------|
| `scan_skills()` | 扫描 agent-team 目录中的所有 Skill |
| `load_skill()` | 加载单个 Skill（支持新旧格式） |
| `build_skills_prompt()` | 构建 Skills 提示词 |
| `get_enabled_skills()` | 获取所有启用的 Skill |

### 4. 集成到 Context Builder

修改了 `mul_agent/brain/context_builder.py`：

```python
# 加载 SKILL.md
if HAS_SKILL_LOADER:
    skill_loader = SkillLoader(agent_team_dir)
    skills = skill_loader.get_enabled_skills()
    skills_prompt = skill_loader.build_skills_prompt(skills)

# 添加到系统提示词
if skills_prompt:
    prompt_parts.extend([
        "## 可用 Agent",
        skills_prompt
    ])
```

## 二、设计原则

参考 OpenClaw 的核心设计原则：

### 1. 简洁至上
- description 字段简洁明了，包含触发条件
- 避免冗余信息，只保留必要上下文

### 2. 明确触发条件
```yaml
description: 代码实现与审查。当需要：(1) 编写新功能代码 (2) 修复 Bug (3) 代码审查和优化 (4) 运行测试和验证 时触发。
```

### 3. 结构化正文
- `何时使用` - 明确使用场景
- `核心职责` - 职责描述
- `路由规则` - 路由映射表
- `行为准则` - 行为规范
- `工作示例` - 具体示例

### 4. 向后兼容
- 保留原有的 `user.md` 和 `soul.md`
- Skill Loader 自动回退到旧格式
- 新旧格式可以同时存在

## 三、Agent 列表

| Agent ID | 名字 | 角色 | 触发条件 |
|----------|------|------|----------|
| `alice` | Alice | 代码工程师 | 写代码、修 bug、代码审查 |
| `bob` | Bob | 技术规划师 | 任务规划、架构设计、技术选型 |
| `core_brain` | Core Brain | 团队指挥官 | 任务分配、多 Agent 协作 |
| `wangyue` | 望月 | 用户助理 | 日常问答、执行命令、记忆管理 |

## 四、测试结果

```python
# 测试加载
from mul_agent.brain.skill_loader import load_skills, build_skills_prompt

skills = load_skills('wang/agent-team')
# Loaded 4 skills:
#   - core_brain: 团队指挥官和管理者...
#   - bob: 技术规划与架构设计...
#   - alice: 代码实现与审查...
#   - wangyue: 日常助理和问题解决...

print(build_skills_prompt('wang/agent-team'))
# 输出格式化的 Agent 列表表格
```

## 五、后续改进建议

### 1. 添加 Eligibility 检查
参考 OpenClaw 的 `shouldIncludeSkill()`，添加：
- OS 检查（某些 Agent 只在特定平台可用）
- 依赖检查（需要特定二进制文件）
- 环境变量检查

### 2. 添加安全扫描
参考 OpenClaw 的 `scanDirectoryWithSummary()`，对 Agent 代码进行安全扫描。

### 3. 添加技能安装
参考 OpenClaw 的 `installSkill()`，支持动态安装新 Agent。

### 4. 优化提示词长度
实现 binary search 限制 prompt 长度：
```python
if prompt.length > maxSkillsPromptChars:
    # 截断或移除部分技能
```

## 六、文件变更清单

### 新增文件
- `wang/agent-team/alice/SKILL.md`
- `wang/agent-team/bob/SKILL.md`
- `wang/agent-team/core_brain/SKILL.md`
- `wang/agent-team/wangyue/SKILL.md`
- `mul_agent/brain/skill_loader.py`

### 修改文件
- `mul_agent/brain/context_builder.py` - 集成 SKILL.md 加载

### 保留文件（向后兼容）
- `wang/agent-team/*/user.md`
- `wang/agent-team/*/soul.md`

## 七、使用说明

### 加载 Skills
```python
from mul_agent.brain.skill_loader import load_skills

skills = load_skills('wang/agent-team')
for skill in skills:
    print(f"{skill.skill_id}: {skill.description}")
```

### 构建提示词
```python
from mul_agent.brain.skill_loader import build_skills_prompt

prompt = build_skills_prompt('wang/agent-team')
print(prompt)
```

### 在系统中使用
```python
from mul_agent.brain.context_builder import ContextBuilder
from mul_agent.brain.config_manager import ConfigManager

config_manager = ConfigManager(Path('wang'))
builder = ContextBuilder(config_manager)

# 系统提示词会自动包含 SKILL.md 内容
prompt = builder.build_system_prompt('core_brain')
```

## 八、参考文档

- [OpenClaw SKILL.md 格式](../openclaw/skills/github/SKILL.md)
- [OpenClaw Skills 加载器](../openclaw/src/agents/skills/workspace.ts)
- [OpenClaw Frontmatter 解析](../openclaw/src/agents/skills/frontmatter.ts)
