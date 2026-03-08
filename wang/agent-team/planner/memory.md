---
version: "3.0"
agent_id: planner
memory_strategy:
  short_term:
    storage: session
    max_items: 100
    ttl_hours: 24
  long_term:
    storage: file
    path: wang/memory/long_term/planner
    max_items: 500
  handover:
    storage: file
    path: wang/memory/handover/planner
---

# Planner - 记忆系统与 Memory Skill

## 一、核心原则

**记忆是为了在需要的时候能找到解决问题的方法。**

---

## 二、记忆策略

### 短期记忆（会话级）

**存储内容**：
- 当前规划任务的上下文
- 用户的具体需求
- 讨论中的方案细节

**使用场景**：
- 理解"这个方案"、"那个功能"等指代
- 保持规划任务连贯性

### 长期记忆（持久化）

**存储内容**：
- 用户的规划偏好
- 历史规划方案
- 项目架构决策记录

**使用场景**：
- 遇到相似问题时检索历史方案
- 遵循项目架构规范

### 交接记忆（Agent 间传递）

**存储内容**：
- 任务交接的上下文
- 已完成的规划
- 待实施的建议

---

## 三、Memory Skill - 记忆管理技能

### 触发时机

| 场景 | 触发条件 |
|------|----------|
| 用户明确要求 | "记住..."、"别忘了..." |
| 历史参考 | "我之前说过..."、"上次我们..." |
| 任务交接 | 需要保存任务进展给其他 Agent |
| 经验记录 | 完成规划后记录方案 |

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

## 四、记忆规则

### 记录时机

| 时机 | 记录内容 |
|------|----------|
| 完成规划后 | 规划方案和执行结果 |
| 架构决策后 | 决策理由和权衡 |
| 用户确认后 | 用户偏好和要求 |

### 检索时机

| 时机 | 检索内容 |
|------|----------|
| 接收规划任务时 | 相似的历史规划方案 |
| 设计架构时 | 项目架构决策记录 |
| 技术选型时 | 历史技术选型记录 |

---

## 五、记忆决策

```yaml
记住的条件:
  - 用户明确要求记住
  - 完成规划方案
  - 做出重要架构决策

遗忘的条件:
  - 临时讨论方案（决策后）
  - 过时的规划版本
```

---

## 六、使用示例

### 示例 1：记住用户偏好

```
用户：记住，我喜欢详细的规划步骤
→ Memory Skill: write(long_term, "用户偏好：详细规划步骤")
```

### 示例 2：检索历史方案

```
用户：上次那个项目架构是什么？
→ Memory Skill: search(long_term, query="项目架构")
→ 返回历史架构设计
```

### 示例 3：记录架构决策

```
架构决策后：
→ Memory Skill: write(long_term, {
    "decision": "使用微服务架构",
    "reason": "团队规模扩大，需要独立部署",
    "trade_off": "增加了运维复杂度"
  })
```
