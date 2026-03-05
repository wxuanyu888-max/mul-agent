# create_user - 创建新Agent

版本：v1.0

## 基本信息

| 项目 | 内容 |
|------|------|
| 路由 | create_user |
| 触发方式 | CLI --route 或 API调用 |
| 权限要求 | can_create_agent: true |

---

## 请求参数

```json
{
  "route": "create_user",
  "params": {
    "agent_id": "new_agent_001",
    "name": "新Agent名称",
    "role_type": "worker",
    "initial_config": {}
  }
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agent_id | string | 是 | Agent唯一标识 |
| name | string | 是 | Agent名称 |
| role_type | string | 否 | 角色类型：coordinator/worker，默认worker |
| initial_config | object | 否 | 初始配置 |

---

## 响应

### 成功

```json
{
  "status": "success",
  "agent_id": "new_agent_001",
  "message": "Agent创建成功",
  "config_path": "storage/agents/new_agent_001/"
}
```

### 失败

| 错误码 | 说明 |
|--------|------|
| 3001 | 团队已满 |
| 3002 | Agent ID已存在 |
| 3003 | 配置创建失败 |

---

## 关联

- 规则文档：规则/核心大脑/规则.md
- 功能文档：规则/核心大脑/功能.md

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2024-01-01 | 初始版本 |
