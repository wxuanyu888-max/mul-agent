# Agent 能力架构与提示词优化报告

> **版本**: v1.0
> **日期**: 2026-03-07
> **目标**: 解决 Agent 路由查找能力优化与上下文膨胀问题

---

## 目录

1. [基础能力架构](#一基础能力架构)
2. [Agent 可用能力清单](#二 agent 可用能力清单)
3. [提示词设计：路由查找优化](#三提示词设计路由查找优化)
4. [上下文压缩策略](#四上下文压缩策略)
5. [配置文件最佳实践](#五配置文件最佳实践)
6. [实施建议](#六实施建议)

---

## 一、基础能力架构

### 1.1 系统架构总览

```
┌─────────────────────────────────────────────────────────────────┐
│                        用户输入                                  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  Brain.think() - 核心决策循环                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ 1. 意图识别 (_decide_action) → 路由选择                   │   │
│  │ 2. 上下文构建 (ContextBuilder) → 上下文聚合               │   │
│  │ 3. 路由分发 (Router.dispatch) → Handler 执行              │   │
│  │ 4. 记忆写入 (Memory.write) → 经验沉淀                     │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         ▼                 ▼                 ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   Tool Layer    │ │  Memory Layer   │ │  Network Layer  │
│ - BashExecutor  │ │ - ShortTerm     │ │ - AgentNetwork  │
│ - GrepTool      │ │ - LongTerm      │ │ - MessageQueue  │
│ - FileTools*    │ │ - Handover      │ │ - TaskDelegate  │
│ - WebSearch*    │ │                 │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

### 1.2 核心模块职责

| 模块 | 文件位置 | 核心职责 |
|------|----------|----------|
| **Brain** | `mul_agent/brain/brain.py` | 意图识别、路由决策、上下文协调 |
| **Router** | `mul_agent/brain/router.py` | 路由分发到 Handler |
| **Handlers** | `mul_agent/brain/handlers/` | 具体业务逻辑实现 |
| **ContextBuilder** | `mul_agent/brain/context_builder.py` | 聚合配置文件 + 记忆 + 历史 |
| **ContextCompressor** | `mul_agent/brain/compressor.py` | 上下文压缩与摘要生成 |
| **Memory** | `mul_agent/memory/memory.py` | 短/长/交接记忆存储 |
| **ToolManager** | `mul_agent/tools/mcp_tools.py` | MCP 工具注册与执行 |

---

## 二、Agent 可用能力清单

### 2.1 核心能力（已实现）

| 能力类别 | 具体能力 | 实现位置 | 状态 |
|---------|---------|----------|------|
| **基础交互** | 直接响应 | `ResponseHandler` | ✅ |
| **命令执行** | Bash 命令 | `BashExecutor` | ✅ |
| **文件搜索** | Grep 文本搜索 | `GrepTool` | ✅ |
| **记忆管理** | 读/写/搜索记忆 | `Memory` | ✅ |
| **Agent 创建** | 创建子 Agent | `CreateUserHandler` | ✅ |
| **团队创建** | 创建 Agent 团队 | `CreateTeamHandler` | ✅ |
| **Agent 对话** | 与其他 Agent 对话 | `ChatHandler` | ✅ |
| **自省进化** | 自我分析与改进 | `HeartHandler` | ✅ |
| **Token 统计** | Token 使用追踪 | `TokenUsageHandler` | ✅ |

### 2.2 网络协作能力（Agent 团队）

| 能力 | 实现位置 | 描述 |
|------|----------|------|
| **任务委派** | `NetworkDelegateHandler` | 将任务委派给专业 Agent |
| **消息发送** | `NetworkSendHandler` | 向指定 Agent 发送消息 |
| **广播消息** | `NetworkBroadcastHandler` | 向所有 Agent 广播 |
| **任务交接** | `NetworkHandoverHandler` | 跨 Agent 任务交接 |
| **查找专家** | `Brain.find_specialist()` | 根据任务类型查找专业 Agent |

### 2.3 待完善能力

| 能力 | 当前状态 | 优先级 | 说明 |
|------|---------|--------|------|
| **文件读写** | ⚠️ 部分实现 | P0 | `FileTools` 需完善 |
| **Web 搜索** | ⚠️ 占位实现 | P1 | 需集成 Tavily API |
| **Chrome 控制** | ⚠️ 占位实现 | P2 | 需集成 chrome-devtools MCP |

---

## 三、提示词设计：路由查找优化

### 3.1 当前问题分析

查看 `brain.py:326-417` 的 `_decide_action` 方法，当前路由决策逻辑：

**问题 1**: 规则路由是硬编码的，Agent 无法动态学习
```python
# 固定的 if-elif 链
if bash_pattern: return {"route": "bash"}
if greeting: return {"route": "uncertain"}
# ... 所有 Agent 看到相同的逻辑
```

**问题 2**: 没有将可用路由告知 LLM
```python
# 当 route="uncertain" 时，LLM 不知道有哪些路由可用
if action.get("route") == "uncertain":
    llm_result = self.llm.think(user_input, context)
    # LLM 可能返回不存在的路由
```

**问题 3**: 上下文构建没有包含路由能力说明
```python
# ContextBuilder.build_context() 只包含：
context = {
    "configs": configs,      # 配置文件
    "text_contents": text,   # 完整文本
    "recent_memory": memory, # 记忆
    "history": history       # 历史
}
# 缺少：可用路由列表、工具能力描述
```

### 3.2 优化方案：路由能力提示词

#### 3.2.1 添加路由能力描述到上下文

修改 `ContextBuilder.build_context()`:

```python
def build_context(self, agent_id: str, user_input: str, options=None):
    # ... 现有逻辑 ...

    # 4. 添加路由能力描述
    available_routes = self._get_available_routes(agent_id)

    context = {
        "agent_id": agent_id,
        "configs": configs,
        "text_contents": text_contents,
        "recent_memory": recent_memories,
        "team_info": team_info,
        "user_input": user_input,
        "available_routes": available_routes  # 新增：可用路由列表
    }

    return context

def _get_available_routes(self, agent_id: str) -> List[Dict]:
    """获取当前 Agent 可用的路由列表"""
    return [
        {
            "name": "response",
            "description": "直接回复用户",
            "parameters": {"message": "str"},
            "usage_example": "route: response, params: {message: '你好！'}"
        },
        {
            "name": "bash",
            "description": "执行 shell 命令",
            "parameters": {"command": "str", "timeout": "int"},
            "usage_example": "route: bash, params: {command: 'ls -la'}"
        },
        # ... 其他路由
    ]
```

#### 3.2.2 设计路由选择提示词模板

创建 `storage/agents/{agent_id}/routing_prompt.md`:

```markdown
# 路由选择指南

## 可用路由

你当前可以使用的路由有以下 {{ routes|length }} 个：

{% for route in routes %}
### {{ loop.index }}. {{ route.name }}
- **描述**: {{ route.description }}
- **参数**: {{ route.parameters|tojson }}
- **示例**: `{{ route.usage_example }}`
{% endfor %}

## 路由选择决策树

```
用户输入分析：
├── 包含命令格式（$ 开头、ls/cd 等） → route: bash
├── 包含创建词汇（create/new/创建） → route: create_user
├── 包含记忆词汇（memory/记住） → route: memory
├── 包含对话词汇（chat/对话） → route: chat
├── 包含自省词汇（heart/evolve） → route: heart
├── 空输入或问候 → route: response
└── 其他情况 → route: response（让 LLM 生成内容）
```

## 输出格式要求

请以 JSON 格式返回路由选择：

```json
{
  "route": "路由名称",
  "params": {
    "参数名": "参数值"
  },
  "confidence": 0.0-1.0,
  "reason": "选择此路由的原因"
}
```

## 示例

用户输入：`$ ls -la`
```json
{
  "route": "bash",
  "params": {"command": "ls -la"},
  "confidence": 1.0,
  "reason": "输入以 $ 开头，是明确的 bash 命令格式"
}
```

用户输入：`创建一个新的 coder agent`
```json
{
  "route": "create_user",
  "params": {"name": "coder", "role_type": "worker"},
  "confidence": 0.95,
  "reason": "包含关键词'创建'和'agent'，符合创建 Agent 场景"
}
```
```

### 3.3 优化方案：LLM 路由选择器

在 `brain.py` 中添加 LLM 辅助路由选择：

```python
def _decide_action_with_llm(self, user_input: str, context: dict) -> Dict:
    """使用 LLM 辅助路由选择"""

    # 构建路由选择提示词
    routes_info = self._get_available_routes(self.agent_id)
    routes_json = json.dumps(routes_info, ensure_ascii=False, indent=2)

    prompt = f"""你是一个智能路由选择器。请分析用户输入，选择最合适的路由。

## 可用路由
{routes_json}

## 当前上下文
- Agent ID: {self.agent_id}
- 角色：{context.get('role', 'unknown')}
- 用户输入：{user_input}

## 路由选择决策树
1. 明确命令格式（$ / ls/cd/pwd 等）→ bash
2. 创建类词汇 → create_user
3. 团队协作词汇 → create_team/chat
4. 记忆相关词汇 → memory
5. 自省进化词汇 → heart
6. 其他 → response（让 LLM 生成内容）

请以 JSON 格式返回：
{{
  "route": "路由名称",
  "params": {{...}},
  "confidence": 0.0-1.0,
  "reason": "选择原因"
}}
"""

    # 调用 LLM
    response = self.llm.chat(prompt)

    # 解析 LLM 返回
    try:
        import re
        json_match = re.search(r'\{.*\}', response.get("content", ""), re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            return result
    except Exception:
        pass

    # 回退到规则路由
    return self._decide_action(user_input)
```

### 3.4 提示词设计原则

| 原则 | 说明 | 实施方法 |
|------|------|----------|
| **能力显式化** | 明确告知 Agent 有哪些能力可用 | 在上下文中添加 `available_routes` |
| **示例驱动** | 提供典型示例供参考 | 每个路由配 usage_example |
| **决策树可视化** | 用流程图展示决策逻辑 | Markdown 树状图 |
| **JSON 格式化** | 强制结构化输出 | 提供输出模板 |
| **置信度评分** | 让 LLM 自我评估准确性 | confidence 字段 |

---

## 四、上下文压缩策略

### 4.1 当前问题分析

查看 `compressor.py` 和 `context_builder.py`：

**问题 1**: 压缩阈值固定，不够灵活
```python
DEFAULT_MAX_TOKENS = 8000  # 固定值
# 但不同 Agent 的 context window 可能不同
```

**问题 2**: 压缩策略单一
```python
def compress(self, messages: List[Dict]) -> List[Dict]:
    # 只保留最近 N 条，其余压缩为摘要
    early_messages = messages[:-self.recent_count]
    recent_messages = messages[-self.recent_count:]
```

**问题 3**: 没有分层压缩
```python
# 所有早期消息一视同仁压缩
# 但有些关键决策点应该保留
```

### 4.2 优化方案：智能分层压缩

#### 4.2.1 动态阈值计算

```python
class ContextCompressor:
    def __init__(self, llm_client=None, max_tokens=8000):
        self.llm_client = llm_client
        self.max_tokens = max_tokens
        self.soft_limit = int(max_tokens * 0.8)   # 软限制（开始预警）
        self.hard_limit = int(max_tokens * 0.95)  # 硬限制（必须压缩）

    def should_compress(self, messages: List[Dict], context=None) -> bool:
        """动态判断是否需要压缩"""
        token_count = self.count_message_tokens(messages)

        # 超过硬限制：必须压缩
        if token_count > self.hard_limit:
            return True

        # 超过软限制：根据任务复杂度判断
        if token_count > self.soft_limit:
            if context:
                # 复杂任务需要更多上下文
                if context.get("complexity") == "high":
                    return False
                # 简单任务可以压缩
                if context.get("complexity") == "low":
                    return True
            return False

        return False
```

#### 4.2.2 分层压缩策略

```python
def compress_with_layers(self, messages: List[Dict]) -> List[Dict]:
    """分层压缩：保留关键节点"""

    # 分层定义
    CRITICAL_SIZE = 5      # 关键消息保留数量
    IMPORTANT_SIZE = 15    # 重要消息保留数量
    RECENT_SIZE = 30       # 最近消息保留数量

    if len(messages) <= RECENT_SIZE:
        return messages  # 不需要压缩

    # 1. 识别关键消息（用户明确指令、重要决策点）
    critical_messages = self._identify_critical_messages(messages)

    # 2. 分离各层消息
    critical = critical_messages[:CRITICAL_SIZE]
    important = messages[CRITICAL_SIZE:IMPORTANT_SIZE]
    recent = messages[-RECENT_SIZE:]

    # 3. 压缩早期消息为摘要
    early_messages = messages[:CRITICAL_SIZE]
    early_summary = self.create_llm_summary(early_messages)

    # 4. 构建压缩结果
    compressed = [
        {
            "role": "system",
            "content": f"【对话摘要】{early_summary}",
            "metadata": {"type": "summary", "original_count": len(early_messages)}
        }
    ]

    # 保留关键消息
    for msg in critical:
        if msg not in recent:  # 避免重复
            compressed.append(msg)

    # 保留最近消息
    compressed.extend(recent)

    return compressed

def _identify_critical_messages(self, messages: List[Dict]) -> List[Dict]:
    """识别关键消息"""
    critical = []

    for msg in messages:
        content = msg.get("content", "")

        # 用户明确指令（包含"请"、"必须"等）
        if msg.get("role") == "user":
            if any(kw in content for kw in ["请", "必须", "务必", "important", "must"]):
                critical.append(msg)
                continue

        # 助手的重要决策（包含路由执行结果）
        if msg.get("role") == "assistant":
            if isinstance(content, dict):
                if content.get("route") in ["create_user", "bash", "network_delegate"]:
                    critical.append(msg)
                    continue

    return critical
```

### 4.3 上下文构建优化

修改 `ContextBuilder.build_context()`:

```python
def build_context(self, agent_id: str, user_input: str, options=None):
    """构建上下文时应用分层策略"""

    options = options or {}

    # 1. 基础配置（必须）
    configs = self.config_manager.load_all(agent_id)

    # 2. 结构化数据（必须）- 不放入 prompt，只给 LLM 决策用
    structured_context = {
        "agent_id": agent_id,
        "role": configs.get("user", {}).get("role", {}),
        "capabilities": configs.get("user", {}).get("capabilities", {}),
        "available_routes": self._get_available_routes(agent_id),
        "available_tools": self._get_available_tools(agent_id)
    }

    # 3. 文本内容（可选）- 按需加载
    text_contents = {}
    if options.get("include_text_content", True):
        # 只加载摘要，不加载完整文本
        text_contents = self._load_text_summaries(agent_id)

    # 4. 记忆（可选）- 限制数量
    recent_memories = []
    if options.get("include_memory", True):
        memory_limit = options.get("memory_limit", 3)
        recent_memories = self.memory.get_recent(limit=memory_limit)

    # 5. 历史（可选）- 应用压缩
    history = options.get("history", [])
    if history and self._should_compress_history(history):
        history = self.compressor.compress_with_layers(history)

    # 6. 构建最终上下文（区分结构化数据和 prompt 内容）
    context = {
        "structured": structured_context,  # 给 LLM 决策用
        "prompt_context": {               # 放入 system prompt 的内容
            "agent_summary": self._build_agent_summary(configs),
            "recent_memory": recent_memories[:3],
            "relevant_text": text_contents,
            "user_input": user_input
        },
        "history": history
    }

    return context

def _load_text_summaries(self, agent_id: str) -> Dict:
    """加载文本摘要而非完整内容"""
    summaries = {}

    for config_type in ["soul", "user", "skill"]:
        full_text = self.config_manager.load_text(agent_id, config_type)
        if full_text:
            # 生成摘要（或用前 N 行）
            lines = full_text.split("\n")
            if len(lines) > 20:
                summaries[config_type] = "\n".join(lines[:20]) + "\n...(省略)"
            else:
                summaries[config_type] = full_text

    return summaries
```

### 4.4 压缩时机判断

| 时机 | 判断条件 | 压缩动作 |
|------|----------|----------|
| **启动时检查** | `token_count > soft_limit` | 预压缩早期历史 |
| **每轮对话前** | `token_count > hard_limit` | 立即压缩 |
| **复杂任务** | `complexity == high` | 保留更多上下文 |
| **简单任务** | `complexity == low` | 激进压缩 |
| **用户明确要求** | `user_input` 包含"记住" | 保留相关历史 |

---

## 五、配置文件最佳实践

### 5.1 配置文件结构

```
storage/agents/{agent_id}/
├── soul.md         # 身份认同（使命、性格、价值观）
├── user.md         # 能力边界（角色、工具、LLM）
├── skill.md        # 技能树（渐进式能力、解锁条件）
├── logic.md        # 决策逻辑（路由规则、意图识别）
├── memory.md       # 记忆策略（类型、更新规则）
└── level.md        # 用户级别（当前级别、升级进度）
```

### 5.2 soul.md - 身份认同

```markdown
---
version: '1.0'
name: core_brain
description: 核心大脑 - 本地运行的 AI 助手
role: 核心协调器
---

# 核心身份

## 使命
协调多 Agent 合作，优化任务分配，确保系统稳定运行

## 核心特质
- **人格**: 冷静、分析型、协作导向
- **价值观**: 效率、协作、透明
- **目标**: 协调多 Agent 合作、优化任务分配、确保系统稳定运行

## 行为模式
- **决策方式**: 协作式 - 先分析再行动
- **问题解决**: 分步分析 - 复杂任务自动拆解
- **沟通风格**: 清晰简洁 - 不冗余

## 进化规则
- 允许自我修改：false
- 需要用户确认：true
- 修改前快照：true
```

### 5.3 user.md - 能力边界

```yaml
---
version: '1.0'
agent_id: core_brain
---

# 角色定义

role:
  type: coordinator
  title: Core Brain
  responsibilities:
    - 任务分析与分解
    - Agent 协调与合作
    - 资源分配与优化

# 能力边界

capabilities:
  max_team_size: 10
  can_create_agent: true
  can_modify_config: true
  can_execute_tools: true

# 工具配置

tools:
  enabled:
    - bash_executor
    - grep_tool
    - file_tools

  bash_executor:
    timeout: 30
    forbidden_commands:
      - "rm -rf /"
      - "sudo rm"

# LLM 配置

llm:
  enabled: true
  max_tokens: 2048
  model: claude-sonnet-4-5-20251001
```

### 5.4 skill.md - 技能树

```yaml
---
version: '1.0'
agent_id: core_brain
---

# 技能树配置

## 技能层级

skill_layers:
  layer_1:
    name: 基础交互
    unlocked: always
    skills:
      - name: response
        description: 直接回复用户
      - name: bash
        description: 执行 shell 命令
      - name: memory
        description: 管理记忆

  layer_2:
    name: 协作能力
    unlock_condition:
      create_agent_count: 1
    skills:
      - name: create_user
        description: 创建新 Agent
      - name: chat
        description: 与其他 Agent 对话
      - name: create_team
        description: 创建 Agent 团队

  layer_3:
    name: 专家能力
    unlock_condition:
      use_heart_explicitly: true
    skills:
      - name: heart
        description: 自省与进化
      - name: network_delegate
        description: 任务委派
      - name: network_broadcast
        description: 广播消息
```

### 5.5 logic.md - 决策逻辑

```markdown
---
version: '1.0'
agent_id: core_brain
---

# 路由决策逻辑

## 意图识别规则

### 优先级 1：明确命令格式
| 模式 | 路由 | 示例 |
|------|------|------|
| `$ ` 或 `$` 开头 | bash | `$ ls -la` |
| `bash/sh/sudo` 开头 | bash | `bash script.sh` |
| 常见命令 (ls/cd/pwd) | bash | `ls -la` |

### 优先级 2：协作意图
| 关键词 | 路由 | 解锁条件 |
|--------|------|---------|
| create/new/创建 | create_user | Layer 1+ |
| team/group/团队 | create_team | Layer 2+ |
| memory/记住/记忆 | memory | Layer 1+ |
| chat/对话 | chat | Layer 2+ |

### 优先级 3：专家命令
| 关键词 | 路由 | 解锁条件 |
|--------|------|---------|
| heart/自省/evolve | heart | Layer 3+ |
| delegate/broadcast | network_* | Layer 3+ |

## 决策流程

```
用户输入
    │
    ▼
┌─────────────────┐
│ 1. 检查命令格式  │ → 匹配 → route: bash
└────────┬────────┘
         │ 不匹配
         ▼
┌─────────────────┐
│ 2. 检查关键词    │ → 匹配 → route: xxx
└────────┬────────┘
         │ 不匹配
         ▼
┌─────────────────┐
│ 3. LLM 分析意图   │ → route: response
└─────────────────┘
```
```

### 5.6 level.md - 用户级别

```yaml
---
version: '1.0'
agent_id: core_brain
---

# 用户级别配置

## 当前级别
current_level: novice
unlocked_routes:
  - response
  - bash
  - memory

## 升级进度
progress:
  create_agent_count: 0
  total_interactions: 5
  advanced_features_used: []
  heart_used: false
  network_feature_used: false

## 升级条件
level_up:
  novice_to_advanced:
    - condition: create_agent_count >= 1
    - condition: total_interactions >= 10
  advanced_to_expert:
    - condition: heart_used == true
    - condition: network_feature_used == true
```

---

## 六、实施建议

### 6.1 优先级排序

| 优先级 | 任务 | 预计工时 | 依赖 |
|--------|------|----------|------|
| P0 | 添加 `available_routes` 到上下文 | 1 小时 | 无 |
| P0 | 设计路由选择提示词模板 | 2 小时 | 无 |
| P0 | 实现分层压缩策略 | 3 小时 | 无 |
| P1 | 完善 FileTools | 4 小时 | 无 |
| P1 | 集成 Tavily Web Search | 4 小时 | 无 |
| P2 | 用户级别系统 | 4 小时 | skill.md |
| P2 | 渐进式披露逻辑 | 6 小时 | level.md |

### 6.2 代码变更清单

| 文件 | 变更内容 | 变更类型 |
|------|----------|----------|
| `mul_agent/brain/context_builder.py` | 添加 `available_routes`、`available_tools` | 增强 |
| `mul_agent/brain/brain.py` | 添加 `_decide_action_with_llm()` | 新增 |
| `mul_agent/brain/compressor.py` | 实现 `compress_with_layers()` | 增强 |
| `mul_agent/tools/mcp_tools.py` | 完善 `FileTools`、`WebSearchMCP` | 增强 |
| `wang/agent-team/.templates/` | 添加 `skill.md.template`、`level.md.template` | 新增 |

### 6.3 测试验证清单

- [ ] 路由选择准确率测试（目标 > 90%）
- [ ] 上下文压缩效果测试（压缩率 > 50%，信息保留 > 80%）
- [ ] 长对话场景测试（100+ 轮对话不超限）
- [ ] 复杂任务上下文充足性测试
- [ ] 渐进式披露效果测试（新用户上手时间缩短）

---

## 七、总结

### 7.1 核心发现

1. **基础架构完整**: Brain-Router-Handler 架构清晰，Memory/Tool 模块功能齐全
2. **路由决策可优化**: 当前硬编码规则可增强为 LLM 辅助决策
3. **上下文压缩必要**: 已有压缩机制，但需分层策略提高灵活性
4. **提示词是关键**: 好的提示词能让 Agent 更聪明地选择路由

### 7.2 核心建议

| 问题 | 方案 | 预期效果 |
|------|------|----------|
| 路由查找不智能 | 添加 `available_routes` + 路由选择提示词 | 准确率提升至 90%+ |
| 上下文膨胀 | 分层压缩 + 动态阈值 | 压缩率 50%+，信息保留 80%+ |
| 提示词结构散 | 规范化 soul/user/skill/logic 职责 | 维护成本降低 |
| 工具不完整 | 完善 FileTools + 集成 WebSearch | 能力覆盖 100% |

### 7.3 下一步行动

1. **立即实施** (今天):
   - 修改 `ContextBuilder` 添加 `available_routes`
   - 创建路由选择提示词模板

2. **本周实施**:
   - 实现分层压缩策略
   - 完善 FileTools

3. **下周实施**:
   - 集成 Tavily Web Search
   - 实现用户级别系统
