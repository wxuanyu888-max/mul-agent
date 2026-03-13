---
name: mul-agent-core
description: 'Mul-Agent 核心系统操作：使用 Hooks、Commands 和 Skills 系统。Use when: (1) 需要执行 bash 命令或文件操作，(2) 需要运行预定义命令如/help、/status，(3) 需要触发钩子事件，(4) 需要执行技能如文件读写、搜索。NOT for: 简单聊天回复、不需要工具调用的任务。'
metadata:
  {
    "mul_agent": { "emoji": "🤖", "version": "2026.3.9" },
  }
---

# Mul-Agent 核心系统

本技能提供 Mul-Agent 的核心系统使用说明，包括 **Hooks（钩子）**、**Commands（命令）**和 **Skills（技能）** 系统。

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Mul-Agent Core                        │
├─────────────────┬─────────────────┬─────────────────────┤
│    Hooks        │   Commands      │      Skills         │
│  (事件钩子)     │  (预定义命令)   │    (可执行技能)     │
├─────────────────┼─────────────────┼─────────────────────┤
│ • pre_tool_use  │ • /help         │ • bash              │
│ • post_tool_use │ • /status       │ • read_file         │
│ • session_start │ • /echo         │ • write_file        │
│ • session_end   │ • /version      │ • edit_file         │
│ • pre_message   │                 │ • search            │
│ • pre_command   │                 │                     │
└─────────────────┴─────────────────┴─────────────────────┘
```

## 1. Hooks 系统（钩子）

钩子系统允许在特定事件发生时执行自定义逻辑。

### 1.1 支持的事件类型

| 事件 | 触发时机 | 用途 |
|------|----------|------|
| `PRE_TOOL_USE` | 工具使用前 | 参数验证、权限检查、日志记录 |
| `POST_TOOL_USE` | 工具使用后 | 结果处理、日志记录、缓存 |
| `SESSION_START` | 会话开始时 | 加载上下文、初始化状态 |
| `SESSION_END` | 会话结束时 | 保存状态、清理资源、归档 |
| `PRE_MESSAGE` | 消息处理前 | 输入验证、预处理 |
| `POST_MESSAGE` | 消息处理后 | 响应后处理、通知 |
| `PRE_COMMAND` | 命令执行前 | 命令权限检查、参数修改 |
| `POST_COMMAND` | 命令执行后 | 命令结果处理 |

### 1.2 使用示例

#### 触发工具前钩子
```python
from mul_agent.hooks.manager import HookManager

hook_manager = HookManager(config_manager, agent_id)
# 触发权限检查
modified_params = hook_manager.trigger_pre_tool_use(
    route='/bash',
    params={'command': 'ls -la'}
)
```

#### 触发会话钩子
```python
# 会话开始
context = hook_manager.trigger_session_start({
    'user_id': 'user123',
    'session_type': 'chat'
})

# 会话结束
context = hook_manager.trigger_session_end({
    'duration': 3600,
    'messages_count': 42
})
```

### 1.3 内置钩子

#### LogHook（日志钩子）
- **hook_id**: `log_hook`
- **功能**: 记录所有工具调用和会话事件
- **优先级**: 1（低）

#### ValidationHook（验证钩子）
- **hook_id**: `validation_hook`
- **功能**: 验证工具和命令的参数
- **优先级**: 8（高）

#### PermissionHook（权限钩子）
- **hook_id**: `permission_hook`
- **功能**: 控制工具和命令的访问权限
- **优先级**: 10（最高）

### 1.4 自定义钩子

```python
from mul_agent.hooks.base import BaseHook, HookEvent

class CustomHook(BaseHook):
    hook_id = "my_custom_hook"
    hook_name = "My Custom Hook"
    hook_description = "自定义钩子示例"
    hook_tags = ["custom", "demo"]
    priority = 5

    def pre_tool_use(self, route: str, params: dict) -> dict:
        """工具使用前执行"""
        print(f"[HOOK] Tool called: {route}")
        return params

    def session_start(self, context: dict) -> dict:
        """会话开始时执行"""
        context['hooked'] = True
        return context

