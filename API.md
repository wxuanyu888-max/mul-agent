# API Documentation - 接口文档

> 详细说明系统提供的API接口

---

## 1. CLI 命令行接口

### 1.1 启动核心大脑（交互模式）

```bash
python main.py brain
# 或
python main.py repl
```

启动核心大脑Agent，进入交互模式。

### 1.2 指定Agent启动

```bash
python main.py agent <agent_id>
```

使用指定Agent ID启动。

### 1.3 查看团队状态

```bash
python main.py team
```

列出当前所有Agent成员及状态。

### 1.4 手动触发路由

```bash
python main.py route <route_name> --params <json>
```

手动触发指定的路由。

### 1.5 守护进程模式（实验性）

```bash
# 启动守护进程（默认配置）
python main.py daemon

# 自定义空闲超时和成长间隔
python main.py daemon --idle-timeout 300 --grow-interval 3600

# 禁用自动自我成长
python main.py daemon --no-growth
```

守护进程内置命令：
- `status` - 查看守护状态
- `task add <action> <interval>` - 添加定时任务
- `task list` - 查看定时任务
- `task del <id>` - 删除定时任务
- `rest` - 强制进入休息状态
- `work` - 强制进入工作状态
- `grow` - 立即触发自我成长

### 1.6 帮助命令

```bash
python main.py --help
```

显示帮助信息。

---

## 2. 核心路由 API

系统提供 **6个核心路由**：

| 路由 | 处理器 | 功能 |
|------|--------|------|
| `create_user` | CreateUserHandler | 创建新Agent成员 |
| `bash` | BashHandler | 执行shell命令 |
| `heart` | HeartHandler | 自省/进化（分析自身状态并改进） |
| `memory` | MemoryHandler | 记忆管理（读写/搜索） |
| `chat` | ChatHandler | 与其他Agent对话 |
| `response` | ResponseHandler | 直接响应用户 |

### 2.1 create_user - 创建新Agent

创建新的Agent成员。

**请求**
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

**响应**
```json
{
  "status": "success",
  "agent_id": "new_agent_001",
  "message": "Agent创建成功"
}
```

---

### 2.2 bash - 执行命令

执行shell命令。

**请求**
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

**响应**
```json
{
  "status": "success",
  "stdout": "total 0\ndrwxr-xr-x 1 ...",
  "stderr": "",
  "exit_code": 0
}
```

---

### 2.3 heart - 自省/进化

触发核心大脑自省和进化。

**请求**
```json
{
  "route": "heart",
  "params": {
    "trigger": "manual",  // or "automatic"
    "focus": "all"       // or "soul", "user", "skill", "memory"
  }
}
```

**响应**
```json
{
  "status": "success",
  "analysis": {
    "current_state": {...},
    "issues_found": [...],
    "proposed_changes": [...]
  },
  "evolutions_applied": [...]
}
```

---

### 2.4 memory - 记忆管理

管理记忆的读/写/更新。

**请求**
```json
{
  "route": "memory",
  "params": {
    "action": "write",    // or "read", "update", "delete", "list"
    "memory_type": "long_term",  // or "short_term", "handover"
    "agent_id": "core_brain",
    "content": {
      "key": "some_key",
      "value": "some_value"
    }
  }
}
```

**响应**
```json
{
  "status": "success",
  "memory_id": "mem_001",
  "action": "write",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

### 2.5 chat - Agent间对话

与其他Agent进行对话。

**请求**
```json
{
  "route": "chat",
  "params": {
    "target_agent": "agent_id",
    "message": "hello"
  }
}
```

---

### 2.6 response - 直接响应

直接响应用户，不执行任何工具。

**请求**
```json
{
  "route": "response",
  "params": {
    "message": "你好，我是核心大脑"
  }
}
```

---

## 3. 工具层 API

### 3.1 Bash Executor

```python
class BashExecutor:
    def execute(command: str, timeout: int = 30, cwd: str = None) -> dict
    def is_safe(command: str) -> bool
