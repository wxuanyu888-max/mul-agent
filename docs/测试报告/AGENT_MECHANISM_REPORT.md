# Agent 任务分发、路由调用、团队协作、自我进化 完整报告

## 一、任务分发机制

### 1.1 决策流程

```
用户输入
    ↓
[Brain.think()]
    ↓
1. 保存到对话历史
2. 构建上下文 (ContextBuilder)
3. 判断是否需要压缩上下文
    ↓
[决策分支]
├── LLM 可用 → llm.think() 生成 action
└── LLM 不可用 → _decide_action() 关键词匹配
    ↓
[Router.dispatch()]
    ↓
对应 Handler 处理
```

### 1.2 路由决策逻辑 (`_decide_action`)

| 关键词 | 路由 | 参数 |
|--------|------|------|
| create/创建 | create_user | {"name": ...} |
| bash/运行/$ | bash | {"command": ...} |
| memory/记忆 | memory | {"action": "list", ...} |
| heart/自省 | heart | {"trigger": "manual", ...} |
| 其他 | chat | {"agent_id": target, ...} |

### 1.3 目标 Agent 决策 (`_decide_target_agent`)

```python
def _identify_task_type(input_lower: str) -> Optional[str]:
    """识别任务类型"""
    # coding 相关
    if any(kw in input_lower for kw in ['code', '编程', 'function', 'bug']):
        return "coding"
    # security 相关
    if any(kw in input_lower for kw in ['security', '安全', 'audit']):
        return "security"
    # testing 相关
    if any(kw in input_lower for kw in ['test', '测试', 'coverage']):
        return "testing"
    # writing 相关
    if any(kw in input_lower for kw in ['write', '文档', 'readme']):
        return "writing"
    # research 相关
    if any(kw in input_lower for kw in ['search', '搜索', '查找']):
        return "research"
    # planning 相关
    if any(kw in input_lower for kw in ['plan', '架构', 'design']):
        return "planning"
    return None
```

### 1.4 任务分发实例

| 任务输入 | 识别类型 | 目标 Agent | 路由 |
|----------|----------|------------|------|
| "创建一个 Python 文件" | create | - | create_user |
| "运行 ls -la 命令" | bash | - | bash |
| "和 coder 对话" | collaboration | coder | chat |
| "写单元测试" | testing | test_agent | chat |

---

## 二、路由调用

### 2.1 核心路由

| 路由名称 | 处理器 | 功能 |
|----------|--------|------|
| create_user | CreateUserHandler | 创建新 Agent |
| bash | BashHandler | 执行 shell 命令 |
| heart | HeartHandler | 自省、反思、状态查询 |
| memory | MemoryHandler | 记忆管理 (读/写/搜索) |
| chat | ChatHandler | 与其他 Agent 对话 |
| response | ResponseHandler | 直接响应 |
| token_usage | TokenUsageHandler | Token 使用统计 |

### 2.2 Agent Network 路由 (新增)

| 路由名称 | 处理器 | 功能 |
|----------|--------|------|
| network_delegate | NetworkDelegateHandler | 任务委派 |
| network_send | NetworkSendHandler | 发送消息 |
| network_check | NetworkCheckHandler | 检查消息 |
| network_broadcast | NetworkBroadcastHandler | 广播消息 |
| network_handover | NetworkHandoverHandler | 交接文档 |

### 2.3 路由调用示例

```python
# 调用 heart 路由
result = brain.router.dispatch("heart", {"trigger": "manual", "focus": "status"})
# 返回:
# {
#     "status": "success",
#     "result": {
#         "analysis": {...},
#         "can_evolve": True,
#         "evolutions_applied": [...]
#     }
# }

# 调用 network_delegate 路由
result = brain.router.dispatch("network_delegate", {
    "to_agent": "coder",
    "task": {"description": "Write code", "priority": 1}
})
```

---

## 三、团队协作

### 3.1 Agent Network 架构

```
┌─────────────────────────────────────────────────────────┐
│                    AgentNetwork                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   coder     │  │  reviewer   │  │ test_agent  │      │
│  │ (coding)    │  │ (security)  │  │ (testing)   │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
│  ┌─────────────┐  ┌─────────────┐                        │
│  │   writer    │  │ core_brain  │                        │
│  │ (writing)   │  │ (coordinator)│                       │
│  └─────────────┘  └─────────────┘                        │
└─────────────────────────────────────────────────────────┘
                         ↕
              ┌─────────────────────┐
              │    MessageQueue     │
              │  (持久化消息存储)    │
              └─────────────────────┘
```

### 3.2 已注册 Agent

| Agent ID | 能力 | 角色 |
|----------|------|------|
| core_brain | 无特殊能力 | 团队协调员 |
| coder | coding, development | 代码专家 |
| reviewer | security, review | 安全审查专家 |
| test_agent | coding, testing | 测试专家 |
| writer | writing, documentation | 文档专家 |

### 3.3 任务委派流程

```python
# 1. 查找专业 Agent
specialist = brain.find_specialist('coding')
# 返回：{'status': 'success', 'found': True, 'agent_id': 'coder'}

# 2. 委派任务
msg_id = brain.network.delegate_task(
    from_agent='core_brain',
    to_agent='coder',
    task={'description': 'Write Python function', 'priority': 1}
)

# 3. 消息入队 (MessageQueue)
# 消息存储在：storage/message_queue/queues/coder/{msg_id}.json

# 4. 目标 Agent 接收消息
messages = mq.receive('coder', limit=5)
```

