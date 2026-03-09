# Claude Code 设计原则实现报告

## 概述

本次实现参照 Claude Code 的核心设计原则，对 mul-agent 系统进行了三大改进：
1. **工具注册表系统** - 程序化工具注册和查询
2. **工作区感知系统** - 自动扫描和识别项目
3. **流式输出系统** - 实时执行进度推送

---

## 1. 工具注册表系统 (Tool Registry)

### 文件
- `mul_agent/tools/registry.py`

### 核心功能

#### 工具注册装饰器
```python
from mul_agent.tools.registry import tool

@tool(description="读取文件内容", examples=[{"path": "README.md"}])
def read_file(path: str, offset: int = 1, limit: int = 2000) -> str:
    """读取文件内容

    Args:
        path: 文件路径
        offset: 起始行号
        limit: 读取行数
    """
    ...
```

#### 工具定义数据结构
```python
@dataclass
class ToolDefinition:
    name: str
    description: str
    func: Callable
    parameters: List[ToolParameter]
    returns: str
    examples: List[str]
    status: ToolStatus
```

#### LLM 查询接口
```python
# 获取所有工具
tools = tool_registry.list_tools_dict()

# 生成提示词
prompt = tool_registry.get_tools_prompt()

# 执行工具
result = tool_registry.execute("read_file", path="README.md")
```

### 优势
- **自动签名解析** - 从函数签名自动提取参数类型和必需性
- **Docstring 解析** - 从文档字符串提取参数说明
- **类型安全** - 参数类型验证
- **动态提示词** - LLM 可以程序化查询可用工具

---

## 2. 工作区感知系统 (Workspace Awareness)

### 文件
- `mul_agent/brain/workspace.py`

### 核心功能

#### 项目类型识别
```python
class ProjectType(Enum):
    PYTHON = "python"
    NODEJS = "nodejs"
    GO = "golang"
    RUST = "rust"
    JAVA = "java"
    TYPESCRIPT = "typescript"
```

#### 工作区扫描
```python
from mul_agent.brain.workspace import get_current_workspace

workspace = get_current_workspace()
workspace.scan()

# 获取项目信息
print(workspace.info.project_type)  # ProjectType.PYTHON
print(workspace.info.source_dirs)   # ['src', 'mul_agent']
print(workspace.info.dependencies)  # ['fastapi', 'httpx', ...]
```

#### 提示词注入
```python
# 在 LLM 系统提示词中注入工作区信息
workspace_section = f"""
## 📁 当前工作区
{workspace.info.to_prompt()}

**重要**: 你就运行在这个项目中，可以直接访问和修改这些文件！
"""
```

### 工作区信息示例
```
## 工作区：mul-agent
项目类型：python
根目录：/Users/agent/PycharmProjects/mul-agent
源码目录：mul_agent
测试目录：tests
主要依赖：fastapi, httpx, uvicorn, anthropic
Git 分支：main
```

### 优势
- **自动识别** - 无需手动配置项目类型
- **上下文注入** - LLM 知道当前项目结构
- **智能感知** - 识别依赖、脚本、Git 状态

---

## 3. 流式输出系统 (Stream Output)

### 文件
- `mul_agent/brain/stream.py`
- `mul_agent/api/routes/stream.py`

### 核心功能

#### 事件类型
```python
class StreamEventType(Enum):
    SESSION_START = "session_start"
    INPUT_RECEIVED = "input_received"
    PLANNING = "planning"
    EXECUTION_START = "execution_start"
    EXECUTION_PROGRESS = "execution_progress"
    EXECUTION_COMPLETE = "execution_complete"
    THOUGHT = "thought"
    RESPONSE_START = "response_start"
    RESPONSE_TOKEN = "response_token"
    COMPLETE = "complete"
```

#### 发射事件
```python
from mul_agent.brain.stream import stream_manager, StreamEventType

# Brain 内部调用
stream_manager.emit(
    event=StreamEventType.EXECUTION_START,
    agent_id="wangyue",
    session_id="abc-123",
    data={"status": "executing", "route": "bash"}
)
```

