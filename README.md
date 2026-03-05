# Self-Growing Agent Team

> 一个能够自我进化的多Agent系统，核心大脑可以自主改写团队所有成员配置

## 项目概述

### 核心定位
- **形态**: CLI工具（命令行入口）
- **特点**: 动态团队，由核心Agent自主决定分裂/协作方式
- **权限**: 核心大脑完全自主，可改写所有配置文件
- **版本**: v1.0 (Wang Brain)

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI Entry (main.py)                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                     Core Brain (Agent)                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │  heart  │  │  bash   │  │ memory  │  │ create  │        │
│  │ (自省)   │  │ (执行)  │  │ (记忆)  │  │ (分裂)  │        │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │
│  ┌─────────┐  ┌─────────┐                                 │
│  │  chat   │  │response │                                 │
│  │ (对话)  │  │ (响应)  │                                 │
│  └─────────┘  └─────────┘                                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   Tool Layer (MCP + Native)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Bash Executor│  │ Chrome MCP   │  │ Web Search   │     │
│  │   (命令执行)  │  │   (浏览器)   │  │    (搜索)    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   Storage Layer                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ soul.md │  │user.md  │  │skill.md  │  │memory/  │    │
│  │ (灵魂)   │  │ (用户)   │  │ (技能)   │  │ (记忆)   │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 核心路由 (Core Routes)

| 路由 | 功能 | 说明 |
|------|------|------|
| `create_user` | 创建新Agent成员 | 由核心大脑决定何时分裂 |
| `bash` | 执行shell命令 | 外部能力之一 |
| `heart` | 自省/进化 | 核心大脑自己决定唤醒时机 |
| `memory` | 记忆管理 | 读/写/更新，长期/短期记忆 |
| `chat` | Agent间对话 | 与其他Agent通信 |
| `response` | 响应处理 | 直接响应用户 |

---

## 记忆系统

### 设计原则
- **短期记忆**: 当前会话上下文，由Agent自行管理
- **长期记忆**: Markdown文件持久化，Agent自己决定何时写入
- **交接文档**: Agent自己生成输出文件，指定下一个Agent读取什么

### 记忆文件结构
```
storage/memory/
├── short_term/          # 短期记忆（会话级）
│   └── {agent_id}/
├── long_term/           # 长期记忆（持久化）
│   └── {agent_id}/
└── handover/            # 交接文档
    └── {from}_{to}_{timestamp}.md
```

---

## 配置文件结构

配置文件使用 **Markdown格式**，存储在 `storage/agents/{agent_id}/` 目录下：

| 文件 | 作用 | 管理者 |
|------|------|--------|
| `soul.md` | Agent的灵魂/核心特质、价值观、行为准则 | 核心大脑 |
| `user.md` | Agent的角色定位、能力边界、工具权限、可用路由 | 核心大脑 |
| `skill.md` | Agent能使用的具体技能和能力 | 核心大脑 |
| `memory.md` | 记忆的存储策略、读取规则 | 核心大脑 |

> 详细配置规范见 [CONFIG_SPEC.md](CONFIG_SPEC.md)

---

## 外部能力 (Tools)

| 工具 | 用途 | 配置位置 |
|------|------|----------|
| Bash执行器 | 执行shell命令 | user.md |
| 谷歌浏览器MCP | 浏览器操作、自动化 | user.md |
| Web Search MCP | 网络搜索能力 | user.md |

---

## 守护进程模式

系统支持 **守护进程模式**，具备以下特性：
- **工作状态**: 正在处理用户请求
- **休息状态**: 定时执行任务 + 自我成长
- **定时任务**: 用户可自定义定时任务
- **自我成长**: 定时调用 heart 路由进行自省

---

## 使用方式

```bash
# 启动核心大脑（交互模式）
python main.py brain

# 或指定Agent启动
python main.py agent <agent_id>

# 查看团队状态
python main.py team

# 手动触发某个路由
python main.py route <route_name> --params <json>

# 启动守护进程模式（实验性）
python main.py daemon
python main.py daemon --idle-timeout 300 --grow-interval 3600
python main.py daemon --no-growth  # 禁用自动自我成长
```

---

## 设计原则

1. **代码提供能力，配置定义规则**
   - 代码层只提供基础设施
   - 具体规则由大脑自己在配置文件中定义

2. **自主进化**
   - 核心大脑可以自主修改所有配置文件
   - 通过heart路由进行自省和进化

3. **动态团队**
   - Agent形态不固定，由核心大脑决定
   - 通过create_user路由进行分裂

---

## 技术栈

- **语言**: Python 3.10+
- **CLI框架**: Click
- **LLM集成**: Anthropic SDK (Claude)
- **配置格式**: Markdown (.md)
- **MCP集成**: chrome-devtools MCP, Web Search MCP

## 安全与监控

- **版本快照**: 每次配置修改前自动备份
- **日志记录**: 所有操作可追溯
- **错误处理**: 完善的异常捕获与重试机制

详见 [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 项目结构

```
mul-agent/
├── main.py                 # CLI入口
├── mul_agent/              # 核心代码
│   ├── brain/              # 大脑模块
│   │   ├── brain.py        # 核心大脑类
│   │   ├── router.py       # 路由分发
│   │   ├── handlers.py     # 处理器
│   │   ├── config_manager.py
│   │   ├── llm.py
│   │   ├── context_builder.py
│   │   └── daemon.py       # 守护进程
│   ├── tools/              # 工具层
│   │   ├── bash_executor.py
│   │   └── mcp_tools.py
│   └── memory/             # 记忆系统
│       └── memory.py
├── storage/                # 存储层
│   ├── agents/             # Agent配置
│   │   └── core_brain/
│   │       ├── soul.md
│   │       ├── user.md
│   │       ├── skill.md
│   │       └── memory.md
│   ├── memory/             # 记忆文件
│   │   ├── short_term/
│   │   ├── long_term/
│   │   └── handover/
│   └── snapshots/          # 版本快照
├── tests/                  # 测试
└── docs/                  # 文档
```

---

## 文档目录

- [README.md](README.md) - 项目概述
- [ARCHITECTURE.md](ARCHITECTURE.md) - 详细架构设计
- [CONFIG_SPEC.md](CONFIG_SPEC.md) - 配置文件规范
- [API.md](API.md) - 接口文档
- [IMPLEMENTATION.md](IMPLEMENTATION.md) - 实施计划
