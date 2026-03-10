# Session API 集成指南

> 如何将 Session 系统集成到你的 FastAPI 应用中

---

## 快速开始

### 1. 导入依赖

```python
from fastapi import FastAPI
from mul_agent.sessions import SessionManager
from mul_agent.api.routes.sessions import create_session_router
```

### 2. 创建应用

```python
app = FastAPI(
    title="Mul-Agent Session API",
    description="会话管理 API",
    version="1.0.0"
)

# 创建 SessionManager 实例
session_manager = SessionManager(
    storage_path="storage/sessions",
    default_agent_id="default",
)

# 注册路由
app.include_router(
    create_session_router(session_manager),
    prefix="/api",
)
```

### 3. 启动服务器

```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## API 端点

### GET /api/sessions

列出所有会话

**请求参数:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| agentId | string | 否 | 按 Agent ID 过滤 |
| limit | integer | 否 | 返回数量限制 |

**响应示例:**
```json
{
  "success": true,
  "data": [
    {
      "id": "session-123",
      "agentId": "default",
      "title": "第一次对话",
      "createdAt": 1234567890.0,
      "updatedAt": 1234567891.0,
      "tokenCount": 1500,
      "messageCount": 10,
      "needsCompression": false
    }
  ]
}
```

---

### GET /api/sessions/{session_id}

获取会话详情

**路径参数:**
| 参数 | 类型 | 说明 |
|------|------|------|
| session_id | string | 会话 ID |

**查询参数:**
| 参数 | 类型 | 说明 |
|------|------|------|
| agentId | string | Agent ID |
| maxMessages | integer | 最大消息数 |

**响应示例:**
```json
{
  "success": true,
  "data": {
    "id": "session-123",
    "agentId": "default",
    "title": "第一次对话",
    "messages": [
      {
        "id": "msg-1",
        "role": "user",
        "content": "你好",
        "timestamp": 1234567890.0
      }
    ],
    "tokenCount": 1500,
    "needsCompression": false
  }
}
```

---

### POST /api/sessions

创建新会话

**请求体:**
```json
{
  "sessionId": "my-session",
  "agentId": "default",
  "title": "新会话",
  "initialMessages": [
    {
      "role": "user",
      "content": "你好"
    }
  ],
  "metadata": {
    "bootstrap": {
      "system_prompt": "你是一个助手"
    }
  }
}
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "id": "my-session",
    "agentId": "default",
    "title": "新会话",
    "messages": [...],
    "tokenCount": 50
  }
}
```

---

### DELETE /api/sessions/{session_id}

删除会话

**响应示例:**
```json
{
  "success": true,
  "data": {
    "deleted": true,
    "sessionId": "session-123"
  }
}
```

---

### GET /api/sessions/{session_id}/history

获取会话历史

**查询参数:**
| 参数 | 类型 | 说明 |
|------|------|------|
| agentId | string | Agent ID |
| limit | integer | 消息数量限制 |
| includeTools | boolean | 是否包含工具消息 |

**响应示例:**
```json
{
  "success": true,
  "data": {
    "sessionId": "session-123",
    "messages": [
      {"id": "msg-1", "role": "user", "content": "你好", ...}
    ],
    "totalCount": 10,
    "tokenCount": 1500
  }
}
```

---

### POST /api/sessions/{session_id}/messages

添加消息到会话

**请求体:**
```json
{
  "role": "user",
  "content": "请帮我分析这段代码",
  "metadata": {
    "source": "web"
  }
}
```

**响应示例:**
```json
{
  "success": true,
  "data": {
    "sessionId": "session-123",
    "messageCount": 11,
    "tokenCount": 1600,
    "needsCompression": false,
    "compressionReason": null
  }
}
```

---

### PUT /api/sessions/{session_id}/metadata

更新会话元数据

**请求体:**
```json
{
  "title": "新标题",
  "metadata": {
    "key": "value"
  }
}
```

---

### POST /api/sessions/{session_id}/compress

获取压缩提示

**响应示例:**
```json
{
  "success": true,
  "data": {
    "needsCompression": true,
    "type": "session",
    "currentTokens": {
      "session": 8500,
      "bootstrap": 500
    },
    "targetTokens": 3000,
    "reason": "Session tokens (8500) approaching max",
    "prompt": "【压缩请求】会话内容接近 token 上限..."
  }
}
```

---

## 完整示例

```python
from fastapi import FastAPI, HTTPException
from mul_agent.sessions import SessionManager
from mul_agent.api.routes.sessions import create_session_router
import uvicorn

