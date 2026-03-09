# OpenClaw vs mul-agent 架构对比分析

**日期**: 2026-03-09
**目的**: 识别架构差异，指导 mul-agent 后续重构

---

## 一、根目录结构对比

### OpenClaw 根目录

```
openclaw/
├── openclaw.mjs              # 主入口 (TypeScript/ESM)
├── package.json              # 主配置 (5223 行，monorepo)
├── pnpm-workspace.yaml       # pnpm 工作区
├── tsconfig.json             # TypeScript 配置
├── vitest.config.ts          # 测试配置
├── .pre-commit-config.yaml   # Git hooks
├── docker-compose.yml        # Docker 编排
├── Dockerfile                # 容器构建
│
├── src/                      # 核心源代码 (77 个子目录)
├── extensions/               # 扩展插件 (42 个子目录)
├── skills/                   # 技能库 (54 个文件)
├── apps/                     # 应用程序 (6 个子目录)
├── ui/                       # Web UI 源代码
├── packages/                 # 共享包
├── scripts/                  # 脚本工具 (114 个)
├── docs/                     # 文档 (47 个子目录)
├── test/                     # 测试 (15 个子目录)
├── vendor/                   # 第三方代码
└── Swabble/                  # 游戏示例
```

### mul-agent 根目录

```
mul-agent/
├── mul_agent/                # Python 主包 (18 个子目录)
├── wang/                     # 配置和数据
├── storage/                  # 运行时存储
├── frontend/                 # Web UI (Vite + React)
├── extensions/               # 扩展包 (空)
├── scripts/                  # 脚本 (新建)
├── openclaw/                 # 参考项目 ( submodule)
├── docs/                     # 文档
└── tests/                    # 测试
```

---

## 二、核心源代码目录详细对比

### OpenClaw `src/` 模块 (77 个)

| 模块 | 说明 | 规模 |
|------|------|------|
| `agents/` | Agent 系统 | 538 文件 |
| `commands/` | 命令系统 | 295 文件 |
| `cli/` | CLI 入口 | 168 文件 |
| `plugin-sdk/` | 插件 SDK | 113 文件 |
| `plugins/` | 内置插件 | 68 文件 |
| `gateway/` | 网关系统 | 238 文件 |
| `channels/` | 消息渠道 | 65 文件 |
| `memory/` | 记忆系统 | 98 文件 |
| `config/` | 配置系统 | 207 文件 |
| `hooks/` | Hook 系统 | 38 文件 |
| `security/` | 安全模块 | 31 文件 |
| `cron/` | 定时任务 | 71 文件 |
| `sessions/` | 会话管理 | 14 文件 |
| `providers/` | 服务提供商 | 13 文件 |
| `routing/` | 路由系统 | 13 文件 |
| `utils/` | 工具函数 | 31 文件 |
| `shared/` | 共享代码 | 44 文件 |
| `types/` | 类型定义 | 11 文件 |
| `entry.ts` | 应用入口 | - |
| `index.ts` | 包导出 | - |

**渠道集成** (独立目录):
- `telegram/` (125 文件)
- `discord/` (73 文件)
- `slack/` (60 文件)
- `imessage/` (16 文件)
- `web/` (42 文件)
- `whatsapp/` (6 文件)
- `signal/` (28 文件)
- `line/` (45 文件)

### mul_agent `mul_agent/` 模块 (18 个)

| 模块 | 说明 | 状态 |
|------|------|------|
| `brain/` | Agent 大脑 | ✅ 31 文件 |
| `tools/` | 工具系统 | ✅ 15 子目录 |
| `commands/` | 命令系统 | ✅ 8 文件 |
| `hooks/` | Hook 系统 | ✅ 8 文件 |
| `memory/` | 记忆系统 | ✅ 11 文件 |
| `skills/` | 技能系统 | ✅ 8 文件 |
| `api/` | API 层 | ✅ 7 文件 |
| `core/` | 核心 Agent/Brain | ✅ 6 文件 |
| `plugins/` | 插件系统 | ✅ 7 文件 |
| `cli/` | CLI 入口 | ⚠️ 1 文件 |
| `mcp/` | MCP 客户端 | ✅ 4 文件 |
| `network/` | 网络系统 | ✅ 6 文件 |
| `observability/` | 可观测性 | ✅ 4 文件 |
| `parallel/` | 并行处理 | ✅ 7 文件 |
| `repositories/` | 数据仓库 | ✅ 8 文件 |
| `extensions/` | 扩展模块 | ❌ 空 |
| ~~`common/`~~ | ~~通用模块~~ | ❌ 已删除 |

