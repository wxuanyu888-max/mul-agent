# heart - 自省/进化

版本：v1.0

## 基本信息

| 项目 | 内容 |
|------|------|
| 路由 | heart |
| 触发方式 | CLI --route 或 API调用 |
| 权限要求 | 核心大脑专属 |

---

## 请求参数

```json
{
  "route": "heart",
  "params": {
    "trigger": "manual",
    "focus": "all"
  }
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| trigger | string | 否 | 触发方式：manual/automatic，默认manual |
| focus | string | 否 | 关注点：all/soul/user/skill/memory，默认all |

---

## 响应

### 成功

```json
{
  "status": "success",
  "analysis": {
    "current_state": {
      "team_size": 3,
      "recent_tasks": [...],
      "success_rate": 0.85
    },
    "issues_found": [
      "Bash超时设置过长",
      "部分技能未启用"
    ],
    "proposed_changes": [
      "调整bash超时为60秒",
      "启用web_search技能"
    ]
  },
  "evolutions_applied": [
    {
      "config": "user.json",
      "field": "tools.bash.timeout",
      "old_value": 30,
      "new_value": 60
    }
  ],
  "snapshot_id": "snapshot_20240101_001"
}
```

---

## 关联

- 规则文档：规则/核心大脑/规则.md

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2024-01-01 | 初始版本 |
