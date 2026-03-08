# Skill/Hook/Command 系统使用指南

## 概述

本项目现已添加完整的 Skill/Hook/Command 支持系统：

| 系统 | 用途 | 触发方式 |
|------|------|----------|
| **Skill** | Agent 的核心能力单元 | 自动或手动调用 |
| **Hook** | 事件驱动的回调函数 | 特定事件触发 |
| **Command** | 用户可直接执行的命令 | 用户输入触发 |

---

## Skill 系统

### 内置技能

| 技能 ID | 名称 | 描述 | 标签 |
|---------|------|------|------|
| `bash_executor` | Bash Executor | 执行 shell 命令 | shell, command, execution |
| `memory_manager` | Memory Manager | 管理记忆系统 | memory, storage, retrieval |
| `agent_chat` | Agent Chat | 与其他 Agent 对话 | chat, communication, agent |
| `code_executor` | Code Executor | 执行代码 | code, execution, analysis |
| `searcher` | Searcher | 搜索文件和内容 | search, file, content |

### 使用方式

#### 1. 通过 Brain 实例调用

```python
from mul_agent.brain.brain import Brain
from mul_agent.brain.config_manager import ConfigManager

config_manager = ConfigManager(config_dir)
brain = Brain("wangyue", config_manager)

# 执行技能
result = brain.execute_skill("bash_executor", command="ls -la")
print(result)

# 列出所有技能
skills = brain.list_skills()
for skill in skills:
    print(f"{skill['skill_name']}: {skill['skill_description']}")
```

#### 2. 通过用户输入调用

```
用户：execute skill bash_executor command=ls -la
用户：使用 skill memory_manager action=list memory_type=short_term
```

### 创建自定义技能

```python
from mul_agent.skills.base import BaseSkill
from typing import Any, Dict

class MyCustomSkill(BaseSkill):
    skill_id = "my_custom_skill"
    skill_name = "My Custom Skill"
    skill_version = "1.0.0"
    skill_description = "Description of my skill"
    skill_tags = ["custom", "example"]
    priority = 5

    def _initialize(self) -> None:
        """初始化逻辑"""
        pass

    def execute(self, **kwargs) -> Any:
        """执行逻辑"""
        param1 = kwargs.get("param1", "default")
        return {"result": f"Executed with param1={param1}"}

# 注册技能
brain.skill_manager.register_skill(MyCustomSkill)
```

---

## Hook 系统

### 内置钩子

| 钩子 ID | 名称 | 事件类型 | 优先级 | 描述 |
|---------|------|----------|--------|------|
| `log_invocation` | Log Invocation | PostToolUse | Low | 记录工具调用日志 |
| `format_output` | Format Output | PostToolUse | Normal | 格式化输出 |
| `safety_check` | Safety Check | PreToolUse | High | 安全检查 |
| `session_state` | Session State | SessionStart/End | - | 会话状态管理 |
| `rate_limit` | Rate Limit | PreToolUse | High | 限流控制 |

### 事件类型

```python
from mul_agent.hooks.base import HookEvent

# 可用的事件类型
HookEvent.PRE_TOOL_USE      # 工具执行前
HookEvent.POST_TOOL_USE     # 工具执行后
HookEvent.SESSION_START     # 会话开始
HookEvent.SESSION_END       # 会话结束
HookEvent.PRE_MESSAGE       # 消息处理前
HookEvent.POST_MESSAGE      # 消息处理后
```

### 使用方式

#### 1. 触发钩子

```python
from mul_agent.hooks.base import HookEvent

# 触发 PreToolUse 钩子
modified_params = brain.hook_manager.trigger_pre_tool_use(
    tool_name="bash",
    params={"command": "ls -la"}
)

# 触发 PostToolUse 钩子
modified_result = brain.hook_manager.trigger_post_tool_use(
    tool_name="bash",
    params={"command": "ls -la"},
    result={"stdout": "..."}
)

# 触发 SessionStart 钩子
brain.hook_manager.trigger_session_start()

# 触发 SessionEnd 钩子
brain.hook_manager.trigger_session_end()
```

#### 2. 创建自定义钩子

```python
from mul_agent.hooks.base import (
    BaseHook,
    HookContext,
    HookEvent,
    HookPriority,
    PreToolUseHook
)
from typing import Optional, Dict, Any

class MySafetyHook(PreToolUseHook):
    hook_id = "my_safety_hook"
    hook_name = "My Safety Hook"
    hook_version = "1.0.0"
    hook_description = "Custom safety check"
    events = [HookEvent.PRE_TOOL_USE]
    priority = HookPriority.HIGH

    def _initialize(self) -> None:
        self.forbidden_commands = ["rm -rf /"]

    def on_pre_tool_use(self, context: HookContext) -> Optional[Dict[str, Any]]:
        tool_name = context.get("tool_name")
        params = context.get("params", {})

        if tool_name == "bash":
            command = params.get("command", "")
            for forbidden in self.forbidden_commands:
                if forbidden in command:
                    return {
                        "blocked": True,
                        "error": f"Command blocked: {command}"
                    }
        return None

# 注册钩子
brain.hook_manager.register_hook(MySafetyHook)
```

#### 3. 添加函数钩子（快速方式）

```python
from mul_agent.hooks.base import HookEvent, HookPriority

def my_logging_hook(context: HookContext) -> Optional[Dict[str, Any]]:
    print(f"Tool called: {context.get('tool_name')}")
    return None

brain.hook_manager.add_hook_function(
    event=HookEvent.POST_TOOL_USE,
    callback=my_logging_hook,
    priority=HookPriority.LOW,
    hook_id="my_logging_hook"
)
```

