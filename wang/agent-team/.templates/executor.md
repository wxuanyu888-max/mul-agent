---
version: "1.0"
type: executor_template
---

# Executor Agent 模板

适用于：代码实现、文档编写、数据处理等执行类任务

```yaml
---
version: "1.0"
agent_id: <agent_id>
name: <名称>
role:
  type: executor
  title: <角色标题>
  responsibilities:
    - 职责 1
    - 职责 2
tools:
  bash: true
  file_edit: true
  memory: true
  chat: true
llm:
  enabled: true
  temperature: 0.3
---

# <名称> - <角色标题>

## 核心职责
1. 职责 1 描述
2. 职责 2 描述

## 工作流程
1. 理解需求
2. 执行任务
3. 验证结果
4. 提交输出
```
