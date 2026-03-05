# Architecture Design - 详细架构设计

> 版本: v1.0 (Wang Brain)
> 最后更新: 2026-03-05

## 1. 系统分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                        │
│                    (CLI / REPL Interface)                       │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│   │ main.py     │  │ Click CLI   │  │ Daemon      │           │
│   │ (入口)      │  │ (命令)      │  │ (守护进程)  │           │
│   └─────────────┘  └─────────────┘  └─────────────┘           │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                       Agent Core Layer                           │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│   │ Brain       │  │ Router      │  │ LLM Client  │           │
│   │ (大脑)      │  │ (路由)      │  │ (LLM调用)  │           │
│   └─────────────┘  └─────────────┘  └─────────────┘           │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│   │ Config      │  │ Memory      │  │ Context     │           │
│   │ Manager     │  │ Manager     │  │ Builder     │           │
│   └─────────────┘  └─────────────┘  └─────────────┘           │
│   ┌─────────────┐  ┌─────────────┐                             │
│   │ Handlers    │  │ Daemon      │                             │
│   │ (处理器)    │  │ (守护进程)  │                             │
│   └─────────────┘  └─────────────┘                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      Tool Layer                                  │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│   │ Bash        │  │ Chrome MCP  │  │ Web Search  │           │
│   │ Executor    │  │ (浏览器)    │  │ MCP         │           │
│   └─────────────┘  └─────────────┘  └─────────────┘           │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      Storage Layer                               │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │
│   │ agents/     │  │ memory/     │  │ snapshots/  │           │
│   │ (.md配置)   │  │ (记忆文件)  │  │ (版本快照)  │           │
│   └─────────────┘  └─────────────┘  └─────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 核心模块设计

### 2.1 Brain (大脑)

```python
class Brain:
    """核心大脑 - 自主决策中心"""

    def __init__(self, config_path: str):
        self.soul = load_md("soul.md")      # 灵魂配置
        self.user = load_md("user.md")       # 用户配置
        self.skill = load_md("skill.md")    # 技能配置

    def think(self, context: dict) -> Action:
        """思考并决定下一步行动"""
        pass

    def evolve(self):
        """自我进化 - 修改自身配置"""
        pass

    def create_agent(self, config: dict):
        """创建新Agent成员"""
        pass
```

> **注意**: 配置文件使用 Markdown (.md) 格式，存储在 `storage/agents/{agent_id}/` 目录下

### 2.2 Router (路由)

```python
class Router:
    """路由分发器"""
    
    ROUTES = {
        "create_user": CreateUserHandler,
        "bash": BashHandler,
        "heart": HeartHandler,
        "memory": MemoryHandler,
    }
    
    def dispatch(self, route: str, params: dict):
        """根据路由名分发到对应处理器"""
        pass
```

### 2.3 Tool Manager (工具管理器)

```python
class ToolManager:
    """外部能力管理器"""
    
    def __init__(self, user_config: dict):
        self.enabled_tools = user_config.get("tools", [])
        
    def execute(self, tool_name: str, params: dict):
        """执行工具"""
        pass
        
    def list_tools(self):
        """列出可用工具"""
        pass
```

### 2.4 Memory System (记忆系统)

```python
class Memory:
    """记忆管理系统"""
    
    def __init__(self, base_path: str):
        self.short_term_path = f"{base_path}/short_term"
        self.long_term_path = f"{base_path}/long_term"
        self.handover_path = f"{base_path}/handover"
        
    def read(self, memory_type: str, agent_id: str):
        """读取记忆"""
        pass
        
    def write(self, memory_type: str, agent_id: str, content: dict):
        """写入记忆"""
        pass
        
    def create_handover(self, from_agent: str, to_agent: str, content: dict):
        """创建交接文档"""
        pass
```

---

## 3. 配置文件关系图

```
                    ┌─────────────┐
                    │  soul.md    │
                    │  (灵魂/核心) │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐
     │ user.md     │ │skill.md  │ │memory.md  │
     │ (用户/角色) │ │ (技能)    │ │ (记忆配置) │
     └─────────────┘ └───────────┘ └───────────┘
```

> **重要**: 配置文件使用 Markdown (.md) 格式，详情见 [CONFIG_SPEC.md](CONFIG_SPEC.md)

---

## 4. 数据流

### 4.1 基础请求流程

