# bash - 执行命令

版本：v1.0

## 基本信息

| 项目 | 内容 |
|------|------|
| 路由 | bash |
| 触发方式 | CLI --route 或 API调用 |
| 权限要求 | tools.bash.enabled: true |

---

## 请求参数

```json
{
  "route": "bash",
  "params": {
    "command": "ls -la",
    "timeout": 30,
    "cwd": "/path/to/dir"
  }
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| command | string | 是 | 要执行的shell命令 |
| timeout | int | 否 | 超时时间（秒），默认30 |
| cwd | string | 否 | 工作目录 |

---

## 响应

### 成功

```json
{
  "status": "success",
  "stdout": "total 0\ndrwxr-xr-x  5 user  staff   160 Jan  1 00:00 .",
  "stderr": "",
  "exit_code": 0,
  "duration": 0.123
}
```

### 失败

| 错误码 | 说明 |
|--------|------|
| 4001 | 命令执行超时 |
| 4002 | 命令被禁止 |
| 4003 | 工具未启用 |

---

## 关联

- 规则文档：规则/工具层/规则.md

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2024-01-01 | 初始版本 |