---

## 三、关键架构差异

### 1. 入口点设计

| 方面 | OpenClaw | mul-agent |
|------|----------|-----------|
| **主入口** | `openclaw.mjs` → `dist/entry.js` | `mul_agent/main.py` (已删) |
| **CLI 入口** | `src/cli/` (168 文件) | `mul_agent/cli/__init__.py` (简单) |
| **网关入口** | `src/provider-web.ts` | `mul_agent/api/server.py` |
| **运行时** | Node 22+ ESM | Python 3.10+ |

**差距**: mul-agent 缺少统一的入口编排，CLI 功能薄弱

### 2. Agent 系统

| 方面 | OpenClaw | mul-agent |
|------|----------|-----------|
| **Agent 目录** | `src/agents/` (538 文件) | `wang/agent-team/` (配置文件) |
| **Agent 实现** | TypeScript 类 + 配置 | SKILL.md/YAML 配置 |
| **Agent 发现** | 自动扫描 + 注册 | 文件加载 |
| **Agent 身份** | `agent-identity.ts` | `soul.md` |
| **Agent 技能** | `agent-skills.ts` | `SKILL.md` |

**差距**: mul-agent 的 Agent 实现过度依赖配置文件，缺少运行时逻辑

### 3. 插件/扩展系统

| 方面 | OpenClaw | mul-agent |
|------|----------|-----------|
| **SDK** | `src/plugin-sdk/` (113 文件) | `mul_agent/plugins/` (7 文件) |
| **扩展** | `extensions/` (42 个包) | `extensions/` (空) |
| **内置插件** | `src/plugins/` (68 文件) | ❌ 无 |
| **工作区** | pnpm workspace | ❌ 无 |

**差距**: 插件 SDK 功能不完整，缺少示例扩展

### 4. 命令系统

| 方面 | OpenClaw | mul-agent |
|------|----------|-----------|
| **规模** | 295 文件 | ~8 文件 |
| **类型** | 内置 + 可插拔 | 内置 |
| **认证** | `auth-choice-*` 系列 | ❌ 无 |
| **安装器** | `install.ts` | ❌ 无 |

**差距**: 命令系统过于简化，缺少认证、安装等关键功能

### 5. Hook 系统

| 方面 | OpenClaw | mul-agent |
|------|----------|-----------|
| **规模** | 38 文件 | ~8 文件 |
| **类型** | Pre/Post/内部 | Pre/Post |
| **消息钩子** | `message-hook-mappers` | ❌ 无 |

### 6. 记忆系统

| 方面 | OpenClaw | mul-agent |
|------|----------|-----------|
| **规模** | 98 文件 | ~11 文件 |
| **存储** | LanceDB + 文件 | 文件系统 |
| **核心** | `memory-core.ts`, `memory-lancedb.ts` | `memory_manager.py` |

### 7. 渠道/通信集成

| 方面 | OpenClaw | mul-agent |
|------|----------|-----------|
| **渠道目录** | 独立目录 (telegram, discord 等) | ❌ 无 |
| **渠道 SDK** | `src/channels/` (65 文件) | ❌ 无 |
| **路由** | `src/routing/` (13 文件) | `mul_agent/brain/router.py` |

**差距**: mul-agent 完全没有多渠道通信支持

---

## 四、测试架构对比

### OpenClaw 测试

```
测试框架：Vitest
配置文件:
- vitest.config.ts (主配置)
- vitest.unit.config.ts (单元测试)
- vitest.e2e.config.ts (E2E 测试)
- vitest.live.config.ts (实时测试)
- vitest.extensions.config.ts (扩展测试)
- vitest.gateway.config.ts (网关测试)

测试目录:
- test/ (15 个子目录)
- src/**/*.test.ts ( colocated)
```

