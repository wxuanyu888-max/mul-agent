# mul-agent 架构统一方案

**日期**: 2026-03-09
**参考**: OpenClaw 架构
**目标**: 统一 mul-agent 文件架构，与 OpenClaw 保持一致的模块组织

---

## 一、当前架构问题

### 1.1 模块分散

```
当前问题:
- brain/ 包含了过多职责 (路由、处理器、LLM)
- core/ 与 brain/ 职责重叠
- tools/ 与 handlers/ 功能交叉
- plugins/ 与 extensions/ 界限模糊
```

### 1.2 命名不一致

| 当前命名 | OpenClaw 命名 | 建议统一 |
|----------|---------------|----------|
| `brain/` | `agents/` | `agents/` |
| `core/` | `agents/core` | 合并到 `agents/` |
| `tools/` | `agents/tools` | 保持 `tools/` |
| `handlers/` | `agents/handlers` | 合并到 `agents/` |

---

## 二、目标架构设计

### 2.1 根目录结构

```
mul-agent/
├── mul_agent/                    # Python 主包
│   ├── __init__.py               # 包入口
│   ├── __main__.py               # python -m 入口
│   └── main.py                   # 主程序
│
├── src/                          # 核心源代码 (统一)
│   ├── agents/                   # Agent 核心系统
│   ├── commands/                 # 命令系统
│   ├── channels/                 # 消息渠道
│   ├── gateway/                  # 网关系统
│   ├── plugins/                  # 插件系统
│   ├── plugin-sdk/               # 插件 SDK
│   ├── hooks/                    # Hook 系统
│   ├── memory/                   # 记忆系统
│   ├── config/                   # 配置系统
│   ├── security/                 # 安全模块
│   ├── sessions/                 # 会话管理
│   ├── cron/                     # 定时任务
│   ├── routing/                  # 路由系统
│   ├── utils/                    # 工具函数
│   ├── shared/                   # 共享代码
│   └── types/                    # 类型定义
│
├── extensions/                   # 独立扩展包
├── skills/                       # 独立技能包
├── scripts/                      # 脚本工具
├── tests/                        # 测试
├── docs/                         # 文档
├── wang/                         # 项目配置
└── storage/                      # 运行时存储
```

### 2.2 模块映射表

| OpenClaw | mul-agent 当前 | mul-agent 目标 | 操作 |
|----------|----------------|----------------|------|
| `src/agents/` | `mul_agent/brain/`, `mul_agent/core/` | `src/agents/` | 合并 |
| `src/commands/` | `mul_agent/commands/` | `src/commands/` | 移动 |
| `src/hooks/` | `mul_agent/hooks/` | `src/hooks/` | 移动 |
| `src/memory/` | `mul_agent/memory/` | `src/memory/` | 移动 |
| `src/plugins/` | ❌ | `src/plugins/` | 新建 |
| `src/plugin-sdk/` | `mul_agent/plugins/` | `src/plugin-sdk/` | 重命名 |
| `src/gateway/` | ❌ | `src/gateway/` | 新建 |
| `src/channels/` | ❌ | `src/channels/` | 新建 |
| `src/config/` | ❌ | `src/config/` | 新建 |
| `src/security/` | ❌ | `src/security/` | 新建 |
| `src/sessions/` | ❌ | `src/sessions/` | 新建 |
| `src/cron/` | ❌ | `src/cron/` | 新建 |
| `src/routing/` | `mul_agent/brain/router.py` | `src/routing/` | 移动 |
| `src/utils/` | ❌ | `src/utils/` | 新建 |
| `src/shared/` | ❌ | `src/shared/` | 新建 |
| `src/types/` | `frontend/src/types.ts` | `src/types/` | 新建 |
| `src/cli/` | `mul_agent/cli/` | `src/cli/` | 移动 |
| `src/tools/` | `mul_agent/tools/` | `src/tools/` | 移动 |
| `src/skills/` | `mul_agent/skills/` | `src/skills/` | 移动 |

---

## 三、详细模块结构

### 3.1 `src/agents/` - Agent 核心系统