app = FastAPI(
    title="Mul-Agent Session API",
    description="会话管理 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 创建 SessionManager
session_manager = SessionManager(
    storage_path="storage/sessions",
    default_agent_id="default",
)

# 注册路由
app.include_router(
    create_session_router(session_manager),
    prefix="/api",
)

# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "mul-agent-session-api"}

# 事件监听
@session_manager.on_session_created
def on_session_created(ctx):
    print(f"新会话创建：{ctx.id}")

@session_manager.on_session_deleted
def on_session_deleted(session_id, agent_id):
    print(f"会话删除：{session_id}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 使用示例

### curl 示例

```bash
# 创建会话
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"title": "第一次对话"}'

# 列出会话
curl http://localhost:8000/api/sessions

# 获取会话详情
curl http://localhost:8000/api/sessions/{session_id}

# 添加消息
curl -X POST http://localhost:8000/api/sessions/{session_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"role": "user", "content": "你好"}'

# 获取压缩提示
curl -X POST http://localhost:8000/api/sessions/{session_id}/compress

# 删除会话
curl -X DELETE http://localhost:8000/api/sessions/{session_id}
```

### Python 示例

```python
import httpx

BASE_URL = "http://localhost:8000/api"

# 创建会话
with httpx.Client() as client:
    response = client.post(
        f"{BASE_URL}/sessions",
        json={"title": "测试会话"}
    )
    session = response.json()["data"]
    session_id = session["id"]

    # 添加消息
    client.post(
        f"{BASE_URL}/sessions/{session_id}/messages",
        json={"role": "user", "content": "你好"}
    )

    # 获取历史
    response = client.get(f"{BASE_URL}/sessions/{session_id}/history")
    history = response.json()["data"]
    print(f"消息数：{history['totalCount']}")
```

---

## 配置选项

### SessionManager 配置

```python
session_manager = SessionManager(
    storage_path="storage/sessions",      # 存储路径
    default_agent_id="default",           # 默认 Agent ID
    thresholds=TokenThreshold(
        session_warning=8000,             # Session 警告阈值
        session_max=16000,                # Session 最大阈值
        bootstrap_warning=4000,           # Bootstrap 警告阈值
        bootstrap_max=8000,               # Bootstrap 最大阈值
        compression_target=3000,          # 压缩后目标 token 数
    )
)
```

### 环境变量

```bash
# 存储路径
export MUL_AGENT_STORAGE_PATH="storage/sessions"

# 默认 Agent ID
export MUL_AGENT_DEFAULT_AGENT_ID="my-agent"

# Token 阈值
export MUL_AGENT_SESSION_WARNING=8000
export MUL_AGENT_SESSION_MAX=16000
```

---

## 安全建议

### 1. 添加认证

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(
    creds: HTTPAuthorizationCredentials = Depends(security)
):
    expected = os.getenv("API_TOKEN")
    if creds.credentials != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    return True

# 应用到路由
app.include_router(
    create_session_router(session_manager),
    prefix="/api",
    dependencies=[Depends(verify_token)]
)
```

### 2. 速率限制

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# 应用到端点
@app.post("/api/sessions")
@limiter.limit("10/minute")
async def create_session(...):
    ...
```

### 3. 数据加密

```python
from cryptography.fernet import Fernet

# 加密敏感数据
key = Fernet.generate_key()
cipher = Fernet(key)

encrypted = cipher.encrypt(b"sensitive data")
decrypted = cipher.decrypt(encrypted)
```

---

## 故障排除

### 会话无法加载

检查存储路径权限：
```bash
ls -la storage/sessions
chmod 755 storage/sessions
```

### Token 计数不准确

Token 估算是近似的，如需精确计数请使用实际的 LLM Tokenizer。

### 压缩提示未触发

检查 Token 阈值配置是否合理，确保会话 token 数达到阈值。

---

## 相关资源

- [Session 使用指南](../sessions/README.md)
- [Token 压缩指南](./compression.md)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