```
User Input
    │
    ▼
CLI Entry (main.py)
    │
    ▼
Router.dispatch(route, params)
    │
    ├──► Brain.think() ──► ToolManager.execute()
    │                          │
    │                          ▼
    │                     External Tool
    │                          │
    │                          ▼
    │                     Tool Result
    │                          │
    ▼                          ▼
Memory.write() ◄──────────────┘
    │
    ▼
Response to User
```

### 4.2 自我进化流程

```
Brain.heart() (自省)
    │
    ▼
分析当前状态
    │
    ├──► 读取配置文件
    │
    ├──► 评估需要修改的点
    │
    ├──► 生成修改方案
    │
    ├──► 执行修改 (热重载)
    │
    └──► 记录版本快照
```

---

## 5. 目录结构

```
mul-agent/
├── main.py                 # CLI入口
├── mul_agent/              # 核心代码包
│   ├── __init__.py
│   ├── brain/              # 大脑模块
│   │   ├── __init__.py
│   │   ├── brain.py       # 核心大脑类
│   │   ├── router.py      # 路由分发
│   │   ├── handlers.py    # 处理器 (CreateUserHandler, BashHandler, etc.)
│   │   ├── config_manager.py  # 配置管理器
│   │   ├── llm.py         # LLM客户端
│   │   ├── context_builder.py # 上下文构建
│   │   └── daemon.py      # 守护进程
│   ├── tools/             # 工具层
│   │   ├── __init__.py
│   │   ├── bash_executor.py   # Bash执行器
│   │   └── mcp_tools.py       # MCP工具集成
│   └── memory/            # 记忆系统
│       ├── __init__.py
│       └── memory.py      # 记忆管理
├── storage/                # 存储层
│   ├── agents/            # Agent配置文件 (.md格式)
│   │   └── {agent_id}/
│   │       ├── soul.md
│   │       ├── user.md
│   │       ├── skill.md
│   │       └── memory.md
│   ├── memory/            # 记忆文件
│   │   ├── short_term/
│   │   ├── long_term/
│   │   └── handover/
│   └── snapshots/         # 版本快照
├── tests/                  # 测试
│   ├── test_router.py
│   ├── test_bash_executor.py
│   ├── test_config_manager.py
│   └── test_daemon.py
└── docs/                   # 文档
    ├── README.md
    ├── ARCHITECTURE.md
    ├── CONFIG_SPEC.md
    ├── API.md
    └── IMPLEMENTATION.md
```

---

## 6. 安全机制

虽然具体规则由配置定义，但代码层提供基础安全底线：

| 机制 | 说明 |
|------|------|
| 版本快照 | 每次修改前自动备份 |
| 配置校验 | JSON Schema验证 |
| 沙箱执行 | 危险命令隔离执行 |
| 日志记录 | 所有操作可追溯 |

---

## 7. 模块依赖关系

```
┌─────────────────────────────────────────────────────────────────┐
│                        main.py (入口)                           │
└─────────────────────────────┬───────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
        ┌─────────┐    ┌──────────┐    ┌─────────┐
        │ Brain   │    │ Daemon   │    │ Router  │
        └────┬────┘    └────┬─────┘    └────┬────┘
             │               │               │
    ┌────────┼────────┐     │        ┌──────┴──────┐
    ▼        ▼        ▼     │        ▼             ▼
 ┌──────┐ ┌─────┐ ┌──────┐ │   ┌─────────┐  ┌─────────┐
 │Config│ │LLM  │ │Memory│ │   │Handler  │  │ToolMgr  │
 │Manager│ │Client│ │      │ │   │(s)     │  │         │
 └──┬───┘ └──┬──┘ └───┬──┘ │   └────┬────┘  └───┬─────┘
    │       │        │     │         │            │
    └───────┴────────┴─────┴─────────┴────────────┘
    │       │        │              │
    ▼       ▼        ▼              ▼
 ┌─────────────────────────────────────────────┐
 │              Storage Layer                   │
 │   (agents/.md, memory/, snapshots/)         │
 └─────────────────────────────────────────────┘
```

### 依赖说明

| 模块 | 依赖 | 被依赖 |
|------|------|--------|
| Brain | ConfigManager, LLM, Memory | main.py, Router |
| Router | Handlers, Brain | main.py |
| ConfigManager | Storage | Brain, Handlers |
| LLM | - | Brain |
| Memory | Storage | Brain, Handlers |
| Handlers | ToolManager, Memory, ConfigManager | Router |
| ToolManager | MCP Tools | Handlers |

