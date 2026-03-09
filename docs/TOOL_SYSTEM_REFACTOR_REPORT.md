# 工具系统重构报告 - 按照 Claude 设计原则

## 概述

本次重构将工具系统完全对齐到 **Claude 原生设计原则**，采用 Handler + Router 架构，替代了独立的 ToolRegistry 系统。

## 设计原则对比

### 重构前（独立 ToolRegistry）

```
┌─────────────────┐
│  ToolRegistry   │
│  (独立系统)      │
├─────────────────┤
│ - Tool          │
│ - SyncTool      │
│ - ToolMetadata  │
│ - ToolResult    │
└─────────────────┘
        ↓
┌─────────────────┐
│  Builtins       │
│  - BashTool     │
│  - ReadTool     │
│  - WriteTool    │
│  - EditTool     │
│  - GlobTool     │
│  - GrepTool     │
└─────────────────┘
```

### 重构后（Handler + Router）

```
┌─────────────────────────────────────────┐
│              Brain                      │
├─────────────────────────────────────────┤
│  ┌───────────┐    ┌─────────────────┐  │
│  │   LLM     │    │    Router       │  │
│  │ (路由决策)│───▶│  (统一分发)     │  │
│  └───────────┘    └────┬─────────────┘  │
│                        │                 │
│         ┌──────────────┼──────────────┐ │
│         ▼              ▼              ▼ │
│    ┌────────┐   ┌──────────┐   ┌────────┐│
│    │ Bash   │   │FileEdit  │   │ Glob   ││
│    │Handler │   │ Handler  │   │Handler ││
│    └────────┘   └──────────┘   └────────┘│
│                                          │
└──────────────────────────────────────────┘
```

## 核心变更

### 1. 新增 Handler

| Handler | 路由名 | 功能 |
|---------|--------|------|
| `GlobHandler` | `glob` | 文件名模式匹配 |
| `GrepHandler` | `grep` | 文件内容搜索 |

### 2. 路由系统扩展

**router.py** 核心路由从 5 个扩展到 7 个：

```python
ROUTES = {
    "bash": BashHandler,         # 执行 shell 命令
    "file_edit": FileEditHandler, # 文件编辑（读/写/编辑/插入/删除）
    "glob": GlobHandler,          # 文件名匹配 ⭐ 新增
    "grep": GrepHandler,          # 内容搜索 ⭐ 新增
    "chat": ChatHandler,          # Agent 对话
    "create_user": CreateUserHandler,
    "create_team": CreateTeamHandler,
    "heart": HeartHandler,
}
```

### 3. LLM 路由定义更新

**llm.py** 中 `_get_default_routes()` 添加了新路由定义：

```python
{
    "name": "glob",
    "description": "文件名模式匹配。用于搜索匹配特定模式的文件。",
    "params": {"pattern": "str", "path": "str", "recursive": "bool"},
    "example": '{"route": "glob", "params": {"pattern": "*.py"}}'
},
{
    "name": "grep",
    "description": "文件内容搜索。用于在文件中搜索文本或正则表达式模式。",
    "params": {"pattern": "str", "path": "str", "file_pattern": "str"},
    "example": '{"route": "grep", "params": {"pattern": "TODO"}}'
}
```

### 4. Brain 意图识别增强

**brain.py** 中 `_decide_action()` 添加了对 `glob` 和 `grep` 的规则识别：

```python
# Glob - 文件名匹配
glob_patterns = ["find", "查找文件", "*.py", "*.ts"]
if is_glob:
    return {"route": "glob", "params": {"pattern": pattern}}

# Grep - 内容搜索
grep_keywords = ["grep", "search for", "TODO", "FIXME"]
if is_grep:
    return {"route": "grep", "params": {"pattern": pattern}}
```

### 5. 允许的路由列表更新

```python
# brain.py - 允许 LLM 选择的路由
allowed_routes = [
    "bash", "file_edit",
    "glob", "grep",  # ⭐ 新增
    "chat", "create_user", "create_team"
]
```

## 文件变更清单

### 新增文件
| 文件 | 说明 |
|------|------|
| `mul_agent/brain/handlers/glob.py` | GlobHandler 实现 |
| `mul_agent/brain/handlers/grep.py` | GrepHandler 实现 |
| `tests/test_handlers.py` | 新增测试类（已合并到现有文件） |

### 修改文件
| 文件 | 变更内容 |
|------|----------|
| `mul_agent/brain/handlers/__init__.py` | 导出 GlobHandler, GrepHandler |
| `mul_agent/brain/router.py` | 添加 glob/grep 路由 |
| `mul_agent/brain/llm.py` | 添加 glob/grep 路由定义 |
| `mul_agent/brain/brain.py` | 意图识别添加 glob/grep 规则 |
| `mul_agent/tools/__init__.py` | 简化为仅导出 BashExecutor |
| `mul_agent/tools/builtins/__init__.py` | 移除已迁移到 Handler 的工具 |

