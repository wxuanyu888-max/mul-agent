# Session 会话管理

> 以会话为单位管理 Agent 聊天上下文

---

## 概述

Mul-Agent 的 **Session（会话）** 系统是 Agent 聊天和工作的基本单位。每个会话包含：

- **对话历史** - 完整的用户和 Agent 对话记录
- **Token 计数** - 自动追踪会话使用的 token 数量
- **压缩提示** - 当 token 接近上限时自动触发压缩建议
- **Bootstrap 内容** - 可选的初始上下文/设定

---

## 快速开始

### 1. 导入模块

```python
from mul_agent.sessions import SessionManager, TokenThreshold
```

### 2. 创建 SessionManager

```python
# 使用默认配置
session_manager = SessionManager()

# 自定义配置
session_manager = SessionManager(
    storage_path="storage/sessions",  # 存储路径
    default_agent_id="my-agent",      # 默认 Agent ID
    thresholds=TokenThreshold(
        session_warning=8000,         # Session 警告阈值
        session_max=16000,            # Session 最大阈值
        bootstrap_warning=4000,       # Bootstrap 警告阈值
        bootstrap_max=8000,           # Bootstrap 最大阈值
        compression_target=3000,      # 压缩后目标 token 数
    )
)
```

### 3. 创建会话

```python
# 自动分配会话 ID
session = session_manager.create_session(
    title="第一次对话",
    agent_id="my-agent"
)
print(f"会话 ID: {session.id}")

# 指定会话 ID
session = session_manager.create_session(
    session_id="my-custom-session-id",
    title="自定义会话"
)

# 带初始消息
from mul_agent.sessions import SessionMessage

initial_messages = [
    SessionMessage(
        id="msg-1",
        role="user",
        content="你好，请帮我分析这个代码",
        timestamp=datetime.now().timestamp()
    )
]
session = session_manager.create_session(
    initial_messages=initial_messages
)
```

### 4. 添加消息

```python
# 添加用户消息
session = session_manager.add_message(
    session_id="session-123",
    role="user",
    content="请帮我解释这段代码"
)

# 添加 Agent 回复
session = session_manager.add_message(
    session_id="session-123",
    role="assistant",
    content="当然可以，让我来分析一下..."
)
```

### 5. 加载会话

```python
# 加载完整会话
session = session_manager.load_session("session-123")

# 限制加载的消息数量（分页）
session = session_manager.load_session("session-123", max_messages=50)
```

### 6. 列出会话

```python
# 列出所有会话
sessions = session_manager.list_sessions()

# 按 Agent ID 过滤
sessions = session_manager.list_sessions(agent_id="my-agent")
```

### 7. 删除会话

```python
session_manager.delete_session("session-123")
```

---

## Token 管理

### Token 估算

系统使用简化的估算方法：
- **英文**: 约 4 个字符 = 1 token
- **中文**: 约 1.5 个字符 = 1 token

```python
from mul_agent.sessions import estimate_tokens

tokens = estimate_tokens("Hello, 你好")
print(f"Token 数：{tokens}")
```

### Token 阈值

当会话 token 数达到阈值时会触发相应行为：

| 阈值 | 默认值 | 触发行为 |
|------|--------|----------|
| `session_warning` | 8000 | 标记为需要压缩 |
| `session_max` | 16000 | 强制压缩 |
| `bootstrap_warning` | 4000 | 标记为需要压缩 |
| `bootstrap_max` | 8000 | 强制压缩 |
| `compression_target` | 3000 | 压缩后目标 token 数 |

### 获取压缩提示

```python
session = session_manager.load_session("session-123")
hint = session_manager.get_compression_hint(session)

if hint.needs_compression:
    print(f"需要压缩：{hint.compression_type}")
    print(f"原因：{hint.reason}")
    print(f"提示词：{hint.prompt}")
```

---

## 事件监听

SessionManager 支持事件回调：

```python
# 注册事件回调
@session_manager.on_session_created
def on_created(context):
    print(f"新会话创建：{context.id}")

@session_manager.on_session_deleted
def on_deleted(session_id, agent_id):
    print(f"会话删除：{session_id}")
```

---

## 存储结构

