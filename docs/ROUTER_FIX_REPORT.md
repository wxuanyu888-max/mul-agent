# 路由修复报告

## 问题描述

在自主模式测试中，发现所有工具调用失败：

```
| 步骤 | 操作类型 | 状态 | 错误信息 |
|------|----------|------|----------|
| bash | 执行 shell 命令 | ❌ 失败 | 'bool' object has no attribute 'get' |
| file_edit | 文件读取 | ❌ 失败 | Missing: path |
| chat | Agent 对话 | ⚠️ 部分成功 | 响应被截断 |
```

---

## 根本原因分析

### 问题 1: BashHandler 配置加载错误

**错误代码** (`mul_agent/brain/handlers/bash.py:33-34`):
```python
allowed = agent_config.get("tools", {}).get("bash", {}).get("allowed_commands", ["*"])
forbidden = agent_config.get("tools", {}).get("bash", {}).get("forbidden_commands", [])
```

**问题分析**:
- `agent_config["tools"]["bash"]` 的值是 `True` (布尔值)
- 在布尔值上调用 `.get()` 方法导致错误：`'bool' object has no attribute 'get'`

**配置示例** (`wang/agent-team/core_brain/user.md`):
```yaml
tools:
  bash: true    # ← 这是布尔值，不是字典
  memory: true
  chat: true
```

**修复方案**:
```python
# 修复：tools.bash 可能是布尔值或字典
bash_config = agent_config.get("tools", {}).get("bash")
if isinstance(bash_config, dict):
    allowed = bash_config.get("allowed_commands", ["*"])
    forbidden = bash_config.get("forbidden_commands", [])
else:
    # 如果是 True/布尔值，使用默认配置
    allowed = ["*"]
    forbidden = self.DANGEROUS_PATTERNS
```

---

### 问题 2: 配置格式不一致

**期望格式** (支持自定义配置):
```yaml
tools:
  bash:
    allowed_commands: ["ls", "cat", "find", "grep"]
    forbidden_commands: ["rm -rf", "sudo"]
```

**实际格式** (简化开关):
```yaml
tools:
  bash: true    # 仅启用，无自定义配置
```

**解决方案**:
- 代码需要同时支持两种格式
- 布尔值 → 使用默认配置
- 字典 → 使用自定义配置

---

## 修复验证

### Bash 路由测试
```bash
python -c "
from mul_agent.brain.router import Router
from mul_agent.brain.config_manager import ConfigManager
from pathlib import Path

wang_dir = Path('/Users/agent/PycharmProjects/mul-agent/wang')
config_manager = ConfigManager(config_dir=wang_dir, wang_dir=wang_dir)
router = Router(config_manager, 'core_brain')

result = router.dispatch('bash', {'command': 'ls -la'})
print(result)
"
```

**结果**: ✅ 成功返回文件列表

---

### File Edit 路由测试
```python
result = router.dispatch('file_edit', {
    'action': 'read',
    'path': '/Users/agent/PycharmProjects/mul-agent/README.md',
    'start': 1,
    'end': 10
})
```

**结果**: ✅ 成功读取文件内容

---

### Chat 路由测试
```python
result = router.dispatch('chat', {
    'agent_id': 'alice',
    'message': '你好，请介绍一下你自己'
})
```

**结果**: ✅ 成功返回对话响应

---

## 完整集成测试

**用户输入**:
```
我的电脑里面有一个 stock-crawler 项目，请你帮我看看你能为这个项目做什么
```

**Agent 执行流程**:
1. ✅ 复杂任务检测 → 识别为复杂任务
2. ✅ 意图理解 → 分析用户需求
3. ✅ 任务分解 → 生成执行步骤
4. ✅ Bash 执行 → 成功扫描项目结构
5. ✅ 报告生成 → 输出完整的 Markdown 报告

**输出摘要**:
```markdown
# Stock-Crawler 项目探索报告

## 1. 任务目标
探索用户本地电脑上的 `stock-crawler` 项目...

## 2. 执行步骤
| 步骤 | 操作 | 描述 |
|------|------|------|
| 1 | find 命令扫描 | 扫描项目主要文件结构... |

## 3. 项目结构概览
stock-crawler/
├── frontend/              # 前端部分
├── tests/                 # 测试目录
├── wang/                  # 核心配置目录
└── ...

## 4. 我能为这个项目做什么
| 能力 | 具体帮助 |
|------|----------|
| 代码审查 | 检查 Python/TypeScript 代码... |
| 代码生成 | 根据需求生成新的测试用例... |
...
```

---

## 修改文件清单

| 文件 | 修改内容 |
|------|----------|
| `mul_agent/brain/handlers/bash.py` | 修复配置加载，支持布尔值和字典两种格式 |

---

## 配置格式建议

### 简化用法 (当前支持)
```yaml
# wang/agent-team/core_brain/user.md
tools:
  bash: true
  file_edit: true
  chat: true
```

### 高级用法 (可选)
```yaml
tools:
  bash:
    allowed_commands: ["ls", "cat", "find", "grep", "pwd", "cd"]
    forbidden_commands: ["rm -rf /", "sudo", "dd"]
    timeout: 60

  file_edit:
    max_file_size: 100KB
    allowed_extensions: [".py", ".md", ".json", ".ts", ".tsx"]

  chat:
    max_history: 50
    timeout: 120
```

---

## 总结

### 问题根源
- 配置格式期望不一致：代码期望字典，实际配置是布尔值

### 修复方案
- 增加类型检查，兼容两种格式
- 布尔值 → 使用默认配置
- 字典 → 使用自定义配置

### 验证结果
- ✅ Bash 路由正常工作
- ✅ File Edit 路由正常工作
- ✅ Chat 路由正常工作
- ✅ 自主模式完整执行成功

### 后续建议
1. 更新配置模板，说明两种格式的区别
2. 添加配置验证，启动时检查格式
3. 提供更详细的配置示例文档