```
src/agents/
├── __init__.py
├── agent.py                    # Agent 基类
├── agent_config.py             # Agent 配置
├── agent_identity.py           # Agent 身份
├── agent_files.py              # Agent 文件管理
├── agent_scope.py              # Agent 作用域
├── agent_paths.py              # Agent 路径
├── delivery.py                 # Agent 交付
├── providers.py                # Agent 提供商
├── skills.py                   # Agent 技能
│
├── handlers/                   # 处理器 (从 brain/ 移入)
│   ├── __init__.py
│   ├── bash.py
│   ├── code_understanding.py
│   ├── cot.py
│   ├── git.py
│   ├── glob.py
│   ├── grep.py
│   ├── memetic.py
│   ├── planner.py
│   ├── response.py
│   ├── subagent.py
│   └── visualization.py
│
├── tools/                      # 工具 (从 tools/ 移入)
│   ├── __init__.py
│   ├── base.py
│   ├── registry.py
│   ├── policy.py
│   ├── manager.py
│   └── builtins/
│       ├── bash.py
│       ├── edit.py
│       ├── read.py
│       └── write.py
│
└── brain/                      # 大脑 (保留核心)
    ├── __init__.py
    ├── brain.py                # Brain 主类
    ├── llm.py                  # LLM 客户端
    ├── router.py               # 路由分发器
    ├── skill_loader.py         # 技能加载器
    ├── autonomous_loop.py      # 自主循环
    ├── brain_v2.py             # Brain v2
    ├── checkpoint.py           # 检查点
    ├── code_understanding.py   # 代码理解
    ├── cot_engine.py           # CoT 引擎
    ├── daemon.py               # 守护进程
    ├── memetic_engine.py       # 模因引擎
    ├── planner.py              # 规划器
    ├── session_state.py        # 会话状态
    ├── stream.py               # 流处理
    ├── subagent.py             # 子 Agent
    ├── visualizer.py           # 可视化
    └── workspace.py            # 工作空间
```

### 3.2 `src/commands/` - 命令系统

```
src/commands/
├── __init__.py
├── loader.py                   # 命令加载器
├── types.py                    # 命令类型
├── workspace.py                # 工作空间命令
├── message_hooks.py            # 消息钩子命令
├── install.py                  # 安装命令
├── installs.py                 # 安装管理
├── hooks.py                    # Hooks 管理
└── builtin/
    ├── __init__.py
    ├── bash.py
    ├── chat.py
    ├── memory.py
    └── heart.py
```

### 3.3 `src/channels/` - 消息渠道

```
src/channels/
├── __init__.py
├── base.py                     # 渠道基类
├── registry.py                 # 渠道注册表
├── lifecycle.py                # 生命周期
├── config.py                   # 渠道配置
├── plugin_common.py            # 渠道插件通用
├── webhook.py                  # Webhook 支持
│
├── providers/                  # 渠道提供商
│   ├── telegram.py
│   ├── discord.py
│   ├── slack.py
│   ├── whatsapp.py
│   ├── signal.py
│   └── web.py
│
└── builtin/                    # 内置渠道
    ├── console.py
    └── file.py
```

### 3.4 `src/gateway/` - 网关系统

```
src/gateway/
├── __init__.py
├── server.py                   # HTTP 服务器
├── provider_web.py             # Web 提供者
├── routing.py                  # 网关路由
├── auth.py                     # 认证
├── health.py                   # 健康检查
├── device_pair.py              # 设备配对
└── webhooks.py                 # Webhook 处理
```

### 3.5 `src/plugins/` - 插件系统

```
src/plugins/
├── __init__.py
├── registry.py                 # 插件注册表
├── loader.py                   # 插件加载器
├── runtime.py                  # 插件运行时
└── builtin/                    # 内置插件
    ├── __init__.py
    ├── memory.py
    └── github.py
```

### 3.6 `src/plugin-sdk/` - 插件 SDK

```
src/plugin-sdk/
├── __init__.py
├── core.py                     # SDK 核心
├── types.py                    # 类型定义
├── registry.py                 # 注册表
├── hook_registry.py            # Hook 注册表
├── tool_registry.py            # 工具注册表
├── command_registry.py         # 命令注册表
├── api.py                      # 插件 API
├── discovery.py                # 插件发现
└── utils/
    ├── file_lock.py
    ├── temp_path.py
    ├── json_store.py
    └── keyed_queue.py
```

### 3.7 `src/hooks/` - Hook 系统

```
src/hooks/
├── __init__.py
├── registry.py                 # Hook 注册表
├── types.py                    # Hook 类型
├── manager.py                  # Hook 管理器
├── permission.py               # 权限控制
├── message_hooks.py            # 消息钩子
├── internal_hooks.py           # 内部钩子
└── builtin/
    ├── __init__.py
    ├── pre_tool_use.py
    ├── post_tool_use.py
    └── session_hooks.py
```

### 3.8 `src/memory/` - 记忆系统

