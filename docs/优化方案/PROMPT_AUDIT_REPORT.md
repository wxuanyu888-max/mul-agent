# 提示词引用检查报告

> **版本**: v3.1
> **日期**: 2026-03-07
> **目标**: 确保所有提示词都从 `wang/` 目录引用，无硬编码

---

## 一、检查范围

检查了 `mul_agent/` 目录下所有 Python 文件中的提示词引用。

---

## 一、v3.1 修复说明 (2026-03-07)

**问题**: 提示词加载失败，所有提示词都返回"未找到"

**原因**: 正则表达式 `## {prompt_name}\s*\n` 无法匹配 `## default_assistant - 默认助手提示词` 格式（提示词名称后面有描述文字）

**修复**:
1. 更新 `config_manager.py` 的 `load_prompt` 方法，使用新正则表达式：
   ```python
   # 旧：## {prompt_name}\s*\n
   # 新：## {prompt_name}(?:\s*-.*?)*\s*\n
   # 说明：支持提示词名称后面的描述文字，如 "## default_assistant - 默认助手提示词"
   ```
2. 简化 `brain.py` 和 `handlers/chat.py` 的 `_load_response_prompt` 方法，直接委托给 `config_manager.load_prompt`

**验证结果**:
```
✓ default_assistant
✓ empty_input_style
✓ help_menu_style
✓ context_prompt
✓ agent_chat
✓ coder_greeting
✓ writer_greeting
✓ greeting_style
```

---

## 二、修复的文件

### 2.1 `mul_agent/brain/llm.py`

**修复内容**:

| 方法 | 修复前 | 修复后 |
|------|--------|--------|
| `_build_system_prompt_for_content_generation` | 硬编码模板 | 从 `wang/agent-team/.templates/prompt.md.template` 读取 |
| `_build_system_prompt` | 硬编码模板 | 从 `wang/agent-team/.templates/prompt.md.template` 读取 |
| `_load_prompt_template` | 无 | 新增方法，支持优先级加载 |

**加载优先级**:
1. `wang/agent-team/{agent_id}/prompt.md` (Agent 自定义)
2. `wang/agent-team/.templates/prompt.md.template` (标准模板)
3. 代码内硬编码备份

---

### 2.2 `mul_agent/brain/brain.py`

**修复内容**:

| 方法 | 修复前 | 修复后 |
|------|--------|--------|
| `_load_response_prompt` | 从 `user.md` 读取 | 从 `prompt.md.template` 读取 |

**修复前代码**:
```python
def _load_response_prompt(self, prompt_name: str, default: str) -> str:
    user_text = self.config_manager.load_text_content(self.agent_id, "user")
    if user_text:
        pattern = rf'### \d+\.\d+\.\d+ {prompt_name}\s*\n```\n(.*?)```'
        match = re.search(pattern, user_text, re.DOTALL)
        if match:
            return match.group(1).strip()
    loaded = self.config_manager.load_prompt(self.agent_id, prompt_name)
    return loaded if loaded else default
```