会话数据以以下结构存储在文件系统中：

```
storage/sessions/
└── {agent_id}/
    └── {session_id}/
        ├── history.jsonl       # 对话历史 (JSONL 格式)
        ├── bootstrap.json      # Bootstrap 内容 (可选)
        └── context_meta.json   # 元数据
```

### history.jsonl 格式

```jsonl
{"id": "msg-1", "role": "user", "content": "你好", "timestamp": 1234567890.0}
{"id": "msg-2", "role": "assistant", "content": "你好！有什么可以帮助你的？", "timestamp": 1234567891.0}
```

### context_meta.json 格式

```json
{
  "title": "第一次对话",
  "agent_id": "my-agent",
  "session_id": "session-123",
  "token_count": 1500,
  "bootstrap_token_count": 500,
  "needs_compression": false,
  "created_at": 1234567890.0,
  "updated_at": 1234567891.0,
  "message_count": 10
}
```

---

## API 端点

如果使用 FastAPI 服务器，可通过以下 REST API 访问：

### 列出会话
```http
GET /api/sessions
Query: agentId, limit
```

### 获取会话详情
```http
GET /api/sessions/{session_id}
Query: agentId, maxMessages
```

### 创建会话
```http
POST /api/sessions
Body: { sessionId, agentId, title, initialMessages, metadata }
```

### 删除会话
```http
DELETE /api/sessions/{session_id}
Query: agentId
```

### 获取会话历史
```http
GET /api/sessions/{session_id}/history
Query: agentId, limit, includeTools
```

### 添加消息
```http
POST /api/sessions/{session_id}/messages
Body: { role: "user"|"assistant"|"system", content, metadata }
Query: agentId
```

### 更新元数据
```http
PUT /api/sessions/{session_id}/metadata
Body: { title, metadata }
Query: agentId
```

### 获取压缩提示
```http
POST /api/sessions/{session_id}/compress
Query: agentId
```

---

## 最佳实践

### 1. 会话复用

```python
# 检查会话是否存在，不存在则创建
try:
    session = session_manager.load_session("my-session")
except FileNotFoundError:
    session = session_manager.create_session(session_id="my-session")
```

### 2. 分页加载

对于长对话历史，使用分页加载避免内存溢出：

```python
# 只加载最近 50 条消息
session = session_manager.load_session("session-123", max_messages=50)
```

### 3. 定期清理

```python
# 列出所有超过阈值的会话
sessions = session_manager.list_sessions()
for session in sessions:
    if session.needs_compression:
        print(f"会话 {session.id} 需要压缩")
```

### 4. Bootstrap 使用

Bootstrap 用于存储初始设定/上下文：

```python
# 创建时设置
session = session_manager.create_session(
    metadata={
        "bootstrap": {
            "system_prompt": "你是一个 Python 助手",
            "workspace_context": {...}
        }
    }
)

# 更新 Bootstrap
session_manager.update_session_metadata(
    "session-123",
    metadata={
        "bootstrap": {
            "system_prompt": "你是一个全栈开发者助手"
        }
    }
)
```

---

## 常见问题

### Q: 如何迁移会话数据？

会话数据存储在文件系统中，直接复制对应的目录即可迁移：

```bash
cp -r storage/sessions/my-agent/session-123 \
       storage/sessions/my-agent/session-456
```

### Q: 如何合并两个会话？

```python
# 加载两个会话
session1 = session_manager.load_session("session-1")
session2 = session_manager.load_session("session-2")

# 合并消息
merged_messages = session1.messages + session2.messages

# 创建新会话
new_session = session_manager.create_session(
    title="合并的会话",
    initial_messages=merged_messages
)
```

### Q: 如何导出会话为 JSON？

```python
import json

session = session_manager.load_session("session-123")
export_data = {
    "id": session.id,
    "title": session.title,
    "messages": [m.to_dict() for m in session.messages],
    "metadata": session.metadata,
}

with open("session-export.json", "w") as f:
    json.dump(export_data, f, ensure_ascii=False, indent=2)
```

---

## 相关资源

- [Session API 文档](./api/sessions.md)
- [Token 压缩指南](./compression.md)
- [Memory 系统集成](./memory.md)
