# mul-agent 重构计划

> 参照 openclaw 项目结构进行全面重构

---

## 目标结构

```
mul-agent/
├── src/                          # 核心源代码 (对应 openclaw/src/)
│   ├── agents/                   # Agent 核心逻辑
│   │   ├── core/                 # 核心 Agent 逻辑
│   │   ├── session/              # 会话管理
│   │   ├── prompt/               # Prompt 工程
│   │   └── memory/               # Agent 记忆
│   │
│   ├── gateway/                  # Gateway 服务 (对应 openclaw/src/gateway/)
│   │   ├── boot/                 # 启动引导
│   │   ├── auth/                 # 认证授权
│   │   ├── config/               # 配置管理
│   │   ├── events/               # 事件系统
│   │   └── middleware/           # 中间件
│   │
│   ├── tools/                    # 工具系统 (对应 openclaw/src/agents/tools/)
│   │   ├── base/                 # 工具基类
│   │   ├── builtin/              # 内置工具
│   │   ├── policy/               # 工具策略
│   │   └── manager/              # 工具管理器
│   │
│   ├── skills/                   # 技能系统 (对应 openclaw/skills/ 的运行时)
│   │   ├── loader/               # 技能加载
│   │   ├── manager/              # 技能管理
│   │   └── builtin/              # 内置技能
│   │
│   ├── cli/                      # 命令行接口 (对应 openclaw/src/cli/)
│   │   ├── commands/             # 命令定义
│   │   ├── ui/                   # TTY UI
│   │   └── completion/           # Shell 补全
│   │
│   ├── brain/                    # Agent 大脑 (保留原有核心)
│   │   ├── router/               # 路由分发
│   │   ├── handlers/             # 处理器
│   │   ├── llm/                  # LLM 客户端
│   │   └── cot/                  # 思维链引擎
│   │
│   ├── commands/                 # 命令系统
│   │   ├── builtin/              # 内置命令
│   │   └── registry/             # 命令注册表
│   │
│   ├── hooks/                    # 钩子系统
│   │   ├── pre_tool_use/         # 工具使用前
│   │   ├── post_tool_use/        # 工具使用后
│   │   └── session/              # 会话钩子
│   │
│   ├── memory/                   # 记忆系统
│   │   ├── long_term/            # 长期记忆
│   │   ├── short_term/           # 短期记忆
│   │   └── vector/               # 向量存储
│   │
│   ├── plugins/                  # 插件系统 (对应 openclaw/src/plugins/)
│   │   ├── loader/               # 插件加载
│   │   ├── sdk/                  # 插件 SDK
│   │   └── runtime/              # 插件运行时
│   │
│   ├── network/                  # 网络通信
│   │   ├── agent_protocol/       # Agent 协议
│   │   └── discovery/            # 服务发现
│   │
│   ├── observability/            # 可观测性
│   │   ├── logging/              # 日志
│   │   ├── metrics/              # 指标
│   │   └── tracing/              # 追踪
│   │
│   ├── mcp/                      # MCP 客户端
│   │
│   ├── common/                   # 通用工具
│   │   ├── utils/                # 工具函数
│   │   ├── types/                # 类型定义
│   │   └── constants/            # 常量
│   │
│   └── api/                      # API 服务器
│       ├── routes/               # 路由
│       └── middleware/           # 中间件
│
├── skills/                       # 技能定义 (对应 openclaw/skills/)
│   ├── bash/
│   │   └── SKILL.md
│   ├── read/
│   │   └── SKILL.md
│   ├── write/
│   │   └── SKILL.md
│   ├── edit/
│   │   └── SKILL.md
│   ├── glob/
│   │   └── SKILL.md
│   ├── grep/
│   │   └── SKILL.md
│   ├── git/
│   │   └── SKILL.md
│   └── ...                       # 更多技能
│
├── extensions/                   # 扩展插件 (对应 openclaw/extensions/)
│   ├── discord/
│   │   └── src/
│   ├── telegram/
│   │   └── src/
│   ├── memory-core/
│   │   └── src/
│   └── ...
│
├── test/                         # 测试 (对应 openclaw/test/)
│   ├── fixtures/                 # 测试夹具
│   ├── helpers/                  # 测试辅助
│   ├── mocks/                    # Mock 对象
│   └── scripts/                  # 测试脚本
│
├── docs/                         # 文档 (对应 openclaw/docs/)
│   ├── start/                    # 快速开始
│   ├── concepts/                 # 概念
│   ├── cli/                      # CLI 文档
│   ├── gateway/                  # Gateway 文档
│   ├── tools/                    # 工具文档
│   ├── skills/                   # 技能文档
│   ├── plugins/                  # 插件文档
│   ├── concepts/                 # 核心概念
│   ├── reference/                # 参考文档
│   ├── help/                     # 帮助
│   └── zh-CN/                    # 中文文档
│       ├── start/
│       ├── concepts/
│       └── ...
│
├── wang/                         # 项目配置 (保留原有)
│   ├── agent-team/               # Agent 配置
│   ├── rules/                    # 规则
│   ├── commands/                 # 自定义命令
│   └── settings.json
│
├── storage/                      # 存储 (保留原有)
│   ├── memory/
│   ├── token_usage/
│   ├── agent_states/
│   └── stream_states/
│
├── scripts/                      # 脚本工具
│   ├── setup.sh
│   ├── test.sh
│   └── quality-check.sh
│
├── .agents/                      # Agent 配置 (对应 openclaw/.agents/)
│   ├── skills/                   # 全局技能
│   └── commands/                 # 全局命令
│
├── .claude/                      # Claude 配置
│   ├── settings.json
│   └── rules/
│
├── .git-hooks/                   # Git 钩子
├── .github/                      # GitHub 配置
├── .vscode/                      # VSCode 配置
│
├── CLAUDE.md                     # 项目指南 (保留)
├── AGENTS.md                     # Agent 系统说明 (新增)
├── README.md                     # 说明文档
├── pyproject.toml                # Python 项目配置
├── package.json                  # Node.js 项目配置
├── mint.json                     # Mintlify 文档配置
└── requirements.txt              # Python 依赖
```