### 3.4 消息队列状态

| Agent | 待处理消息 | 说明 |
|-------|------------|------|
| coder | 0 | 消息已被处理 |
| reviewer | 0 | 消息已被处理 |
| test_agent | 0 | 消息已被处理 |
| writer | 0 | 消息已被处理 |

---

## 四、自我进化

### 4.1 进化配置 (soul.md)

```yaml
version: "2.0"
evolution_rules:
  can_modify_self: true           # 允许自我修改
  modification_scope: 核心模块与配置参数
  snapshot_before_change: true    # 修改前创建快照
  self_check_required: false      # 不强制自检验

collaboration:
  mode: auto                      # 自动协作模式
  auto_delegate_threshold: 0.7   # 置信度低于 0.7 自动委派
  network_enabled: true           # 启用 Agent 网络
  parallel_execution_enabled: true # 启用并行执行
```

### 4.2 进化流程

```
[Brain.evolve()]
    ↓
1. _analyze_current_state() - 分析当前状态
2. _generate_evolution() - 生成进化方案 (使用 LLM)
3. 检查 can_modify_self
   ├── True: 应用变更
   │   ├── 创建快照 (snapshot_before_change)
   │   ├── 应用变更 (_apply_change)
   │   └── 保存到磁盘 (config_manager.save)
   └── False: 返回建议等待确认
    ↓
4. 返回进化结果
```

### 4.3 进化示例

实际调用 `heart` 路由时的进化结果：

```json
{
  "status": "success",
  "evolutions_applied": [{
    "type": "soul",
    "field": "version",
    "old": "2.0",
    "new": "2.1",
    "reason": "描述中已声明 v2.1 特性，需保持版本号一致"
  }],
  "can_evolve": true
}
```

### 4.4 进化指南

根据 `soul.md` 定义：

**进化要求**:
- 每个改进建议必须包含具体修改内容（字段级）
- 必须说明预期影响（可量化）
- 必须标注优先级（High/Medium/Low）
- 必须提供回滚方案

**进化流程**:
1. 识别改进机会
2. 创建快照备份
3. 提出具体修改方案
4. 评估影响范围
5. 执行修改
6. 验证修改结果

---

## 五、系统能力评估

### 5.1 任务分发能力

| 评估项 | 状态 | 说明 |
|--------|------|------|
| 关键词匹配 | ✓ | 支持 create/bash/memory/heart/chat |
| 任务类型识别 | ✓ | 支持 coding/security/testing/writing/research/planning |
| Agent 自动路由 | ✓ | 根据任务类型自动选择目标 Agent |

### 5.2 路由调用能力

| 评估项 | 状态 | 说明 |
|--------|------|------|
| 核心路由 | ✓ | 7 个核心路由正常工作 |
| 网络路由 | ✓ | 5 个网络路由已添加 |
| 路由扩展 | ✓ | 支持动态添加新路由 |

### 5.3 团队协作能力

| 评估项 | 状态 | 说明 |
|--------|------|------|
| Agent 注册 | ✓ | 5 个 Agent 已注册 |
| 专家查找 | ✓ | find_specialist() 正常工作 |
| 任务委派 | ✓ | delegate_task() 发送消息 |
| 消息持久化 | ✓ | MessageQueue 存储消息 |
| 并行执行 | ✓ | ParallelExecutor 支持并发 |

### 5.4 自我进化能力

| 评估项 | 状态 | 说明 |
|--------|------|------|
| 自我分析 | ✓ | _analyze_current_state() |
| 进化方案生成 | ✓ | _generate_evolution() 使用 LLM |
| 配置修改 | ✓ | can_modify_self=True |
| 快照备份 | ✓ | snapshot_before_change=True |
| 协作配置 | ✓ | mode=auto, threshold=0.7 |

---

## 六、结论

### 6.1 任务分发机制

**现状**:
- ✓ 基于关键词匹配的简单路由
- ✓ 支持 6 种基本任务类型
- ✓ 自动识别目标 Agent

**局限**:
- LLM 决策未完全启用 (需要 API key)
- 复杂任务分解需要手动配置

### 6.2 路由调用

**现状**:
- ✓ 12 个路由处理器
- ✓ 支持动态扩展
- ✓ Router.dispatch() 统一分发

**特点**:
- 核心路由处理基本任务
- 网络路由支持 Agent 协作
- Handler 模式便于扩展

### 6.3 团队协作

**现状**:
- ✓ 5 个专业 Agent
- ✓ Agent Network 支持注册/发现
- ✓ MessageQueue 持久化消息
- ✓ 支持任务委派和消息传递

**能力**:
- 可识别并委派任务给专业 Agent
- 支持消息队列异步通信
- 支持并行执行引擎

### 6.4 自我进化

**现状**:
- ✓ can_modify_self=True
- ✓ 支持 soul/user/skill/memory 修改
- ✓ 快照备份机制
- ✓ LLM 辅助进化分析

**特点**:
- 版本号自动更新
- 配置一致性检查
- 支持进化建议生成

---

**报告生成时间**: 2026-03-06
**系统版本**: Mul-Agent v2.0
**测试状态**: ✓ 验证通过