```

### 3.2 Chrome MCP

```python
class ChromeMCP:
    def navigate(url: str) -> dict
    def click(selector: str) -> dict
    def fill(selector: str, value: str) -> dict
    def screenshot() -> bytes
    def execute_script(script: str) -> any
```

### 3.3 Web Search MCP

```python
class WebSearchMCP:
    def search(query: str, max_results: int = 10) -> list
    def get_page(url: str) -> str
```

---

## 4. 守护进程 API

### 4.1 AgentDaemon

守护进程支持自动自我成长和定时任务。

```python
class AgentDaemon:
    def start(self) -> None
    def stop(self) -> None
    def force_rest(self) -> None
    def force_work(self) -> None
    def add_scheduled_task(self, name: str, action: str, params: dict, interval: int) -> str
    def remove_scheduled_task(self, task_id: str) -> bool
    def get_status(self) -> dict
    def record_activity(self) -> None
```

### 4.2 状态管理

守护进程有两种状态：
- **工作状态 (WORKING)**: 正在处理用户请求
- **休息状态 (RESTING)**: 定时执行任务 + 自我成长

---

## 5. 配置管理 API

### 4.1 读取配置

```python
class ConfigManager:
    def load(agent_id: str, config_type: str) -> dict
    def load_all(agent_id: str) -> dict
```

### 4.2 写入配置

```python
class ConfigManager:
    def save(agent_id: str, config_type: str, data: dict) -> bool
    def create_snapshot(agent_id: str) -> str
    def restore_snapshot(snapshot_id: str) -> bool
```

### 4.3 热重载

```python
class ConfigManager:
    def reload(agent_id: str) -> bool
    def watch_changes(agent_id: str, callback: callable) -> None
```

---

## 6. 记忆系统 API

### 6.1 读取记忆

```python
class Memory:
    def read(agent_id: str, memory_type: str, memory_id: str = None) -> dict
    def search(query: str, agent_id: str = None) -> list
    def get_recent(agent_id: str, limit: int = 10) -> list
```

### 5.2 写入记忆

```python
class Memory:
    def write(agent_id: str, memory_type: str, content: dict) -> str
    def update(memory_id: str, content: dict) -> bool
    def delete(memory_id: str) -> bool
```

### 5.3 交接文档

```python
class Memory:
    def create_handover(from_agent: str, to_agent: str, content: dict) -> str
    def read_handover(handover_id: str) -> dict
    def list_handoffs(agent_id: str = None) -> list
```

---

## 7. 事件与回调

### 6.1 系统事件

| 事件名 | 说明 | 回调参数 |
|--------|------|----------|
| `agent_created` | 新Agent创建 | (agent_id, config) |
| `agent_deleted` | Agent删除 | (agent_id) |
| `config_modified` | 配置被修改 | (agent_id, config_type, changes) |
| `memory_written` | 记忆写入 | (memory_id, content) |
| `tool_executed` | 工具执行 | (tool_name, params, result) |

### 6.2 注册回调

```python
class EventManager:
    def on(event: str, callback: callable) -> None
    def off(event: str, callback: callable) -> None
    def emit(event: str, *args, **kwargs) -> None
```

---

## 8. 错误处理

### 7.1 错误码

| 错误码 | 说明 |
|--------|------|
| 1000 | 未知错误 |
| 1001 | 配置不存在 |
| 1002 | 配置格式错误 |
| 1003 | 权限不足 |
| 1004 | 工具执行失败 |
| 1005 | 记忆读取失败 |
| 1006 | 记忆写入失败 |
| 1007 | 快照创建失败 |
| 1008 | 版本不兼容 |

### 7.2 错误响应格式

```json
{
  "status": "error",
  "error_code": 1001,
  "message": "配置不存在",
  "details": {}
}
```
