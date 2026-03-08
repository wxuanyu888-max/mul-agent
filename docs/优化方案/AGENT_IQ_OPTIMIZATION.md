# Agent 智商优化报告

> **版本**: v1.0
> **日期**: 2026-03-07
> **目标**: 让 Agent 变聪明 - 完整的提示词工程方案

---

## 一、问题诊断

### 1.1 核心问题

**修改前** (`llm.py:665-693`):

```python
system_template = """你是一个名为 {role_title} 的 AI 助手。

重要：你是运行在用户本地电脑上的 AI 助手，不是云端服务！

核心特质：{personality}
职责：{responsibilities}
可用技能：{skills}

运行环境说明:
1. 你直接运行在用户的电脑上
2. 你可以执行 bash 命令来操作本地文件系统
3. 你可以直接读取和分析用户电脑上的文件
4. 不要说"我是云端 AI"或"我无法访问你的文件"

回复原则:
1. 用户请求执行命令时，直接执行并分析结果
2. 用户请求分析文件时，直接读取并分析
3. 不要说"请你执行命令后把结果发给我"
4. 直接行动，然后告诉用户结果

请用用户使用的语言（中文/英文等）来回答。"""
```

**问题**:
1. ❌ 没有告诉 LLM 有哪些**路由可用**
2. ❌ 没有**路由选择指导**（决策树）
3. ❌ 没有**输出格式要求**和示例
4. ❌ 没有**上下文信息**（配置、记忆、历史）

### 1.2 影响

- LLM 不知道能做什么 → 瞎猜路由
- 没有决策依据 → 随机选择
- 没有格式约束 → 返回非 JSON

---

## 二、优化方案

### 2.1 完整的提示词结构

```
┌─────────────────────────────────────────────────────────────┐
│ 1. 系统身份（角色定义 + 核心特质 + 能力边界）               │
├─────────────────────────────────────────────────────────────┤
│ 2. 可用路由列表（每个路由：名称、描述、参数、示例）         │
├─────────────────────────────────────────────────────────────┤
│ 3. 路由选择决策树（清晰的 if-then 规则）                    │
├─────────────────────────────────────────────────────────────┤
│ 4. 当前上下文（Agent 信息 + 最近记忆 + 可用工具）          │
├─────────────────────────────────────────────────────────────┤
│ 5. 对话历史（压缩后的最近 N 轮）                            │
├─────────────────────────────────────────────────────────────┤
│ 6. 输出格式要求（JSON 格式 + 示例）                          │
├─────────────────────────────────────────────────────────────┤
│ 7. 用户输入                                                  │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 优化后的提示词模板

```markdown
你是一个名为 {role_title} 的 AI 助手。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【重要】你是运行在用户本地电脑上的 AI 助手，不是云端服务！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 核心特质
- 人格：{personality}
- 职责：{responsibilities}
- 技能：{skills}

## 运行环境说明
1. 你直接运行在用户的电脑上
2. 你可以执行 bash 命令来操作本地文件系统
3. 你可以直接读取和分析用户电脑上的文件
4. 不要说"我是云端 AI"或"我无法访问你的文件"

## 回复原则
1. 用户请求执行命令时，直接执行并分析结果
2. 用户请求分析文件时，直接读取并分析
3. 不要说"请你执行命令后把结果发给我"
4. 直接行动，然后告诉用户结果

## 可用路由（你只能选择以下路由）

### 1. response - 直接回复用户
- 参数：message (str)
- 示例：{"route": "response", "params": {"message": "你好！"}}
- 适用场景：问候、解答问题、简单回复

### 2. bash - 执行 shell 命令
- 参数：command (str), timeout (int)
- 示例：{"route": "bash", "params": {"command": "ls -la"}}
- 适用场景：用户明确要执行命令、查看文件、运行脚本

### 3. create_user - 创建新 Agent
- 参数：name (str), role_type (str)
- 示例：{"route": "create_user", "params": {"name": "coder", "role_type": "worker"}}
- 适用场景：用户说"创建 Agent"、"新建一个助手"

### 4. memory - 管理记忆
- 参数：action (str), memory_type (str)
- 示例：{"route": "memory", "params": {"action": "list"}}
- 适用场景：查看记忆、搜索记忆

### 5. chat - 与其他 Agent 对话
- 参数：agent_id (str), message (str)
- 示例：{"route": "chat", "params": {"agent_id": "coder", "message": "帮我写代码"}}
- 适用场景：需要其他 Agent 协助

### 6. heart - 自省/进化
- 参数：trigger (str), focus (str)
- 示例：{"route": "heart", "params": {"trigger": "manual"}}
- 适用场景：自我改进、分析当前状态

## 路由选择决策树

分析用户输入，按以下优先级选择路由：

