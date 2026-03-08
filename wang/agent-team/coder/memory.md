---
version: "3.0"
agent_id: coder
memory_strategy:
  short_term:
    storage: session
    max_items: 100
    ttl_hours: 24
  long_term:
    storage: file
    path: wang/memory/long_term/coder
    max_items: 500
  handover:
    storage: file
    path: wang/memory/handover/coder
---

# Coder - 记忆系统与 Memory Skill

## 一、核心原则

**记忆是为了在需要的时候能找到解决问题的方法。**

---

## 二、记忆策略

### 短期记忆（会话级）

**存储内容**：
- 当前任务的上下文
- 正在编辑的文件
- 用户的即时反馈

**使用场景**：
- 理解"这个文件"、"那个函数"等指代
- 保持编码任务连贯性

### 长期记忆（持久化）

**存储内容**：
- 用户的编码偏好
- 项目结构和规范
- 历史解决方案

**使用场景**：
- 遇到相似问题时检索历史方案
- 遵循项目编码规范

### 交接记忆（Agent 间传递）

**存储内容**：
- 任务交接的上下文
- 已完成代码的说明
- 待实现的功能

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

## 四、记忆规则

### 记录时机

| 时机 | 记录内容 |
|------|----------|
| 完成任务后 | 实现方案和结果 |
| 修复 bug 后 | 问题原因和解决方法 |
| 用户确认后 | 用户偏好和规范 |

### 检索时机

| 时机 | 检索内容 |
|------|----------|
| 接收任务时 | 相似的历史解决方案 |
| 编写代码时 | 项目编码规范 |
| 遇到问题时 | 历史问题解决记录 |

---

## 五、记忆决策

```yaml
记住的条件:
  - 用户明确要求记住
  - 完成任务实现
  - 发现重要项目逻辑

遗忘的条件:
  - 临时上下文（任务完成后）
  - 过时的实现方案
```

---

## 六、使用示例

### 示例 1：记住用户偏好

```
用户：记住，我喜欢用 TypeScript
→ Memory Skill: write(long_term, "用户偏好：TypeScript")
```

### 示例 2：检索历史方案

```
用户：上次那个 API 怎么写的？
→ Memory Skill: search(long_term, query="API 实现")
→ 返回历史代码方案
```

### 示例 3：记录 Bug 修复

```
修复 bug 后：
→ Memory Skill: write(long_term, {
    "bug": "登录 token 过期",
    "cause": "时间计算错误",
    "solution": "修正过期时间公式"
  })
```
