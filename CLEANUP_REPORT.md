# mul-agent 目录清理报告

**日期**: 2026-03-09
**目标**: 清理重复目录，统一项目结构

---

## 一、清理前的问题

### 1. 重复的源代码目录
```
❌ src/              (与 mul_agent/ 重复)
❌ agents/           (与 wang/agent-team/ 重复)
❌ skills/           (与 mul_agent/skills/ 重复)
❌ test/             (与 tests/ 重复)
```

### 2. 重复的配置文件
```
❌ main.py           (根目录)
❌ mul_agent_cli.py  (根目录)
❌ run_tests.sh      (根目录)
```

### 3. 混乱的文档目录
```
❌ docs/优化方案
❌ docs/归档
❌ docs/测试报告
❌ docs/todo
❌ docs/规则
❌ docs/help
❌ docs/installation
❌ docs/introduction
❌ ... (62 个子目录)
```

### 4. 重复的存储
```
❌ storage/wang/     (与 wang/ 重复)
```

---

## 二、清理后结构

```
mul-agent/
├── mul_agent/              # ✅ Python 主包（唯一源代码）
│   ├── api/                # API 层
│   ├── brain/              # 大脑系统
│   ├── cli/                # CLI 入口
│   ├── commands/           # 命令系统
│   ├── core/               # 核心系统 (Agent/Brain)
│   ├── extensions/         # 扩展
│   ├── hooks/              # Hook 系统
│   ├── mcp/                # MCP 客户端
│   ├── memory/             # 记忆系统
│   ├── network/            # 网络系统
│   ├── observability/      # 可观测性
│   ├── parallel/           # 并行处理
│   ├── plugins/            # 插件系统
│   ├── repositories/       # 数据仓库
│   ├── skills/             # 技能系统
│   └── tools/              # 工具系统
│
├── wang/                   # ✅ 配置和数据存储
│   ├── agent-team/         # Agent 配置 (SKILL.md)
│   ├── commands/           # 自定义命令
│   ├── file-history/       # 文件历史
│   ├── hooks/              # Hook 配置
│   ├── mcp-configs/        # MCP 配置
│   ├── projects/           # 项目配置
│   ├── rules/              # 规则
│   ├── settings.json       # 全局设置
│   ├── skills/             # 技能配置
│   ├── snapshots/          # 配置快照
│   └── token_usage/        # Token 统计
│
├── storage/                # ✅ 运行时存储
│   ├── agent_states/       # Agent 状态
│   ├── agent-team/         # 团队状态
│   ├── conversations/      # 对话历史
│   ├── file-history/       # 文件历史缓存
│   ├── logs/               # 日志
│   ├── memory/             # 记忆数据
│   ├── network/            # 网络队列
│   ├── observability/      # 观测数据
│   ├── permissions/        # 权限记录
│   ├── projects/           # 项目缓存
│   ├── sessions/           # 会话状态
│   ├── skill_evolution/    # 技能进化
│   ├── snapshots/          # 状态快照
│   ├── stream_states/      # 流状态
│   └── token_usage/        # Token 使用
│
├── frontend/               # ✅ Web UI
├── docs/                   # ✅ 文档
├── tests/                  # ✅ 测试（唯一）
├── scripts/                # ✅ 脚本工具
├── extensions/             # ✅ 扩展包
├── openclaw/               # 参考项目（只读）
│
└── [配置文件]
    ├── pyproject.toml      # Python 项目配置
    ├── .gitignore          # Git 忽略
    ├── .env.example        # 环境变量示例
    ├── .mcp.json           # MCP 配置
    ├── package.json        # Node.js 依赖
    └── pnpm-lock.yaml      # pnpm 锁定
```

---

## 三、删除的文件和目录

### 源代码目录
- ❌ `src/` - 19 个子目录，与 `mul_agent/` 重复
- ❌ `agents/` - 6 个 Agent 配置，与 `wang/agent-team/` 重复
- ❌ `skills/` - 13 个技能，与 `mul_agent/skills/` 重复
- ❌ `test/` - 6 个子目录，与 `tests/` 重复

### 废弃文件
- ❌ `main.py` - 旧入口文件
- ❌ `mul_agent_cli.py` - 旧 CLI 脚本
- ❌ `run_tests.sh` - 旧测试脚本
- ❌ `favicon.svg` - 未使用
- ❌ `docs-mint/` - 空目录

### 缓存目录
- ❌ `.pytest_cache/`
- ❌ `.ruff_cache/`
- ❌ `node_modules/` (根目录)
- ❌ `frontend/node_modules/`

### 过期文档
- ❌ `docs/优化方案`
- ❌ `docs/归档`
- ❌ `docs/测试报告`
- ❌ `docs/todo`
- ❌ `docs/规则`
- ❌ `docs/help`
- ❌ `docs/installation`
- ❌ `docs/introduction`
- ❌ `docs/start`
- ❌ `docs/gateway`
- ❌ `docs/nodes`
- ❌ `docs/commands`
- ❌ `docs/cli`
- ❌ `docs/hooks`
- ❌ `docs/plugins`
- ❌ `docs/reference`
- ❌ `docs/skills`
- ❌ `docs/tools`

### 重复配置
- ❌ `AGENTS.md`
- ❌ `ARCHITECTURE.md`
- ❌ `CLAUDE.md`
- ❌ `mint.json`
- ❌ `.mintignore`
- ❌ `oxfmt.config.json`
- ❌ `oxlint.json`
- ❌ `ruff.toml`
- ❌ `requirements.txt`
- ❌ `storage/wang/`

### 空扩展
- ❌ `extensions/discord/`
- ❌ `extensions/memory-core/`
- ❌ `extensions/telegram/`

---

## 四、更新的文件

### pyproject.toml
```toml
# 之前
[project.scripts]
mul-agent = "src.cli:main"

[tool.setuptools.packages.find]
include = ["src*", "extensions*", "skills*"]

# 之后
[project.scripts]
mul-agent = "mul_agent.cli:main"

[tool.setuptools.packages.find]
include = ["mul_agent*"]
exclude = ["tests*", "extensions*", "skills*"]
```

### .gitignore
保持不变，已有的规则仍然适用。

---

## 五、清理结果

### 清理前
- 根目录：44 个目录/文件
- mul_agent 包：25 个子目录
- docs: 62 个子目录

### 清理后
- 根目录：23 个目录/文件 ⬇️ 48%
- mul_agent 包：18 个子目录 ⬇️ 28%
- docs: 46 个子目录 ⬇️ 26%

### 磁盘空间释放
- 约 50MB (主要是 node_modules 和缓存)

---

## 六、后续工作

### 1. 文档整理
- [ ] 合并重复的文档目录 (guide/guides, concepts/introduction)
- [ ] 更新文档索引
- [ ] 删除过时的报告文件

### 2. 代码迁移
- [ ] 确认所有 src/ 的代码已迁移到 mul_agent/
- [ ] 删除对旧路径的引用

### 3. 测试验证
- [ ] 运行测试确保功能正常
- [ ] 更新测试路径配置

---

## 七、参考

- [架构改造报告](./docs/ARCHITECTURE_REFACTOR_REPORT.md)
- [SKILL.md 迁移指南](./docs/AGENT_SKILL_MIGRATION.md)