---

## Command 系统

### 内置命令

| 命令 ID | 名称 | 别名 | 描述 |
|---------|------|------|------|
| `help` | help | h, ?, 援助 | 显示帮助信息 |
| `status` | status | st, 状态 | 显示 Agent 状态 |
| `list` | list | ls, 列表 | 列出项目 |
| `skill` | skill | sk, 技能 | 管理技能 |
| `hook` | hook | hk, 钩子 | 管理钩子 |
| `memory` | memory | mem, 记忆 | 管理记忆 |
| `bash` | bash | $, sh, 执行 | 执行 shell 命令 |

### 使用方式

#### 1. 通过用户输入调用

```
用户：/help skill
用户：!status
用户：.list skills
用户：/skill list
用户：/hook list
用户：/memory list
```

#### 2. 通过 Brain 实例调用

```python
# 执行命令
result = brain.execute_command("skill", "list")
print(result)

# 列出所有命令
commands = brain.list_commands()
for cmd in commands:
    print(f"{cmd['command_name']}: {cmd['command_description']}")
```

### 创建自定义命令

```python
from mul_agent.commands.base import (
    BaseCommand,
    CommandContext,
    CommandResult,
    CommandStatus
)

class MyCustomCommand(BaseCommand):
    command_id = "my_custom_command"
    command_name = "mycmd"
    command_description = "My custom command"
    command_usage = "mycmd [options]"
    command_aliases = ["mc", "自定义"]
    command_examples = ["mycmd arg1 --flag"]

    def _initialize(self) -> None:
        pass

    def execute(self, context: CommandContext) -> CommandResult:
        arg1 = context.get_arg(0)
        flag = context.get_kwarg("flag", False)

        if not arg1:
            return CommandResult.error(
                message="Argument required",
                usage=self.command_usage
            )

        # 执行逻辑
        result = {"processed": arg1, "flag": flag}

        return CommandResult.success(
            message=f"Processed: {arg1}",
            data=result
        )

# 注册命令
brain.command_manager.register_command(MyCustomCommand)
```

#### 添加函数命令（快速方式）

```python
from mul_agent.commands.base import CommandContext, CommandResult

def hello_command(ctx: CommandContext) -> CommandResult:
    name = ctx.get_arg(0, "World")
    return CommandResult.success(message=f"Hello, {name}!")

brain.command_manager.add_command_function(
    command_name="hello",
    callback=hello_command,
    description="Say hello",
    usage="hello [name]",
    aliases=["hi", "greet"]
)
```

---

## 集成使用示例

### 完整的 Agent 初始化和使用

```python
from mul_agent.brain.brain import Brain
from mul_agent.brain.config_manager import ConfigManager
from pathlib import Path

# 初始化
config_dir = Path("storage")
config_manager = ConfigManager(config_dir)
brain = Brain("wangyue", config_manager)

try:
    # 1. 处理用户输入（自动检测命令）
    result = brain.think("/help")
    print(result)

    # 2. 执行技能
    result = brain.execute_skill("bash_executor", command="pwd")
    print(result)

    # 3. 列出所有可用的组件
    print("Skills:", [s["skill_name"] for s in brain.list_skills()])
    print("Hooks:", [h["hook_name"] for h in brain.list_hooks()])
    print("Commands:", [c["command_name"] for c in brain.list_commands()])

    # 4. 清理资源（触发 SessionEnd 钩子）
    brain.cleanup()

except Exception as e:
    print(f"Error: {e}")
```

---

## 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         Brain                               │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Skill     │  │    Hook      │  │   Command    │      │
│  │   Manager    │  │   Manager    │  │   Manager    │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                 │                 │               │
│  ┌──────┴───────┐  ┌──────┴───────┐  ┌──────┴───────┐      │
│  │ BashSkill    │  │ PreToolUse   │  │ HelpCommand  │      │
│  │ MemorySkill  │  │ PostToolUse  │  │ ListCommand  │      │
│  │ ChatSkill    │  │ SessionStart │  │ SkillCommand │      │
│  │ CodeSkill    │  │ SessionEnd   │  │ HookCommand  │      │
│  │ SearchSkill  │  │              │  │ MemoryCommand│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
├─────────────────────────────────────────────────────────────┤
│                         Router                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 最佳实践

### 1. Skill 使用建议

- 将可复用的功能封装为 Skill
- 使用标签（tags）对技能进行分类
- 为复杂技能实现参数验证

### 2. Hook 使用建议

- 使用 PreToolUse 钩子进行输入验证和安全检查
- 使用 PostToolUse 钩子进行日志记录和结果格式化
- 使用 SessionStart/End 钩子进行资源管理

### 3. Command 使用建议

- 为常用操作创建快捷命令
- 提供清晰的帮助信息和使用示例
- 使用别名提高易用性

---

## 故障排除

### 技能无法执行

1. 检查技能是否已注册：`brain.list_skills()`
2. 检查技能是否启用：检查 `enabled` 属性
3. 验证参数是否正确

### 钩子未触发

1. 检查钩子是否已注册到正确的事件
2. 检查钩子的 `enabled` 属性
3. 检查优先级设置

### 命令无法执行

1. 检查命令是否已注册
2. 检查命令别名是否正确
3. 验证参数格式