```
src/memory/
├── __init__.py
├── memory_manager.py           # 记忆管理器
├── memory_schema.py            # 记忆 Schema
├── memory_routes.py            # 记忆路由
├── memory_indexer.py           # 记忆索引器
├── embeddings.py               # 嵌入
├── mmr.py                      # MMR 检索
└── storage/
    ├── base.py
    ├── filesystem.py
    └── lancedb.py              # LanceDB 支持
```

### 3.9 `src/config/` - 配置系统

```
src/config/
├── __init__.py
├── config.py                   # 配置主类
├── paths.py                    # 配置路径
├── store.py                    # 配置存储
├── form_coerce.py              # 表单转换
├── form_utils.py               # 表单工具
├── auth_profiles.py            # 认证配置
├── channel_config.py           # 渠道配置
├── device_identity.py          # 设备身份
└── secrets.py                  # Secret 管理
```

### 3.10 `src/security/` - 安全模块

```
src/security/
├── __init__.py
├── ssrf_policy.py              # SSRF 防护
├── secrets_policy.py           # Secret 策略
├── webhook_guards.py           # Webhook 防护
├── auth_health.py              # 认证健康
└── api_key_rotation.py         # API Key 轮换
```

### 3.11 `src/sessions/` - 会话管理

```
src/sessions/
├── __init__.py
├── session.py                  # 会话类
├── storage.py                  # 会话存储
├── history.py                  # 会话历史
├── recovery.py                 # 会话恢复
└── presence.py                 # 存在检测
```

### 3.12 `src/cron/` - 定时任务

```
src/cron/
├── __init__.py
├── scheduler.py                # 调度器
├── parser.py                   # Cron 解析器
├── executor.py                 # 执行器
├── filters.py                  # 过滤器
└── builtin/
    ├── __init__.py
    ├── cleanup.py
    └── health_check.py
```

### 3.13 `src/routing/` - 路由系统

```
src/routing/
├── __init__.py
├── router.py                   # 主路由器
├── agent_routing.py            # Agent 路由
├── channel_routing.py          # 渠道路由
└── allowlist.py                # 允许列表
```

### 3.14 `src/utils/` - 工具函数

```
src/utils/
├── __init__.py
├── async_queue.py              # 异步队列
├── file_ops.py                 # 文件操作
├── string_ops.py               # 字符串操作
├── json_ops.py                 # JSON 操作
├── path_ops.py                 # 路径操作
├── retry.py                    # 重试机制
└── decorators.py               # 装饰器
```

### 3.15 `src/shared/` - 共享代码

```
src/shared/
├── __init__.py
├── constants.py                # 常量
├── exceptions.py               # 异常
├── logging.py                  # 日志
├── markers.py                  # 类型标记
└── version.py                  # 版本信息
```

### 3.16 `src/types/` - 类型定义

```
src/types/
├── __init__.py
├── agent.py                    # Agent 类型
├── command.py                  # 命令类型
├── hook.py                     # Hook 类型
├── memory.py                   # 记忆类型
├── message.py                  # 消息类型
├── plugin.py                   # 插件类型
├── tool.py                     # 工具类型
└── channel.py                  # 渠道类型
```

### 3.17 `src/cli/` - CLI 入口

```
src/cli/
├── __init__.py
├── main.py                     # CLI 主入口
├── entry.py                    # 入口点
├── progress.py                 # 进度显示
├── palette.py                  # 终端调色板
└── commands/
    ├── agent.py
    ├── channel.py
    ├── config.py
    ├── hook.py
    ├── memory.py
    ├── plugin.py
    └── tool.py
```

---

## 四、迁移步骤

### 阶段 1: 创建新结构 (Day 1-2)

```bash
# 创建新的 src/ 目录结构
mkdir -p mul_agent/src/{agents,commands,channels,gateway,plugins,plugin-sdk,hooks,memory,config,security,sessions,cron,routing,utils,shared,types,cli,tools,skills}

# 创建 __init__.py 文件
touch mul_agent/src/__init__.py
```

### 阶段 2: 迁移现有模块 (Day 3-5)

1. 迁移 `brain/` → `src/agents/brain/`
2. 迁移 `core/` → `src/agents/` (合并)
3. 迁移 `tools/` → `src/agents/tools/`
4. 迁移 `commands/` → `src/commands/`
5. 迁移 `hooks/` → `src/hooks/`
6. 迁移 `memory/` → `src/memory/`
7. 迁移 `plugins/` → `src/plugin-sdk/`
8. 迁移 `cli/` → `src/cli/`
9. 迁移 `network/` → `src/routing/`

