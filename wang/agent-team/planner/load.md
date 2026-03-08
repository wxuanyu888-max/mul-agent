---
version: "3.0"
agent_id: planner
---

# Agent Load Configuration

## 默认加载文件列表

```yaml
files:
  - path: soul.md
    required: true
  - path: user.md
    required: true
  - path: memory.md
    required: true
```

## 加载规则

1. 仅加载本列表配置的文件
2. 按列表顺序依次加载
3. `required: true` 的文件必须存在

## 文件说明

| 文件 | 说明 |
|------|------|
| `soul.md` | Agent 的角色、价值观、核心特质 |
| `user.md` | 用户配置、工具权限、路由逻辑、Skills |
| `memory.md` | 记忆策略、存储配置、检索规则 |

---