# 注册钩子
hook_manager.register_hook(CustomHook)
```

---

## 2. Commands 系统（命令）

命令系统提供预定义的快捷命令，支持 `/command` 和 `!command` 格式。

### 2.1 内置命令

| 命令 | 别名 | 描述 | 示例 |
|------|------|------|------|
| `/help` | `/h`, `/?` | 显示帮助信息 | `/help bash` |
| `/status` | `/stat` | 显示系统状态 | `/status` |
| `/echo` | - | 回显输入内容 | `/echo hello` |
| `/version` | `/v`, `/ver` | 显示版本信息 | `/version` |

### 2.2 使用示例

#### 执行命令
```python
from mul_agent.commands.manager import CommandManager

cmd_manager = CommandManager(config_manager, agent_id)

# 执行命令
result = cmd_manager.execute('help', '')
print(result.to_dict())
# {'status': 'success', 'data': {...}, 'message': '...'}

# 从输入执行（支持 /command 和 !command 格式）
result = cmd_manager.execute_from_input('/status')
result = cmd_manager.execute_from_input('!echo hello world')
```

### 2.3 命令结果格式

```python
class CommandResult:
    status: CommandStatus  # success, error, not_found, invalid_args
    data: Any              # 返回数据
    message: str           # 人类可读的消息
    error: Optional[str]   # 错误信息（如果有）
```

### 2.4 自定义命令

```python
from mul_agent.commands.base import BaseCommand, CommandResult, CommandStatus

class CustomCommand(BaseCommand):
    command_id = "greet"
    command_name = "greet"
    command_description = "发送问候消息"
    command_usage = "/greet [name]"
    command_aliases = ["hello", "hi"]
    command_examples = [
        "/greet - 简单问候",
        "/greet Alice - 向 Alice 问候",
    ]

    def execute(self, args: str = "") -> CommandResult:
        if args.strip():
            message = f"Hello, {args}! 👋"
        else:
            message = "Hello! How can I help you today?"

        return CommandResult(
            status=CommandStatus.SUCCESS,
            message=message
        )

# 注册命令
cmd_manager.register_command(CustomCommand)
```

---

## 3. Skills 系统（技能）

技能是可执行的功能模块，提供 bash 执行、文件操作、搜索等能力。

### 3.1 内置技能

| 技能 | 描述 | 需要确认 | 示例 |
|------|------|----------|------|
| `bash` | 执行 bash 命令 | ✅ | `skill_manager.execute_skill('bash', command='ls')` |
| `read_file` | 读取文件内容 | ❌ | `skill_manager.execute_skill('read_file', path='file.txt')` |
| `write_file` | 写入文件内容 | ✅ | `skill_manager.execute_skill('write_file', path='f.txt', content='...')` |
| `edit_file` | 编辑文件内容 | ✅ | `skill_manager.execute_skill('edit_file', path='f.py', old_string='x', new_string='y')` |
| `search` | 搜索文件内容 | ❌ | `skill_manager.execute_skill('search', query='TODO', path='./src')` |

### 3.2 使用示例

#### 执行 Bash 命令
```python
from mul_agent.skills.manager import SkillManager

skill_manager = SkillManager(config_manager, agent_id)

# 执行 bash 命令
result = skill_manager.execute_skill('bash', command='echo hello')
print(result)
# {'stdout': 'hello\n', 'stderr': '', 'returncode': 0}

# 带超时的命令
result = skill_manager.execute_skill('bash', command='sleep 5', timeout=10)
```

#### 文件操作
```python
# 读取文件
result = skill_manager.execute_skill('read_file', path='config.py')
print(result['content'])