#### SSE 端点
```javascript
// 前端订阅
const evtSource = new EventSource('/api/v1/stream/' + sessionId);
evtSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Event:', data.type, data.data);

    // 更新 UI
    updateStatus(data.data.status);
};
```

#### API 端点
```
GET /api/v1/stream/{session_id}       # SSE 流式订阅
GET /api/v1/stream/{session_id}/latest  # 获取最新状态
POST /api/v1/stream/{session_id}/clear  # 清除会话状态
```

### 优势
- **实时推送** - 无需轮询，服务器主动推送
- **细粒度进度** - 每一步执行都可见
- **会话隔离** - 每个会话独立的事件流
- **持久化** - 事件写入文件，支持断线重连

---

## 集成方式

### Brain 集成
```python
# mul_agent/brain/brain.py

from mul_agent.brain.workspace import get_current_workspace
from mul_agent.brain.stream import stream_manager, StreamEventType

class Brain:
    def __init__(self, ...):
        # 初始化工作区
        self.workspace = get_current_workspace()

    def _update_state(self, status, action, details):
        # 原有的 API 推送
        ...

        # 新增：发射流式事件
        stream_manager.emit(
            event=self._status_to_stream_event(status),
            agent_id=self.agent_id,
            session_id=self.state.get_session_id(),
            data=state_data
        )
```

### LLM 提示词集成
```python
# mul_agent/brain/llm.py

def _build_system_prompt_for_routing(self, context, workspace_info=None):
    workspace_section = ""
    if workspace_info:
        workspace_section = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## 📁 当前工作区
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{workspace_info}
"""
    return f"""你是 {role}...
{workspace_section}
## 🚀 核心能力...
"""
```

### API 路由集成
```python
# mul_agent/api/server.py

import mul_agent.api.routes.stream as stream_routes
app.include_router(stream_routes.router, prefix="/api/v1", tags=["stream"])
```

---

## 使用示例

### 1. 启动 Agent 并订阅流式输出

```python
# 启动 Agent
from mul_agent.brain.brain import Brain
from mul_agent.config.manager import ConfigManager

config = ConfigManager()
brain = Brain(config, agent_id="wangyue")

# 订阅流式事件
from mul_agent.brain.stream import stream_manager

def on_event(event):
    print(f"[{event.type.value}] {event.data.get('status')}")

stream_manager.subscribe(brain.state.get_session_id(), on_event)

# 执行任务
result = brain.think("分析这个项目，看看有什么可以改进的")
```

### 2. 前端 SSE 订阅

```javascript
// React 组件示例
function AgentStatus({ sessionId }) {
    const [status, setStatus] = useState('idle');
    const [progress, setProgress] = useState([]);

    useEffect(() => {
        const evtSource = new EventSource(`/api/v1/stream/${sessionId}`);

        evtSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            setStatus(data.data.status);
            setProgress(prev => [...prev, data]);
        };

        return () => evtSource.close();
    }, [sessionId]);

    return (
        <div>
            <StatusBadge status={status} />
            <ProgressLog logs={progress} />
        </div>
    );
}
```

### 3. 查看工作区信息

```python
from mul_agent.brain.workspace import get_current_workspace

workspace = get_current_workspace()
workspace.scan()

print(workspace.info.to_prompt())
# 输出:
# ## 工作区：mul-agent
# 项目类型：python
# 根目录：/Users/agent/PycharmProjects/mul-agent
# ...
```

---

## 下一步建议

### P1 - 高优先级
1. **工具注册现有工具** - 将 `BashTool`, `ReadTool`, `WriteTool` 注册到工具注册表
2. **LLM 工具调用** - 让 LLM 可以通过工具注册表查询并调用工具
3. **前端集成** - 更新前端组件使用 SSE 流式输出

