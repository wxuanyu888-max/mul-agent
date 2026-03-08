---
version: "3.0"
agent_id: wangyue
name: 望月
memory_strategy:
  short_term:
    enabled: true
    max_items: 100
    ttl_hours: 24
    storage: session
  long_term:
    enabled: true
    max_items: 1000
    storage: file
    path: wang/memory/long_term/wangyue
  handover:
    enabled: true
    max_items: 50
    storage: file
    path: wang/memory/handover/wangyue
retention_rules:
  user_statements: permanent
  user_feedback: permanent
  project_logic: short_term
  session_context: ephemeral
update_triggers:
  context_length_threshold: 10
  time_threshold_hours: 24
---

# 望月 - 记忆系统与 Memory Skill

## 一、核心原则

**记忆是为了在需要的时候能找到解决问题的方法。**

---

## 二、记忆策略

### 短期记忆
- **启用**: 是
- **最大条目**: 100
- **存储**: 会话存储
- **存活时间**: 24 小时
- **用途**: 理解对话上下文、指代消解

### 长期记忆
- **启用**: 是
- **最大条目**: 1000
- **存储**: 文件存储
- **路径**: wang/memory/long_term/wangyue
- **用途**: 用户偏好、历史解决方案、项目逻辑

### 交接记忆
- **启用**: 是
- **最大条目**: 50
- **存储**: 文件存储
- **路径**: wang/memory/handover/wangyue
- **用途**: Agent 间任务交接、上下文传递

---

## 三、Memory Skill - 记忆管理技能

### 触发时机

| 场景 | 触发条件 |
|------|----------|
| 用户明确要求 | "记住..."、"别忘了..." |
| 历史参考 | "我之前说过..."、"上次我们..." |
| 任务交接 | 需要保存任务进展给其他 Agent |
| 经验记录 | 完成任务后记录解决方案 |

### 可用操作

| 操作 | 描述 | 参数 |
|------|------|------|
| `list` | 列出记忆 | memory_type, limit |
| `read` | 读取记忆 | memory_type, key |
| `write` | 写入记忆 | memory_type, content, key |
| `delete` | 删除记忆 | memory_type, key |
| `search` | 搜索记忆 | query, memory_type, limit |

### 路由规则

```
用户输入
    │
    ▼
记忆相关关键词
├── "记住..." → write (long_term)
├── "查看记忆" → list / read
├── "搜索记忆" → search
├── "删除记忆" → delete
├── "我之前..." → search (long_term)
└── "任务交接" → write (handover)
```

---

## 四、记忆检索策略

### 主动检索（Action Before Decision）

在路由决策前，主动检索：
1. **相似场景** - 历史上类似的问题是如何解决的
2. **用户偏好** - 用户喜欢的响应方式和详细程度
3. **项目逻辑** - 当前项目的关键文件和结构

### 被动检索（On-Demand）

当用户明确提及时检索：
- "记住..." → 写入长期记忆
- "我之前说过..." → 检索历史记忆
- "上次我们..." → 检索相似场景

### 检索时机

```yaml
路由决策前:
  - 目的：理解上下文，做出更好的决策
  - 检索内容：最近交互、相似场景

执行行动前:
  - 目的：找到最优解决方案
  - 检索内容：历史解决方案、项目逻辑

执行行动后:
  - 目的：记录经验，供未来参考
  - 写入内容：任务类型、解决方案、结果反馈
```

---

## 五、记忆更新规则

### 什么值得记住

**永久保留**：
- 用户明确表达的偏好
- 用户的重要反馈（表扬/批评）
- 项目的核心逻辑和架构

**短期保留**：
- 当前任务的进展
- 临时性的上下文信息
- 会话中的对话历史

**可丢弃**：
- 琐碎的闲聊
- 已完成的临时任务的中间状态

### 更新触发条件

```yaml
基于长度:
  - 短期记忆超过 10 条 → 压缩/归档
  - 长期记忆超过 100 条 → 清理低价值内容

基于时间:
  - 会话超过 24 小时 → 归档旧记忆
  - 长期记忆超过 7 天未访问 → 考虑归档

基于价值:
  - 用户明确否定 → 删除相关记忆
  - 用户明确肯定 → 标记为高价值
```

---

## 六、交接记忆规范

### 交接文档格式

```markdown
---
handover_id: <唯一 ID>
from_agent: <发送方>
to_agent: <接收方>
timestamp: <时间戳>
priority: high|medium|low
---

# 任务交接

**任务**: {task}
**背景**: {background}
**已完成**: {completed}
**待完成**: {todo}
**期望**: {expected}
**相关文件**: {files}
**注意**: {notes}
```

### 必填字段

- `task_summary`: 任务摘要
- `context`: 上下文信息
- `next_steps`: 下一步行动
- `priority`: 优先级

---

## 七、使用示例

### 示例 1：记住用户偏好

```
用户：记住，我喜欢简洁的代码风格
→ Memory Skill: write(long_term, "用户偏好：简洁代码风格")
```

### 示例 2：检索历史方案

```
用户：上次我们是怎么解决那个登录 bug 的？
→ Memory Skill: search(long_term, query="登录 bug")
→ 返回历史解决方案
```

### 示例 3：任务交接

```
用户：把这个任务交给 coder
→ Memory Skill: write(handover, 交接文档)
→ Chat Skill: 通知 coder
```

### 示例 4：记录经验

```
任务完成后：
→ Memory Skill: write(long_term, {
    "task_type": "用户认证",
    "solution": "使用 JWT + bcrypt",
    "result": "success"
  })
```