# 写入文件
result = skill_manager.execute_skill('write_file',
    path='output.txt',
    content='Hello, World!'
)

# 编辑文件（字符串替换）
result = skill_manager.execute_skill('edit_file',
    path='main.py',
    old_string='def old_func():',
    new_string='def new_func():'
)
```

#### 搜索文件
```python
# 搜索包含关键词的文件
result = skill_manager.execute_skill('search',
    query='TODO',
    path='./src',
    file_pattern='*.py'
)
print(result['results'])  # 匹配的行列表
```

### 3.3 技能结果格式

各技能返回不同的字典格式：

**Bash 技能:**
```python
{
    'stdout': str,      # 标准输出
    'stderr': str,      # 标准错误
    'returncode': int   # 返回码
}
```

**Read File 技能:**
```python
{
    'content': str,     # 文件内容
    'lines': int,       # 行数
    'error': str        # 错误信息（如果有）
}
```

**Write/Edit File 技能:**
```python
{
    'success': bool,    # 是否成功
    'error': str,       # 错误信息
    'replacements': int # 替换次数（edit_file 专用）
}
```

**Search 技能:**
```python
{
    'results': list,    # 匹配结果列表
    'count': int,       # 匹配数量
    'error': str        # 错误信息（如果有）
}
```

### 3.4 自定义技能

```python
from mul_agent.skills.base import BaseSkill

class WeatherSkill(BaseSkill):
    skill_id = "weather"
    skill_name = "Weather"
    skill_description = "获取天气预报"
    skill_tags = ["weather", "api"]
    priority = 5
    requires_confirmation = False

    def _initialize(self) -> None:
        """初始化技能"""
        pass

    def validate_params(self, params: dict) -> bool:
        """验证参数"""
        return 'city' in params

    def execute(self, **kwargs) -> dict:
        """执行技能"""
        city = kwargs.get('city')
        # 调用天气 API...
        return {
            'city': city,
            'temperature': '25°C',
            'condition': 'Sunny'
        }

# 注册技能
skill_manager.register_skill(WeatherSkill)
```

---

## 4. 综合使用示例

### 4.1 完整工作流

```python
from mul_agent.brain.config_manager import ConfigManager
from mul_agent.hooks.manager import HookManager
from mul_agent.commands.manager import CommandManager
from mul_agent.skills.manager import SkillManager

# 初始化
config = ConfigManager()
hook_manager = HookManager(config, 'agent-1')
cmd_manager = CommandManager(config, 'agent-1')
skill_manager = SkillManager(config, 'agent-1')

# 1. 会话开始钩子触发
context = hook_manager.trigger_session_start({'user': 'alice'})

# 2. 用户执行命令
result = cmd_manager.execute_from_input('/status')

# 3. 用户请求执行 bash
try:
    # 触发 pre_tool_use 钩子（权限检查）
    params = hook_manager.trigger_pre_tool_use('/bash', {'command': 'ls'})

    # 执行技能
    result = skill_manager.execute_skill('bash', command='ls')

    # 触发 post_tool_use 钩子（日志记录）
    result = hook_manager.trigger_post_tool_use('/bash', {'command': 'ls'}, result)

except PermissionError as e:
    print(f"权限拒绝：{e}")

# 4. 会话结束钩子触发
hook_manager.trigger_session_end(context)
```

### 4.2 钩子 + 技能组合

```python
class SecurityHook(BaseHook):
    """安全检查钩子"""
    hook_id = "security_hook"
    priority = 10

    def pre_tool_use(self, route: str, params: dict) -> dict:
        # 阻止危险命令
        dangerous = ['rm -rf /', 'sudo rm -rf', 'dd if=/dev/zero']
        cmd = params.get('command', '')
        if any(d in cmd for d in dangerous):
            raise PermissionError(f"Dangerous command blocked: {cmd}")
        return params