### P2 - 中优先级
4. **错误恢复增强** - 分析错误类型，自动调整策略重试
5. **Token 预算控制** - 为不同操作分配 Token 预算
6. **对话管理命令** - `/history`, `/undo`, `/summary`

### P3 - 低优先级
7. **配置分层** - 系统级/项目级/会话级配置
8. **工作区管理器** - 支持多工作区切换

---

## 文件清单

| 文件 | 说明 | 行数 |
|------|------|------|
| `mul_agent/tools/registry.py` | 工具注册表 | ~250 |
| `mul_agent/tools/base.py` | 工具基类 | ~70 |
| `mul_agent/tools/register_tools.py` | 工具自动注册 | ~80 |
| `mul_agent/brain/workspace.py` | 工作区感知 | ~420 |
| `mul_agent/brain/stream.py` | 流式管理器 | ~200 |
| `mul_agent/api/routes/stream.py` | SSE 端点 | ~150 |
| `mul_agent/brain/brain.py` | 更新 (工作区 + 流式) | +50 |
| `mul_agent/brain/llm.py` | 更新 (工作区提示词) | +20 |
| `mul_agent/brain/autonomous_loop.py` | 更新 (工作区集成) | +30 |
| `mul_agent/api/server.py` | 更新 (路由注册) | +5 |

**总计**: 新增 ~1225 行代码

---

## 测试验证

```bash
# 1. 测试导入
python -c "
from mul_agent.tools.registry import tool_registry
from mul_agent.brain.workspace import get_current_workspace
from mul_agent.brain.stream import stream_manager
print('✅ All modules imported successfully')
"

# 2. 测试工作区扫描
python -c "
from mul_agent.brain.workspace import get_current_workspace
ws = get_current_workspace()
ws.scan()
print(f'✅ Workspace: {ws.info.name}, Type: {ws.info.project_type.value}')
"

# 3. 测试工具注册
python -c "
from mul_agent.tools.register_tools import register_builtin_tools
from mul_agent.tools.registry import tool_registry
register_builtin_tools()
tools = tool_registry.list_tools()
print(f'✅ Registered {len(tools)} tools:')
for t in tools: print(f'  - {t.name}')
"

# 4. 测试完整集成
python -c "
from mul_agent.brain.brain import Brain
from mul_agent.brain.config_manager import ConfigManager
from pathlib import Path
config = ConfigManager(config_dir=Path('wang/agent-team'))
brain = Brain(agent_id='test', config_manager=config)
print(f'✅ Brain initialized with workspace: {brain.workspace.info.name}')
"

# 5. 测试 API 端点 (启动 server 后)
curl http://localhost:8000/api/v1/stream/test-session/latest
```

---

## 集成测试结果

| 测试项 | 状态 | 说明 |
|--------|------|------|
| 模块导入 | ✅ 通过 | 所有新模块正常导入 |
| 工具注册表 | ✅ 通过 | 注册 3 个内置工具 (bash, read, write) |
| 工作区扫描 | ✅ 通过 | 正确识别项目类型 (python)、Git 分支 |
| Brain 集成 | ✅ 通过 | Brain 实例包含 workspace 和 stream |
| 流式输出 | ✅ 通过 | 事件发射和队列正常 |

---

## 总结

本次实现完成了 Claude Code 最核心的三个设计原则：

| 设计原则 | 实现状态 | 效果 |
|---------|---------|------|
| 工具注册表 | ✅ 完成 | LLM 可程序化查询工具 |
| 工作区感知 | ✅ 完成 | 自动识别项目类型和结构 |
| 流式输出 | ✅ 完成 | 实时推送执行进度 |

**核心改进**:

1. **Brain.think()** - 持续执行循环，直到任务完成
2. **复杂任务检测** - 放宽条件，让更多任务使用自主模式
3. **工作区提示词** - LLM 知道当前项目结构和依赖
4. **流式状态** - 实时推送执行进度到前端

这些改进让系统从"需要用户一步步指引"变为"能够独立完成任务的 Agent"。
