# 工具系统实现报告

> 参照 OpenClaw tool kit 架构完成

## 概述

本报告总结了参照 OpenClaw tool kit 架构完成的 mul-agent 工具系统迁移工作。

## 完成的工作

### 1. 核心工具基类 (`mul_agent/tools/base.py`)

增强了工具基类，参照 OpenClaw 设计：

- **SyncTool / AsyncTool**: 同步和异步工具基类
- **ToolMetadata**: 工具元数据，包含名称、描述、输入 schema、示例、门控条件
- **ToolResult**: 工具执行结果，支持结构化输出和媒体内容
- **ToolGate**: 工具门控条件（bins, env, config, os）
- **ToolInputError / ToolAuthorizationError**: 工具错误类型

关键特性：
- 统一的 `execute` 入口方法
- 内置前置检查和后置处理
- 门控条件自动检查
- Owner-only 工具支持
- 沙箱安全标记

### 2. 工具策略系统 (`mul_agent/tools/policy.py`)

参照 OpenClaw 的工具策略设计：

- **ToolPolicy**: 工具策略类
  - Profile 支持：minimal, coding, messaging, full
  - Allow/Deny 列表
  - 工具组支持（group:*）
  - Also-allow 额外允许

- **ToolGroup**: 工具组枚举
  - `group:runtime`: exec, bash, process
  - `group:fs`: read, write, edit, glob
  - `group:sessions`: sessions_list, sessions_history, sessions_send
  - `group:memory`: memory_search, memory_get
  - `group:web`: web_search, web_fetch
  - `group:ui`: browser, canvas
  - `group:code`: glob, grep, git

- **AgentToolPolicy**: Per-Agent 工具策略
  - Provider-specific 策略
  - Sandbox 策略

### 3. 工具管理器 (`mul_agent/tools/manager.py`)

参照 OpenClaw 的 `createOpenClawTools` 设计：

- **ToolContext**: 工具执行上下文
- **ToolManager**: 工具管理器
  - 注册和注销工具
  - 懒加载工具实例
  - 策略过滤
  - 门控检查
  - 工具执行

- **create_tool_manager**: 便捷创建函数

### 4. 技能系统 (`mul_agent/skills/manager.py`)

参照 OpenClaw 的技能系统设计：

- **SkillMetadata**: 技能元数据（解析 SKILL.md frontmatter）
- **SkillInstaller**: 技能安装器配置
- **Skill**: 技能类
- **SkillManager**: 技能管理器
  - 扫描技能目录
  - 门控检查
  - 技能过滤
  - 提示词生成

### 5. 内置工具更新

- **BashTool** (`mul_agent/tools/builtins/bash.py`): 增强了门控支持
- **ReadTool / WriteTool / EditTool**: 文件操作工具
- **FileEditTool**: 支持 search/replace 模式

### 6. 工具示例 (`mul_agent/tools/examples.py`)

提供了完整的工具开发示例：

- **HelloTool**: 简单的同步工具
- **WeatherTool**: 带门控条件的工具
- **HttpFetchTool**: 异步工具
- **GitStatusTool**: 需要二进制文件的工具
- **AdminOnlyTool**: owner-only 工具

### 7. 文档

- **docs/TOOL_SYSTEM_GUIDE.md**: 完整的工具系统使用指南
  - 快速开始
  - 工具策略
  - 工具组
  - 开发自定义工具
  - 工具门控
  - 故障排查

## 架构对比

| 组件 | OpenClaw | mul-agent (新) |
|------|----------|----------------|
| 工具基类 | AgentTool | SyncTool / AsyncTool |
| 工具结果 | AgentToolResult | ToolResult |
| 工具策略 | ToolPolicy | ToolPolicy |
| 工具组 | group:* | ToolGroup |
| 工具管理 | createOpenClawTools | ToolManager |
| 技能格式 | SKILL.md | SKILL.md (兼容) |
| 技能管理 | SkillManager | SkillManager |

## 使用示例

### 基础使用

```python
from mul_agent.tools import ToolManager, ToolContext, ToolPolicy

# 创建上下文和策略
context = ToolContext(agent_id="wangyue", workspace_dir=".")
policy = ToolPolicy.from_profile("coding")

# 创建管理器
manager = ToolManager(context, policy)

# 执行工具
result = manager.execute("bash", command="ls -la")
print(result.to_dict())
```

### 开发自定义工具

```python
from mul_agent.tools.base import SyncTool, ToolMetadata, ToolResult, ToolGate

class MyTool(SyncTool):
    metadata = ToolMetadata(
        name="my_tool",
        description="我的工具",
        input_schema={...},
        gate=ToolGate(bins=["git"], env=["API_KEY"]),
    )

    def execute_sync(self, **kwargs) -> ToolResult:
        # 实现逻辑
        return ToolResult.success(data={...})
```

## 迁移兼容性

新工具系统设计为向后兼容：

- 旧工具类（如 GitDiffTool）可以正常工作
- 管理器自动检测工具类型
- 不支持 check_gate 的工具会被跳过门控检查
- 不支持 to_registry_definition 的工具会生成基本元数据

## 下一步工作

1. **迁移更多工具**: 将现有的 Handler 迁移到新工具架构
2. **添加更多内置工具**: 参照 OpenClaw 的工具列表
3. **技能市场集成**: 实现 ClawHub 类似的技能注册表
4. **工具测试套件**: 添加单元测试
5. **文档完善**: 添加更多使用示例和最佳实践

## 文件清单

### 新增文件

- `mul_agent/tools/base.py` (增强)
- `mul_agent/tools/policy.py` (新增)
- `mul_agent/tools/manager.py` (新增)
- `mul_agent/tools/examples.py` (新增)
- `mul_agent/skills/manager.py` (新增)
- `docs/TOOL_SYSTEM_GUIDE.md` (新增)
- `docs/TOOL_SYSTEM_IMPLEMENTATION.md` (本文件)

### 修改文件

- `mul_agent/tools/__init__.py`
- `mul_agent/tools/builtins/__init__.py`
- `mul_agent/tools/builtins/bash.py`

## 测试验证

运行测试：

```bash
python -c "
from mul_agent.tools import ToolManager, ToolContext, ToolPolicy
context = ToolContext(agent_id='test', workspace_dir='.')
policy = ToolPolicy.from_profile('coding')
manager = ToolManager(context, policy)
tools = manager.list_tools()
print(f'可用工具：{len(tools)} 个')
for tool in tools:
    print(f'  - {tool[\"name\"]}')
"
```

## 参考资料

- [OpenClaw Tools Documentation](https://docs.openclaw.ai/tools)
- [OpenClaw Tool Policy](https://docs.openclaw.ai/tools/tool-policy)
- [OpenClaw Skills](https://docs.openclaw.ai/tools/skills)