**修复后代码**:
```python
def _load_response_prompt(self, prompt_name: str, default: str) -> str:
    """从配置加载响应 prompt

    加载优先级：
    1. 先从 wang/agent-team/{agent_id}/prompt.md 加载（Agent 自定义）
    2. 再从 wang/agent-team/.templates/prompt.md.template 加载（标准模板）
    3. 最后返回默认值
    """
    # 1. 尝试从 Agent 自定义的 prompt.md 加载
    loaded = self.config_manager.load_prompt(self.agent_id, prompt_name)
    if loaded:
        return loaded

    # 2. 从标准模板加载
    try:
        template_path = self.config_manager.agent_team_dir / ".templates" / "prompt.md.template"
        if template_path.exists():
            with open(template_path, "r", encoding="utf-8") as f:
                content = f.read()
            import re
            pattern = rf'## {prompt_name}\s*\n(?:```\n)?(.*?)(?:```|\n---|\n##|$)'
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(1).strip()
    except Exception:
        pass

    # 3. 返回默认值
    return default
```

---

### 2.3 `mul_agent/brain/handlers/chat.py`

**修复内容**:

| 方法 | 修复前 | 修复后 |
|------|--------|--------|
| `_load_response_prompt` | 从 `user.md` 读取，正则表达式无法匹配带描述的头 | 委托给 `config_manager.load_prompt` |

**修复说明**: 简化方法实现，直接委托给 `config_manager.load_prompt`，不再重复实现正则表达式解析逻辑。

---

### 2.4 `mul_agent/brain/brain.py`

**修复内容**:

| 方法 | 修复前 | 修复后 |
|------|--------|--------|
| `_load_response_prompt` | 从 `user.md` 读取，正则表达式无法匹配带描述的头 | 委托给 `config_manager.load_prompt` |

**修复说明**: 简化方法实现，直接委托给 `config_manager.load_prompt`，不再重复实现正则表达式解析逻辑。

---

### 2.5 `mul_agent/brain/config_manager.py`

**修复内容**:

| 方法 | 修复前 | 修复后 |
|------|--------|--------|
| `load_prompt` | 正则表达式 `## {prompt_name}\s*\n` 无法匹配带描述的标题 | `## {prompt_name}(?:\s*-.*?)*\s*\n` 支持描述文字 |

**修复详情**:
```python
# 修复前
pattern = rf'## {prompt_name}\s*\n(?:```\n)?(.*?)(?:```|\n---|\n##|$)'

# 修复后
pattern = rf'## {prompt_name}(?:\s*-.*?)*\s*\n(.*?)(?:\n---|\n##|\Z)'
# 说明：(?:\s*-.*?)* 匹配零个或多个" - 描述文字"
```

---

### 2.6 `mul_agent/brain/context_builder.py`

**状态**: ✅ 无需修改

`build_system_prompt` 方法已经使用 `config_manager.load_prompt()` 从配置文件加载。

---

### 2.7 `mul_agent/brain/compressor.py`

**状态**: ✅ 无需修改

压缩提示词是动态生成的（非配置文件），用于上下文压缩，不属于用户可配置的提示词。

---

### 2.8 `mul_agent/brain/handlers.py`

**状态**: ✅ 无需修改

第 282 行和 457 行的提示词是动态生成的，用于特定场景（自我进化分析、Agent 对话），不属于用户可配置的提示词。

---

### 2.9 `mul_agent/repositories/agent_repository.py`

**状态**: ✅ 无需修改

仅使用 `config_manager.load_prompt()`，已经正确从配置文件加载。

---

## 三、提示词文件结构

```
wang/agent-team/.templates/
└── prompt.md.template      # 标准提示词模板（所有提示词的来源）
```

### 包含的提示词模块

| 模块名 | 用途 | 使用位置 |
|--------|------|----------|
| `default_assistant` | 默认助手提示词 | `llm._build_system_prompt_for_content_generation` |
| `empty_input_style` | 空输入响应 | `brain._load_response_prompt` |
| `help_menu_style` | 帮助菜单 | `brain._load_response_prompt` |
| `context_prompt` | 上下文提示词 | `context_builder.build_system_prompt` |
| `agent_chat` | Agent 对话提示词 | `handlers/chat._generate_response` |
| `coder_greeting` | 编码助手问候 | `handlers/chat._generate_response` |
| `writer_greeting` | 写作助手问候 | `handlers/chat._generate_response` |
| `greeting_style` | 通用问候 | `handlers/chat._generate_response` |

---

## 四、验证方法

### 4.1 检查是否有硬编码提示词

```bash
# 搜索所有 Python 文件中的提示词相关代码
grep -r "system_prompt\|prompt_template\|提示词" mul_agent/**/*.py
```

### 4.2 验证加载优先级

1. 修改 `wang/agent-team/.templates/prompt.md.template` 中的 `empty_input_style`
2. 重启 Agent
3. 发送空消息，检查响应是否符合修改

---

## 五、修改后的提示词加载流程

```
用户请求
    │
    ▼
┌─────────────────────────────────┐
│ brain.py / handlers / llm.py    │
│ 需要提示词                       │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│ config_manager.load_prompt()    │
└───────────────┬─────────────────┘
                │
                ▼
┌─────────────────────────────────┐
│ 1. wang/agent-team/{agent_id}/  │
│    prompt.md                    │
│    (Agent 自定义)                │
└───────────────┬─────────────────┘
                │ 未找到
                ▼
┌─────────────────────────────────┐
│ 2. wang/agent-team/.templates/  │
│    prompt.md.template           │
│    (标准模板) ← 你修改这里！     │
└───────────────┬─────────────────┘
                │ 未找到
                ▼
┌─────────────────────────────────┐
│ 3. 代码内硬编码备份             │
│    (降级，不应使用)             │
└─────────────────────────────────┘
```

---

## 六、如何修改提示词

### 直接编辑 `wang/agent-team/.templates/prompt.md.template`

例如，修改 `empty_input_style`:

**修改前**:
```markdown
## empty_input_style

我在听。请告诉我你需要什么帮助？
```

**修改后**:
```markdown
## empty_input_style

👋 我在听！有什么可以帮你的吗？
```

---

## 七、总结

### 修复前
- ❌ `llm.py` 有 2 处硬编码提示词模板
- ❌ `brain.py` 从 `user.md` 读取提示词（格式不统一）
- ❌ `handlers/chat.py` 从 `user.md` 读取提示词（格式不统一）

### 修复后
- ✅ 所有提示词都从 `wang/agent-team/.templates/prompt.md.template` 读取
- ✅ 统一的加载优先级：Agent 自定义 > 标准模板 > 代码备份
- ✅ 你可以直接编辑 `prompt.md.template` 控制所有提示词

---

## 八、后续建议

1. **删除硬编码备份**: 当确认所有提示词都从配置文件加载后，可以删除代码中的 `_get_default_prompt_template()` 方法。

2. **添加提示词版本管理**: 在 `prompt.md.template` 开头添加版本号，便于追踪变更。

3. **提示词测试**: 修改提示词后，运行完整的测试用例，确保所有场景正常工作。

4. **文档更新**: 在 `README.md` 中添加提示词修改指南，方便其他开发者使用。
