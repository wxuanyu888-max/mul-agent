# memory - 记忆管理

版本：v1.0

## 基本信息

| 项目 | 内容 |
|------|------|
| 路由 | memory |
| 触发方式 | CLI --route 或 API调用 |

---

## 请求参数

### 写入记忆

```json
{
  "route": "memory",
  "params": {
    "action": "write",
    "memory_type": "long_term",
    "agent_id": "core_brain",
    "content": {
      "key": "task_001",
      "value": "完成用户登录功能",
      "metadata": {
        "created_at": "2024-01-01T00:00:00Z"
      }
    }
  }
}
```

### 读取记忆

```json
{
  "route": "memory",
  "params": {
    "action": "read",
    "memory_type": "long_term",
    "agent_id": "core_brain",
    "memory_id": "mem_001"
  }
}
```

### 搜索记忆

```json
{
  "route": "memory",
  "params": {
    "action": "search",
    "query": "登录",
    "agent_id": "core_brain"
  }
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| action | string | 是 | 操作：write/read/update/delete/search/list |
| memory_type | string | 是 | 记忆类型：short_term/long_term/handover |
| agent_id | string | 是 | Agent ID |
| memory_id | string | 否 | 记忆ID（read/update/delete需要） |
| content | object | 否 | 记忆内容（write需要） |
| query | string | 否 | 搜索关键词（search需要） |

---

## 响应

### 写入成功

```json
{
  "status": "success",
  "memory_id": "mem_001",
  "action": "write",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 读取成功

```json
{
  "status": "success",
  "memory": {
    "id": "mem_001",
    "type": "long_term",
    "content": {
      "key": "task_001",
      "value": "完成用户登录功能"
    },
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### 搜索成功

```json
{
  "status": "success",
  "results": [
    {
      "memory_id": "mem_001",
      "relevance": 0.95,
      "content": {...}
    }
  ],
  "total": 1
}
```

---

## 关联

- 规则文档：规则/记忆系统/规则.md
- 功能文档：规则/记忆系统/功能.md

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2024-01-01 | 初始版本 |