### mul-agent 测试

```
测试框架：pytest
配置文件：pyproject.toml
测试目录：tests/ (独立)
```

**差距**: 缺少测试配置分层，测试覆盖率不足

---

## 五、配置系统对比

### OpenClaw 配置

- `src/config/` (207 文件)
- `~/.openclaw/` (用户配置)
- 支持：auth-profiles, channel-config, device-identity

### mul-agent 配置

- `wang/agent-team/` (Agent 配置)
- `wang/settings.json` (全局设置)
- `pyproject.toml` (项目配置)

**差距**: 配置系统过于简化，缺少分层和加密

---

## 六、文档架构对比

### OpenClaw 文档

```
docs/
├── channels/          # 渠道文档
├── commands/          # 命令参考
├── configuration/     # 配置指南
├── extensions/        # 扩展开发
├── gateway/           # 网关联运
├── platforms/         # 平台指南
├── plugins/           # 插件开发
├── reference/         # API 参考
├── testing/           # 测试指南
└── zh-CN/            # 中文翻译 (生成)
```

### mul-agent 文档

```
docs/
├── concepts/          # 概念
├── getting-started/   # 入门
├── *.mdx              # Mintlify 格式
```

---

## 七、关键缺失模块

mul-agent 需要补充的核心模块：

1. **网关系统** (`gateway/`)
   - Web 提供者
   - 设备配对
   - 认证健康检查

2. **渠道集成** (`channels/`)
   - Telegram
   - Discord
   - Slack
   - WhatsApp
   - Signal

3. **配置系统** (`config/`)
   - 认证配置
   - 渠道配置
   - 设备身份

4. **安全模块** (`security/`)
   - SSRF 防护
   - Secret 管理
   - Webhook 验证

5. **定时任务** (`cron/`)
   - 任务调度
   - Cron 表达式解析
   - 任务过滤

6. **会话管理** (`sessions/`)
   - 会话存储
   - 会话历史
   - 会话恢复

7. **基础设施** (`infra/`)
   - Docker 集成
   - 进程管理
   - 日志系统

---

## 八、架构改进建议

### 阶段 1: 完善核心 (Week 1-2)

- [ ] 增强 CLI 系统
- [ ] 完善入口点编排
- [ ] 添加配置分层
- [ ] 实现设备身份

### 阶段 2: 插件系统 (Week 3-4)

- [ ] 完善插件 SDK
- [ ] 添加示例扩展
- [ ] 实现 pnpm workspace 类似的机制

### 阶段 3: 渠道集成 (Week 5-8)

- [ ] 实现基础渠道 SDK
- [ ] 添加 Telegram 支持
- [ ] 添加 Discord 支持

### 阶段 4: 安全和运维 (Week 9-10)

- [ ] 实现 SSRF 防护
- [ ] Secret 管理
- [ ] Docker 编排
- [ ] 日志系统

---

## 九、文件规模对比

| 指标 | OpenClaw | mul-agent | 差距 |
|------|----------|-----------|------|
| **源代码文件** | ~3000 | ~200 | 15x |
| **测试文件** | ~500 | ~20 | 25x |
| **文档** | 47 目录 | 6 目录 | 8x |
| **脚本** | 114 | 6 | 19x |
| **扩展/插件** | 42 | 0 | ∞ |

---

## 十、总结

mul-agent 目前处于 **早期阶段**，核心架构骨架已建立，但距离 OpenClaw 的成熟度还有很大差距。

**优先改进领域**:
1. CLI 系统增强
2. 配置系统完善
3. 插件 SDK 实用化
4. 基础渠道集成
5. 安全模块添加

**架构优势**:
- Python 生态更容易集成 AI/ML 工具
- 结构更简洁，学习曲线低
- 已经实现了核心的 Agent/Brain 概念

**下一步行动**:
参考 OpenClaw 的设计模式，逐步补充缺失模块，同时保持 Python 生态的优势。