### 删除文件
| 文件 | 原因 |
|------|------|
| `mul_agent/tools/base.py` | 独立 Tool 抽象不再需要 |
| `mul_agent/tools/registry.py` | ToolRegistry 不再需要 |
| `mul_agent/tools/mcp_adapter.py` | MCP 适配改为 Handler 方式 |
| `mul_agent/tools/builtins/edit.py` | 功能已合并到 FileEditHandler |
| `mul_agent/tools/builtins/glob.py` | 已迁移到 GlobHandler |
| `mul_agent/tools/builtins/grep.py` | 已迁移到 GrepHandler |

## 使用方式

### 方式 1：直接使用 Router

```python
from mul_agent.brain.router import Router
from mul_agent.brain.config_manager import ConfigManager

config_manager = ConfigManager(storage_dir)
router = Router(config_manager, agent_id="wangyue")

# 执行 glob
result = router.dispatch("glob", {
    "pattern": "*.py",
    "path": "src/"
})

# 执行 grep
result = router.dispatch("grep", {
    "pattern": "TODO",
    "path": "src/"
})
```

### 方式 2：通过 Brain 自主决策

```python
from mul_agent.brain.brain import Brain

brain = Brain("wangyue", config_manager)

# 用户输入会被自动路由到正确的 Handler
result = brain.think("查找所有*.py 文件")
result = brain.think("搜索所有 TODO 注释")
```

### 方式 3：LLM 路由决策

```python
from mul_agent.brain.llm import LLMClient

llm = LLMClient(config)

# LLM 会根据上下文选择正确的路由
result = llm.think_with_routes(
    user_input="找找看有没有 TODO",
    context={},
    allowed_routes=["bash", "glob", "grep", "chat"]
)
# 返回：{"route": "grep", "params": {"pattern": "TODO"}}
```

## 测试覆盖

### 新增测试类

```
tests/test_handlers.py
├── TestGlobHandler (4 个测试)
│   ├── test_handle_glob_py_files
│   ├── test_handle_glob_recursive
│   ├── test_handle_glob_missing_pattern
│   └── test_handle_glob_path_not_found
├── TestGrepHandler (6 个测试)
│   ├── test_handle_grep_simple
│   ├── test_handle_grep_regex
│   ├── test_handle_grep_ignore_case
│   ├── test_handle_grep_with_context
│   ├── test_handle_grep_missing_pattern
│   └── test_handle_grep_invalid_regex
└── TestFileEditHandler (5 个测试)
    ├── test_handle_read_action
    ├── test_handle_create_action
    ├── test_handle_edit_action
    ├── test_handle_insert_action
    └── test_handle_delete_lines_action
```

### 测试结果

```
tests/test_handlers.py - 46 passed in 58.18s
```

## 优势对比

| 特性 | 重构前 (ToolRegistry) | 重构后 (Handler+Router) |
|------|----------------------|------------------------|
| 架构一致性 | ❌ 独立系统 | ✅ 与 Brain/Router 一体 |
| LLM 集成 | ❌ 需要额外适配 | ✅ 原生支持 Function Calling |
| 路由决策 | ❌ 无法被 LLM 使用 | ✅ LLM 可自主选择工具 |
| 意图识别 | ❌ 规则与工具分离 | ✅ 规则直接路由到 Handler |
| 代码复用 | ❌ Handler 和 Tool 重复 | ✅ Handler 即 Tool |
| 测试复杂度 | ❌ 需 mock 多个系统 | ✅ 统一测试架构 |

## Claude 设计原则对齐

### 1. **单一职责原则**
- 每个 Handler 只负责一种功能
- Router 只负责分发，不处理业务逻辑

### 2. **开闭原则**
- 新增工具只需添加新的 Handler
- 无需修改现有代码

### 3. **依赖倒置原则**
- 所有 Handler 继承 `BaseHandler`
- Router 依赖抽象接口，不依赖具体实现

### 4. **LLM 优先设计**
- 路由定义包含 JSON Schema 用于 Function Calling
- 意图识别规则与 LLM 路由决策并存

### 5. **渐进式增强**
- 保留原有 BashHandler, FileEditHandler 等
- 新增 GlobHandler, GrepHandler 无缝集成

## 后续工作

1. **MCP 工具适配** - 创建 MCPHandler 适配 Chrome MCP, Web Search MCP 等
2. **工具组合** - 支持 batch 路由组合多个工具
3. **工具发现** - 动态发现并注册 Handler
4. **权限系统** - 基于配置的 Handler 访问控制

## 总结

重构后的工具系统完全符合 **Claude 原生设计原则**：
- ✅ 工具即 Handler
- ✅ Router 统一分发
- ✅ LLM Function Calling 原生支持
- ✅ 规则路由与 LLM 路由并存
- ✅ 完整的测试覆盖

系统更加简洁、一致、易于扩展。
