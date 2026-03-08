---
version: "2.0"
agent_id: wangyue
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

# 望月 - 记忆系统配置

## 核心原则

**记忆是为了在需要的时候能找到解决问题的方法。**

## 记忆策略

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

## 记忆保留规则

1. **用户陈述**: 永久保留
2. **用户反馈**: 永久保留
3. **项目逻辑**: 短期保留
4. **会话上下文**: 临时保留

## 更新触发条件

- 上下文长度超过 10 条
- 时间超过 24 小时
- 用户明确否定/肯定