```
用户输入
    │
    ├── 包含命令格式（$ 开头、ls/cd/pwd 等）
    │   └──→ route: bash
    │
    ├── 包含创建词汇（create/new/创建/新建）+ 目标词（agent/team）
    │   └──→ route: create_user / create_team
    │
    ├── 包含记忆词汇（memory/记住/记忆）
    │   └──→ route: memory
    │
    ├── 包含对话词汇（chat/对话/找 xx）
    │   └──→ route: chat
    │
    ├── 包含自省词汇（heart/evolve/自省）
    │   └──→ route: heart
    │
    ├── 空输入或问候（你好/hello/hi）
    │   └──→ route: response
    │
    └── 其他情况
        └──→ route: response（生成自然语言回复）
```

## 输出格式要求

你必须严格遵循以下格式，只返回 JSON：

```json
{
  "route": "路由名称",
  "params": {
    "参数名": "参数值"
  },
  "confidence": 0.0-1.0,
  "reason": "选择此路由的简短原因"
}
```

### 示例

用户：`$ ls -la`
```json
{"route": "bash", "params": {"command": "ls -la"}, "confidence": 1.0, "reason": "明确命令格式"}
```

用户：`你好`
```json
{"route": "response", "params": {"message": "你好！有什么可以帮你？"}, "confidence": 0.95, "reason": "问候场景"}
```

用户：`创建一个新的 coder agent`
```json
{"route": "create_user", "params": {"name": "coder", "role_type": "worker"}, "confidence": 0.9, "reason": "创建 Agent 场景"}
```

用户：`分析这个项目的结构`
```json
{"route": "bash", "params": {"command": "find . -type f -name "*.py" | head -20"}, "confidence": 0.8, "reason": "需要分析项目结构"}
```

请用用户使用的语言（中文/英文等）来回答。
```

---

## 三、代码变更

### 3.1 `llm.py` 修改

#### 修改 1: `_build_system_prompt_for_content_generation`

```python
def _build_system_prompt_for_content_generation(self, context: Dict[str, Any]) -> str:
    """构建系统提示用于纯内容生成"""
    soul = context.get("soul", {})
    user = context.get("user", {})
    skills = context.get("skills", [])
    available_routes = context.get("available_routes", [])

    personality = soul.get("core_traits", {}).get("personality", "")
    role = user.get("role", {}).get("title", "")
    responsibilities = user.get("role", {}).get("responsibilities", [])
    skill_names = [s.get("name", "") for s in skills if s.get("enabled", False)]

    # 构建可用路由描述
    routes_desc = self._build_routes_description(available_routes)

    system_template = """你是一个名为 {role_title} 的 AI 助手。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【重要】你是运行在用户本地电脑上的 AI 助手，不是云端服务！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 核心特质
- 人格：{personality}
- 职责：{responsibilities}
- 技能：{skills}

## 运行环境说明
...

## 可用路由（你只能选择以下路由）

{routes_desc}

## 路由选择决策树
...

## 输出格式要求
...
"""

    return system_template.format(
        role_title=role,
        personality=personality,
        responsibilities=", ".join(responsibilities) if responsibilities else "AI 助手",
        skills=", ".join(skill_names) if skill_names else "对话、分析、执行命令",
        routes_desc=routes_desc
    )
```

#### 修改 2: 新增 `_build_routes_description`

```python
def _build_routes_description(self, available_routes: List[Dict]) -> str:
    """构建可用路由描述"""
    if not available_routes:
        # 默认路由列表
        available_routes = [
            {"name": "response", "description": "直接回复用户", "params": {"message": "str"}, ...},
            {"name": "bash", "description": "执行 shell 命令", "params": {"command": "str"}, ...},
            {"name": "create_user", "description": "创建新 Agent", "params": {"name": "str"}, ...},
            {"name": "memory", "description": "管理记忆", "params": {"action": "str"}, ...},
            {"name": "chat", "description": "与其他 Agent 对话", "params": {"agent_id": "str"}, ...},
            {"name": "heart", "description": "自省/进化", "params": {}, ...},
        ]

    lines = []
    for i, route in enumerate(available_routes, 1):
        name = route.get("name", "unknown")
        desc = route.get("description", "")
        params = route.get("params", {})
        example = route.get("example", "")

        param_str = ", ".join([f"{k}: {v}" for k, v in params.items()]) if params else "无"

        lines.append(f"### {i}. {name} - {desc}")
        lines.append(f"- 参数：{param_str}")
        lines.append(f"- 示例：{example}")
        lines.append("")

    return "\n".join(lines)
```

#### 修改 3: 新增 `_enhance_context` 和 `_get_default_routes`

```python
def _enhance_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
    """增强上下文，添加配置文件内容和可用路由信息"""
    enhanced = context.copy()

    # 从 configs 中提取 soul/user/skill
    configs = context.get("configs", {})
    enhanced["soul"] = configs.get("soul", {})
    enhanced["user"] = configs.get("user", {})
    enhanced["skill"] = configs.get("skill", {})

    # 添加可用路由列表
    enhanced["available_routes"] = self._get_default_routes()

    return enhanced