---

## 8. 错误处理机制

### 8.1 错误分类

| 错误类型 | 处理方式 | 示例 |
|----------|----------|------|
| 配置错误 | 加载时校验，错误则终止启动 | 缺少必需字段 |
| 执行错误 | 捕获异常，记录日志，返回错误信息 | 命令执行失败 |
| LLM错误 | 重试机制，降级处理 | API超时 |
| 记忆错误 | 回退到默认策略 | 文件写入失败 |

### 8.2 错误处理流程

```
错误发生
    │
    ▼
┌─────────────┐
│ 捕获异常     │ ──► 记录详细日志
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 判断错误类型 │
└──────┬──────┘
       │
       ├── 配置错误 ──► 终止并提示用户
       │
       ├── 执行错误 ──► 返回错误信息给调用者
       │
       ├── LLM错误 ──► 重试3次，失败则降级
       │
       └── 记忆错误 ──► 使用默认策略继续
```

---

## 9. 性能考虑

### 9.1 关键性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 启动时间 | < 2秒 | 冷启动配置加载 |
| 响应延迟 | < 500ms | 不含LLM调用的处理时间 |
| 内存使用 | < 200MB | 基础运行内存 |
| 并发数 | 1 (当前) | 守护进程模式支持 |

### 9.2 优化策略

1. **配置缓存**: 配置加载后缓存在内存中
2. **按需加载**: 配置文件采用延迟加载策略
3. **版本快照异步**: 快照创建使用异步IO
4. **上下文压缩**: 大上下文自动压缩 (见 `compressor.py`)

### 9.3 已知限制

- 当前不支持高并发请求
- 大规模记忆文件可能影响读取性能
- LLM调用是主要延迟来源

---

## 10. 监控与日志

### 10.1 日志结构

```
storage/logs/
├── {date}.log           # 每日日志
├── error_{date}.log     # 错误日志
└── audit_{date}.log      # 审计日志 (重要操作)
```

### 10.2 日志级别

| 级别 | 用途 |
|------|------|
| DEBUG | 调试信息，详细执行步骤 |
| INFO | 正常业务流程 |
| WARNING | 可恢复的异常 |
| ERROR | 执行失败 |
| CRITICAL | 系统级错误 |

### 10.3 关键事件记录

- Agent创建/销毁
- 配置修改
- 进化操作
- 异常错误

---

## 11. 测试策略

### 11.1 测试分层

| 测试类型 | 位置 | 覆盖率目标 |
|----------|------|------------|
| 单元测试 | tests/ | 80%+ |
| 集成测试 | tests/integration/ | 关键路径 |
| E2E测试 | tests/e2e/ | 核心流程 |

### 11.2 核心测试用例

- Router路由分发
- ConfigManager配置加载/保存
- BashExecutor命令执行
- Memory读写操作
- Daemon状态切换

---

## 12. 扩展性

系统设计支持以下扩展：

1. **新增路由**: 在Router中注册新Handler
2. **新增工具**: 在ToolManager中添加新工具类
3. **新增配置**: 在storage/agents/中添加新.md文件
4. **MCP集成**: 保持现有MCP工具的兼容性

### 12.1 新增Handler示例

```python
# 在 handlers.py 中添加
class NewHandler(BaseHandler):
    def handle(self, params: dict) -> Response:
        # 实现处理逻辑
        pass

# 在 router.py 中注册
ROUTES = {
    # ...existing routes
    "new_route": NewHandler,
}
```

### 12.2 新增工具示例

```python
# 在 mcp_tools.py 中添加
class NewTool:
    name = "new_tool"
    async def execute(self, params: dict):
        pass
```

---

## 13. 部署指南

### 13.1 环境要求

- Python 3.10+
- Anthropic API Key
- 依赖: requirements.txt

### 13.2 目录权限

```
storage/          # 需要读写权限
├── agents/       # Agent配置
├── memory/       # 记忆存储
├── snapshots/    # 版本快照
└── logs/         # 日志
```

### 13.3 配置示例

```bash
# 环境变量
export ANTHROPIC_API_KEY="sk-..."
export STORAGE_PATH="./storage"
export LOG_LEVEL="INFO"
```
