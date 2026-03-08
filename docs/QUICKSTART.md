# 快速开始指南

> 如何创建和配置新的 Agent

---

## 一、创建新 Agent

### 方法 1: 使用模板复制

```bash
# 1. 创建 Agent 目录
mkdir -p wang/agent-team/{agent_name}

# 2. 复制模板文件
cp wang/agent-team/.templates/soul.md.template wang/agent-team/{agent_name}/soul.md
cp wang/agent-team/.templates/user.md.template wang/agent-team/{agent_name}/user.md

# 3. 编辑配置文件
# 替换 ${variable} 占位符为实际值
```

### 方法 2: 通过 core_brain 创建

```
/新建 Agent coder
```

---

## 二、配置文件说明

### soul.md 快速配置

```yaml
---
version: "1.0"
name: coder
description: 编码助手 - Python/JavaScript 专家
role: 高级软件工程师
core_traits:
  personality: 严谨、逻辑清晰、追求最佳实践
  values:
  - 代码质量
  - 可维护性
  - 性能优化
  goals:
  - 编写高质量代码
  - 遵循最佳实践
  - 持续学习新技术
---

# Coder Soul
这是编码助手的核心特质定义...
```

### user.md 快速配置

```yaml
---
version: "1.0"
agent_id: coder
role:
  type: worker
  title: 高级软件工程师
  responsibilities:
  - 编写代码
  - 代码审查
  - 问题调试
capabilities:
  max_team_size: 1
  can_create_agent: false
  can_modify_config: false
  can_execute_tools: true
tools:
  enabled:
  - bash
  - grep
  bash:
    enabled: true
    timeout: 30
    allowed_commands:
    - ls
    - pwd
    - cat
    - grep
    - find
    forbidden_commands:
    - rm -rf
    - sudo
permissions:
  file_read:
  - "*"
  file_write:
  - src/**
  - tests/**
  network_access: false
---

# 一、工具使用规范
...
```

---

## 三、添加响应风格

在 `user.md` 中添加响应风格：

```markdown
### 3.2 问候响应 (coder_greeting)
```
你好！我是你的编码助手。擅长 Python、JavaScript 开发。有什么代码问题吗？
```

### 3.3 帮助响应 (coder_help)
```
我可以帮你：
- 编写/修改代码
- 调试 bug
- 代码审查
- 架构设计
```
```

---

## 四、测试 Agent

### 4.1 验证配置

```python
from mul_agent.brain.config_manager import ConfigManager
from pathlib import Path

config_manager = ConfigManager(
    config_dir=Path("storage"),
    wang_dir=Path("wang")
)

# 验证配置
result = config_manager.validate_config("coder")
print(result)
# {'agent_id': 'coder', 'valid': True, 'missing': [], 'errors': []}
```

### 4.2 加载配置

```python
# 加载 soul
soul = config_manager.load("coder", "soul")
print(soul['role'])  # 高级软件工程师

# 加载 user 文本内容
user_text = config_manager.load_text_content("coder", "user")
print(user_text[:100])  # 工具使用规范...
```

### 4.3 启动 Agent

```python
from mul_agent.brain.brain import Brain

brain = Brain(
    agent_id="coder",
    config_manager=config_manager
)

# 处理用户输入
result = brain.think("帮我写一个 hello world 函数")
print(result)
```

---

## 五、常见问题

### Q: 创建 Agent 后无法识别？

**A**: 检查以下几点：
1. 目录是否在 `wang/agent-team/` 下
2. `soul.md` 和 `user.md` 是否存在
3. YAML front matter 格式是否正确

### Q: 如何自定义响应风格？

**A**: 在 `user.md` 中添加响应 prompt 代码块，使用 `_load_response_prompt` 方法加载。

### Q: Agent 可以调用哪些工具？

**A**: 在 `user.md` 的 `tools.enabled` 中定义。可用工具：
- `bash` - 执行 shell 命令
- `grep` - 文件搜索
- `mcp` - MCP 工具（需要配置提供者）

---

## 六、下一步

- 查看 [配置规范](README.md) 了解更多细节
- 查看 [agent-team/core_brain/user.md](agent-team/core_brain/user.md) 参考完整示例
- 添加自定义技能和 Hook