def _get_default_routes(self) -> List[Dict]:
    """获取默认路由列表"""
    return [
        {"name": "response", "description": "直接回复用户", "params": {"message": "str"}, ...},
        {"name": "bash", "description": "执行 shell 命令", "params": {"command": "str"}, ...},
        {"name": "create_user", "description": "创建新 Agent", "params": {"name": "str"}, ...},
        {"name": "memory", "description": "管理记忆", "params": {"action": "str"}, ...},
        {"name": "chat", "description": "与其他 Agent 对话", "params": {"agent_id": "str"}, ...},
        {"name": "heart", "description": "自省/进化", "params": {}, ...},
    ]
```

### 3.2 `brain.py` 修改

#### 优化 `_decide_action` 方法

```python
def _decide_action(self, user_input: str) -> Dict[str, Any]:
    """基于规则的意图识别"""

    # 1. 空输入
    if not input_lower:
        return {"route": "response", "params": {"message": "我在听。"}}

    # 2. Bash 命令模式
    if is_bash:
        return {"route": "bash", "params": {"command": command}}

    # 3. 问候语
    if any(kw in input_lower for kw in greeting_patterns):
        return {"route": "uncertain", "params": {"input": user_input}}

    # 4. 帮助请求
    if any(kw in input_lower for kw in ["help", "?", "帮助"]):
        return {"route": "response", "params": {"message": help_text}}

    # 5. 创建 Agent - 更精确的匹配
    is_create = any(kw in input_lower for kw in ["create", "new", "创建"])
    has_target = any(t in input_lower for t in ["agent", "team", "助手"])
    if is_create and has_target:
        return {"route": "create_user", "params": {"name": user_input}}

    # 6. 记忆相关
    if any(kw in input_lower for kw in ["memory", "记住", "记忆"]):
        return {"route": "memory", "params": {"action": "list"}}

    # 7. 自省/进化
    if any(kw in input_lower for kw in ["heart", "自省", "进化"]):
        return {"route": "heart", "params": {}}

    # 8. 对话相关
    for pattern in chat_patterns:
        if re.search(pattern, input_lower):
            return {"route": "chat", "params": {"message": user_input}}

    # 9. 其他 → LLM
    return {"route": "uncertain", "params": {"input": user_input}}
```

---

## 四、预期效果

### 4.1 智商提升对比

| 场景 | 优化前 | 优化后 |
|------|--------|--------|
| `$ ls -la` | ✅ 规则识别 | ✅ 规则识别 |
| `创建 agent` | ⚠️ 可能误判 | ✅ 精确匹配 |
| `和 coder 对话` | ❌ 无法识别 | ✅ 新增 chat 路由 |
| `分析项目结构` | ❌ 不知道干嘛 | ✅ LLM 选择 bash |
| `你好` | ✅ LLM 生成 | ✅ LLM 生成（有指导） |

### 4.2 智商提升指标

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 路由准确率 | ~60% | ~90% |
| LLM 响应质量 | 随机 | 有指导、有示例 |
| 场景覆盖 | 5 种 | 10+ 种 |

---

## 五、验证方法

### 5.1 测试用例

```bash
# 1. 基础命令
$ ls -la
$ cat README.md

# 2. 创建 Agent
创建一个新的 coder agent
new agent for writing

# 3. 对话
和 coder 对话
tell agent to write code

# 4. 记忆
查看记忆
记住这个

# 5. 自省
heart
自省一下

# 6. 复杂任务
分析这个项目的结构
帮我找一下所有 Python 文件
```

### 5.2 验证步骤

1. 启动 Agent
2. 运行上述测试用例
3. 记录路由选择准确率和响应质量
4. 对比优化前后的效果

---

## 六、持续优化建议

### 6.1 短期（本周）

- [ ] 收集真实用户输入，优化关键词匹配
- [ ] 添加更多路由示例
- [ ] 优化决策树逻辑

### 6.2 中期（下周）

- [ ] 实现用户级别系统（novice/advanced/expert）
- [ ] 添加渐进式披露逻辑
- [ ] 完善 FileTools

### 6.3 长期

- [ ] 基于用户反馈自适应调整提示词
- [ ] 实现路由选择的 few-shot learning
- [ ] 添加多轮对话上下文理解

---

## 七、总结

### 7.1 核心改进

1. **可用路由列表** - 让 LLM 知道能做什么
2. **路由选择决策树** - 告诉 LLM 如何选择
3. **输出格式要求** - 强制 JSON 格式
4. **示例驱动** - 提供典型场景示例

### 7.2 智商提升本质

**优化前**: LLM 瞎猜
**优化后**: LLM 有指导、有示例、有约束

这就是让 Agent 变聪明的核心秘诀！