---

## 迁移步骤

### 阶段 1: 准备 (完成)
- [x] 分析 openclaw 结构
- [x] 创建工具系统基础 (base.py, policy.py, manager.py)
- [x] 创建文档 (TOOL_SYSTEM_GUIDE.md)

### 阶段 2: 目录重组
1. 创建新的 src/ 目录结构
2. 迁移现有代码到新位置
3. 保持向后兼容的导入路径

### 阶段 3: 技能系统
1. 将 skills/ 迁移到 src/skills/
2. 创建 skills/ 根目录用于 SKILL.md 定义
3. 为每个工具创建 SKILL.md

### 阶段 4: 扩展系统
1. 规范化 extensions/ 结构
2. 每个扩展一个目录

### 阶段 5: 文档重组
1. 按照 openclaw/docs/ 结构重组
2. 添加中文文档目录

### 阶段 6: 测试重组
1. 创建 test/ 目录
2. 迁移现有测试

---

## 对照表

### openclaw → mul-agent

| openclaw | mul-agent (新) | 说明 |
|----------|----------------|------|
| src/agents/ | src/agents/ | Agent 核心逻辑 |
| src/gateway/ | src/gateway/ | Gateway 服务 |
| src/cli/ | src/cli/ | 命令行接口 |
| src/plugins/ | src/plugins/ | 插件系统 |
| src/tools/ | src/tools/ | 工具系统 |
| skills/ | skills/ | 技能定义 (SKILL.md) |
| src/skills/ | src/skills/ | 技能运行时 |
| extensions/ | extensions/ | 扩展插件 |
| docs/ | docs/ | 文档 |
| test/ | test/ | 测试 |
| .agents/ | .agents/ | 全局 Agent 配置 |

---

## 代码迁移映射

### mul_agent/ → src/

```
mul_agent/brain/           → src/brain/
mul_agent/api/             → src/api/
mul_agent/tools/           → src/tools/
mul_agent/skills/          → src/skills/
mul_agent/commands/        → src/commands/
mul_agent/hooks/           → src/hooks/
mul_agent/memory/          → src/memory/
mul_agent/network/         → src/network/
mul_agent/mcp/             → src/mcp/
mul_agent/observability/   → src/observability/
mul_agent/common/          → src/common/
mul_agent/parallel/        → src/parallel/
mul_agent/repositories/    → src/repositories/
```

### 新增目录

```
src/agents/                # 新增：Agent 核心逻辑
src/gateway/               # 新增：Gateway 服务
src/plugins/               # 新增：插件系统
```

---

## SKILL.md 示例

参照 openclaw 的技能格式：

```markdown
---
name: bash
description: 执行 shell 命令。用于文件操作、进程管理、系统查询等。
metadata:
  {
    "mul_agent": {
      "emoji": "💻",
      "requires": { "bins": [], "env": [], "config": [] },
      "tags": ["runtime", "shell", "exec"]
    }
  }
---

# Bash 工具

执行 shell 命令。

## 使用示例

```bash
# 查看文件列表
$ ls -la

# 查找文件
$ find . -name '*.py' -type f

# 查看文件内容
$ cat package.json
```

## 安全限制

- 禁止访问敏感路径
- 禁止执行危险命令
- 支持超时控制
```

---

## 实施命令

```bash
# 1. 创建新目录结构
mkdir -p src/{agents,gateway,plugins}/{core,lib}
mkdir -p src/{cli,commands,hooks,memory,network,mcp,observability,common,parallel,repositories}
mkdir -p skills/{bash,read,write,edit,glob,grep,git,memory,search}
mkdir -p extensions/{discord,telegram,memory-core}
mkdir -p test/{fixtures,helpers,mocks,scripts}

# 2. 迁移现有代码
mv mul_agent/brain src/
mv mul_agent/api src/
mv mul_agent/tools src/
mv mul_agent/skills src/
mv mul_agent/commands src/
mv mul_agent/hooks src/
mv mul_agent/memory src/
mv mul_agent/network src/
mv mul_agent/mcp src/
mv mul_agent/observability src/
mv mul_agent/common src/
mv mul_agent/parallel src/
mv mul_agent/repositories src/

# 3. 创建符号链接保持兼容 (可选)
ln -s ../src/brain mul_agent/brain
ln -s ../src/api mul_agent/api
# ...

# 4. 更新导入路径
# 使用 sed 或 Python 脚本批量替换
```

---

## 注意事项

1. **保持向后兼容**: 创建 `mul_agent/` 作为符号链接或导出层
2. **更新导入**: 批量替换 `from mul_agent.` 为 `from src.`
3. **测试验证**: 迁移后运行所有测试
4. **文档更新**: 更新所有文档中的路径引用
5. **配置更新**: 更新 pyproject.toml, package.json 等配置

---

## 验收标准

- [ ] 所有源代码迁移到 src/
- [ ] skills/ 目录包含 SKILL.md 文件
- [ ] extensions/ 规范化
- [ ] docs/ 按主题分类
- [ ] test/ 目录结构完整
- [ ] 所有测试通过
- [ ] 文档链接正确
- [ ] 导入路径正确