### 阶段 3: 新建模块 (Day 6-10)

1. 创建 `src/channels/`
2. 创建 `src/gateway/`
3. 创建 `src/config/`
4. 创建 `src/security/`
5. 创建 `src/sessions/`
6. 创建 `src/cron/`
7. 创建 `src/utils/`
8. 创建 `src/shared/`
9. 创建 `src/types/`

### 阶段 4: 更新导入 (Day 11-12)

- 更新所有 Python 文件的 import 路径
- 更新 `mul_agent/__init__.py` 导出
- 更新测试文件的导入路径

### 阶段 5: 验证测试 (Day 13-14)

- 运行所有测试
- 修复导入错误
- 验证功能正常

---

## 五、最终目录树

```
mul-agent/
├── mul_agent/
│   ├── src/                          # 核心源代码
│   │   ├── __init__.py
│   │   ├── agents/                   # Agent 系统
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── brain/                # 大脑子模块
│   │   │   ├── handlers/             # 处理器
│   │   │   └── tools/                # 工具
│   │   ├── commands/                 # 命令系统
│   │   ├── channels/                 # 消息渠道
│   │   ├── gateway/                  # 网关系统
│   │   ├── plugins/                  # 内置插件
│   │   ├── plugin-sdk/               # 插件 SDK
│   │   ├── hooks/                    # Hook 系统
│   │   ├── memory/                   # 记忆系统
│   │   ├── config/                   # 配置系统
│   │   ├── security/                 # 安全模块
│   │   ├── sessions/                 # 会话管理
│   │   ├── cron/                     # 定时任务
│   │   ├── routing/                  # 路由系统
│   │   ├── utils/                    # 工具函数
│   │   ├── shared/                   # 共享代码
│   │   ├── types/                    # 类型定义
│   │   ├── cli/                      # CLI 入口
│   │   ├── tools/                    # 工具 (复用)
│   │   └── skills/                   # 技能
│   │
│   ├── api/                          # API 层 (保持)
│   ├── mcp/                          # MCP 客户端 (保持)
│   ├── observability/                # 可观测性 (保持)
│   ├── parallel/                     # 并行处理 (保持)
│   └── repositories/                 # 数据仓库 (保持)
│
├── extensions/                       # 独立扩展
├── skills/                           # 独立技能
├── scripts/                          # 脚本工具
├── tests/                            # 测试
├── docs/                             # 文档
├── wang/                             # 配置
└── storage/                          # 存储
```

---

## 六、导入路径映射

### 迁移前 → 迁移后

```python
# 之前
from mul_agent.brain.brain import Brain
from mul_agent.core.agent import Agent
from mul_agent.tools.base import BaseTool
from mul_agent.commands.manager import CommandManager
from mul_agent.hooks.manager import HookManager
from mul_agent.memory.memory_manager import MemoryManager
from mul_agent.plugins.sdk import PluginAPI
from mul_agent.cli import main

# 之后
from mul_agent.src.agents.brain import Brain
from mul_agent.src.agents.agent import Agent
from mul_agent.src.agents.tools.base import BaseTool
from mul_agent.src.commands.manager import CommandManager
from mul_agent.src.hooks.manager import HookManager
from mul_agent.src.memory.memory_manager import MemoryManager
from mul_agent.src.plugin_sdk.api import PluginAPI
from mul_agent.src.cli.main import main
```

---

## 七、优势与收益

### 7.1 统一性

- ✅ 与 OpenClaw 架构保持一致
- ✅ 模块职责清晰
- ✅ 便于跨项目协作

### 7.2 可扩展性

- ✅ 渠道系统支持扩展
- ✅ 插件系统标准化
- ✅ Hook 系统统一

### 7.3 维护性

- ✅ 代码组织更清晰
- ✅ 导入路径统一
- ✅ 测试覆盖率提升

---

## 八、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 导入路径错误 | 高 | 使用 IDE 批量重构 |
| 测试失败 | 中 | 分阶段迁移，逐阶段验证 |
| 功能回归 | 中 | 保留旧代码直到验证完成 |
| 文档过期 | 低 | 更新文档索引 |

---

## 九、后续工作

1. **更新 pyproject.toml** - 指向新的 src/ 目录
2. **更新 .gitignore** - 排除新缓存目录
3. **更新 CLAUDE.md** - 更新项目指南
4. **更新 README.md** - 更新项目结构说明
5. **添加迁移指南** - 帮助用户/开发者迁移