# 注册后，所有技能执行都会经过安全检查
skill_manager.execute_skill('bash', command='ls -la')  # ✅
skill_manager.execute_skill('bash', command='rm -rf /')  # ❌ 被阻止
```

---

## 5. 配置管理

### 5.1 权限配置

```python
from mul_agent.hooks.permission import PermissionHook

# 获取权限钩子
perm_hook = hook_manager.get_hook('permission_hook')

# 添加允许的工具
perm_hook.add_allowed_tool('/bash')
perm_hook.add_allowed_tool('/read_file')

# 添加禁止的工具
perm_hook.add_denied_tool('/write_file')

# 添加允许的命令
perm_hook.add_allowed_command('help')
perm_hook.add_allowed_command('status')

# 检查权限
if perm_hook.allow_tool('/bash'):
    skill_manager.execute_skill('bash', command='ls')
```

### 5.2 配置存储

```python
# 保存配置
config.set_config('permissions.allowed_tools', ['/bash', '/read_file'])
config.set_config('permissions.denied_tools', ['/write_file'])
config.set_config('agents.agent-1.enabled', True)

# 读取配置
allowed = config.get_config('permissions.allowed_tools', [])
agent_enabled = config.get_config('agents.agent-1.enabled', False)
```

---

## 6. 最佳实践

### 6.1 技能使用

| 场景 | 推荐技能 | 说明 |
|------|----------|------|
| 执行系统命令 | `bash` | 支持 timeout、后台执行 |
| 读取配置文件 | `read_file` | 自动处理编码和截断 |
| 创建/修改文件 | `write_file` / `edit_file` | 需要确认，安全 |
| 查找代码 | `search` | 支持文件模式过滤 |

### 6.2 钩子设计原则

1. **保持轻量**: 钩子应快速执行，避免阻塞
2. **单一职责**: 每个钩子只做一件事
3. **错误处理**: 钩子错误不应中断主流程
4. **优先级**: 安全钩子优先级最高（10）

### 6.3 命令设计原则

1. **简洁**: 命令应简单直接
2. **有帮助**: 提供清晰的 usage 和 examples
3. **别名**: 为常用命令设置简短别名
4. **错误友好**: 返回清晰的错误信息

---

## 7. 故障排查

### 7.1 常见问题

**技能未找到:**
```python
# 检查技能是否注册
skills = skill_manager.list_skills()
print([s['skill_id'] for s in skills])
```

**命令执行失败:**
```python
result = cmd_manager.execute('unknown', '')
print(result.status.value)  # 'not_found'
```

**钩子未触发:**
```python
# 检查钩子是否启用
hook = hook_manager.get_hook('log_hook')
print(hook.enabled)  # 应为 True
```

### 7.2 调试模式

```python
# 列出所有已注册的组件
print(f"Hooks: {hook_manager.list_hooks()}")
print(f"Commands: {cmd_manager.list_commands()}")
print(f"Skills: {skill_manager.list_skills()}")

# 查看事件处理器
print(f"Event handlers: {hook_manager.to_dict()['event_handlers']}")
```

---

## 8. 扩展指南

### 8.1 添加新钩子

1. 继承 `BaseHook`
2. 实现事件方法
3. 注册到 `HookManager`

### 8.2 添加新命令

1. 继承 `BaseCommand`
2. 实现 `execute` 方法
3. 注册到 `CommandManager`

### 8.3 添加新技能

1. 继承 `BaseSkill`
2. 实现 `_initialize` 和 `execute` 方法
3. 注册到 `SkillManager`

---

## 9. 版本信息

- **系统版本**: 2026.3.9
- **Python 版本**: 3.10+
- **依赖**: httpx, pyyaml, pydantic

## 10. 相关资源

- [OpenClaw 参考架构](https://github.com/openclaw/openclaw)
- [AGENTS.md](./AGENTS.md) - 项目指南
- [CONTRIBUTING.md](./CONTRIBUTING.md) - 贡献指南
