# mul-agent 与 openclaw 目录结构差异报告

> 生成时间：2026-03-09

---

## 一、根目录差异

### mul-agent 有但 openclaw 没有的目录/文件

| 名称 | 类型 | 说明 |
|------|------|------|
| `channels/` | 目录 | 消息通道（新增） |
| `CLEANUP_REPORT.md` | 文件 | 清理报告 |
| `frontend/` | 目录 | Web UI |
| `mint.json` | 文件 | Mintlify 配置 |
| `mul_agent/` | 目录 | 原始代码（需要迁移到 src/） |
| `node_modules/` | 目录 | npm 依赖 |
| `openclaw/` | 目录 | openclaw 参考副本 |
| `oxfmt.config.json` | 文件 | 格式化配置 |
| `oxlint.json` | 文件 | Lint 配置 |
| `storage/` | 目录 | 数据存储 |
| `tests/` | 目录 | 测试（需要迁移到 test/） |
| `wang/` | 目录 | 项目配置和数据 |

### openclaw 有但 mul-agent 没有的目录/文件

| 名称 | 类型 | 说明 | 优先级 |
|------|------|------|--------|
| `AGENTS.md` | 文件 | 项目指南 | 高 |
| `apps/` | 目录 | 移动/桌面应用 | 中 |
| `assets/` | 目录 | 静态资源 | 低 |
| `CHANGELOG.md` | 文件 | 变更日志 | 中 |
| `CLAUDE.md` | 文件 | CLAUDE 指南（ symlink 到 AGENTS.md） | 高 |
| `CONTRIBUTING.md` | 文件 | 贡献指南 | 中 |
| `docker-compose.yml` | 文件 | Docker 配置 | 低 |
| `Dockerfile*` | 文件 | Docker 镜像 | 低 |
| `docs.acp.md` | 文件 | ACP 文档 | 低 |
| `fly.toml` | 文件 | Fly.io 配置 | 低 |
| `knip.config.ts` | 文件 | Knip 配置 | 低 |
| `LICENSE` | 文件 | 许可证 | 高 |
| `openclaw.mjs` | 文件 | CLI 入口 | 高 |
| `packages/` | 目录 | npm 包 | 中 |
| `patches/` | 目录 | npm patch 文件 | 低 |
| `pnpm-workspace.yaml` | 文件 | pnpm 工作区 | 中 |
| `pyproject.toml` | 文件 | Python 配置 | 已有 |
| `render.yaml` | 文件 | Render 配置 | 低 |
| `SECURITY.md` | 文件 | 安全策略 | 高 |
| `scripts/` | 目录 | 脚本（已有但不完整） | 高 |
| `Swabble/` | 目录 | 游戏项目 | 不需要 |
| `test-fixtures/` | 目录 | 测试夹具（已创建 test/fixtures/） | 中 |
| `tsconfig*.json` | 文件 | TypeScript 配置 | 中 |
| `tsdown.config.ts` | 文件 | 构建配置 | 中 |
| `ui/` | 目录 | UI 源代码 | 已有 frontend/ |
| `vendor/` | 目录 | 第三方库 | 低 |
| `VISION.md` | 文件 | 项目愿景 | 中 |
| `vitest.*.config.ts` | 文件 | 测试配置 | 高 |
| `zizmor.yml` | 文件 | GitHub Actions lint | 低 |
| `.detect-secrets.cfg` | 文件 | 密钥检测配置 | 高 |
| `.dockerignore` | 文件 | Docker 忽略 | 低 |
| `.env.example` | 文件 | 环境变量示例 | 高 |
| `.gitattributes` | 文件 | Git 属性 | 中 |
| `.github/` | 目录 | GitHub 配置 | 高 |
| `.mailmap` | 文件 | Git 邮件映射 | 低 |
| `.markdownlint-cli2.jsonc` | 文件 | Markdown lint | 中 |
| `.npmrc` | 文件 | npm 配置 | 中 |
| `.oxfmtrc.jsonc` | 文件 | 格式化配置 | 中 |
| `.oxlintrc.json` | 文件 | Lint 配置 | 中 |
| `.pi/` | 目录 | Pi 配置 | 低 |
| `.pre-commit-config.yaml` | 文件 | Pre-commit 配置 | 高 |
| `.secrets.baseline` | 文件 | 密钥基线 | 高 |
| `.shellcheckrc` | 文件 | ShellCheck 配置 | 中 |
| `.swiftformat` | 文件 | Swift 格式化 | 不需要 |
| `.swiftlint.yml` | 文件 | Swift lint | 不需要 |
| `.vscode/` | 目录 | VSCode 配置 | 已有 |

---

## 二、src/ 目录结构差异

### openclaw/src/ 有但 mul-agent/src/ 没有的模块

| 模块 | 说明 | 是否需要 |
|------|------|----------|
| `acp/` | ACP 运行时 | 需要 |
| `auto-reply/` | 自动回复 | 需要 |
| `browser/` | 浏览器集成 | 需要 |
| `canvas-host/` | Canvas 宿主 | 需要 |
| `channel-web.ts` | Web 通道 | 已有 channels/ |
| `compat/` | 兼容性层 | 需要 |
| `context-engine/` | 上下文引擎 | 需要 |
| `cron/` | 定时任务 | 需要 |
| `i18n/` | 国际化 | 需要 |
| `infra/` | 基础设施 | 需要 |
| `link-understanding/` | 链接理解 | 需要 |
| `markdown/` | Markdown 处理 | 需要 |
| `media/` | 媒体处理 | 需要 |
| `media-understanding/` | 媒体理解 | 需要 |
| `pairing/` | 配对功能 | 需要 |
| `plugin-sdk/` | 插件 SDK | 需要 |
| `process/` | 进程管理 | 需要 |
| `providers/` | 提供者 | 需要 |
| `routing/` | 路由 | 需要 |
| `secrets/` | 密钥管理 | 需要 |
| `security/` | 安全模块 | 需要 |
| `terminal/` | 终端 UI | 需要 |
| `test-helpers/` | 测试辅助 | 已有 test/helpers/ |
| `test-utils/` | 测试工具 | 已有 test/ |
| `tts/` | 语音合成 | 需要 |
| `tui/` | TUI | 需要 |
| `wizard/` | 向导 | 需要 |

### mul-agent/src/ 有但 openclaw/src/ 没有的模块

| 模块 | 说明 | 调整建议 |
|------|------|----------|
| `api/` | API 服务器 | 移动到 gateway/ |
| `core/` | 核心逻辑 | 合并到 agents/ |
| `extensions/` | 扩展 | 移动到 extensions/ |
| `mcp/` | MCP 客户端 | 保留或移动到 plugins/ |
| `memory/` | 记忆系统 | 保留 |
| `network/` | 网络 | 合并到 infra/ |
| `observability/` | 可观测性 | 合并到 logging/ |
| `parallel/` | 并行执行 | 保留 |
| `repositories/` | 数据仓库 | 保留 |

---

## 三、docs/ 目录结构差异

### openclaw/docs/ 有但 mul-agent/docs/ 没有的子目录

| 子目录 | 说明 |
|--------|------|
| `assets/` | 文档资源 |
| `automation/` | 自动化文档 |
| `channels/` | 通道文档 |
| `debug/` | 调试指南 |
| `design/` | 设计文档 |
| `diagnostics/` | 诊断 |
| `experiments/` | 实验 |
| `gateway/security/` | Gateway 安全 |
| `images/` | 图片 |
| `install/` | 安装指南 |
| `ja-JP/` | 日文文档 |
| `nodes/` | 节点文档 |
| `platforms/` | 平台文档 |
| `providers/` | 提供者文档 |
| `reference/templates/` | 模板参考 |
| `security/` | 安全文档 |
| `web/` | Web 文档 |

---

## 四、skills/ 目录结构差异

### openclaw/skills/ 有的技能（约 54 个）

```
1password, apple-notes, apple-reminders, bear-notes, blogwatcher, blucli,
bluebubbles, camsnap, canvas, clawhub, coding-agent, discord, eightctl,
gemini, gh-issues, gifgrep, github, gog, goplaces, healthcheck, himalaya,
mcporter, model-usage, nano-banana-pro, nano-pdf, notion, obsidian,
openai-image-gen, openai-whisper, openai-whisper-api, openhue, oracle,
ordercli, peekaboo, sag, session-logs, sherpa-onnx-tts, skill-creator,
slack, songsee, sonoscli, spotify-player, summarize, things-mac, tmux,
trello, video-frames, voice-call, wacli, weather, xurl
```

### mul-agent/skills/ 需要的技能

```
bash, read, write, edit, glob, grep, git, memory, search, web_fetch, web_git
```

---

## 五、extensions/ 目录结构差异

### openclaw/extensions/ 有的扩展（约 42 个）

```
acpx, bluebubbles, copilot-proxy, device-pair, diagnostics-otel, diffs,
discord, feishu, google-gemini-cli-auth, googlechat, imessage, irc, line,
llm-task, lobster, matrix, mattermost, memory-core, memory-lancedb,
minimax-portal-auth, msteams, nextcloud-talk, nostr, open-prose,
phone-control, qwen-portal-auth, shared, signal, slack, synology-chat,
talk-voice, telegram, test-utils, thread-ownership, tl on, twitch,
voice-call, whatsapp, zalo, zalouser
```

### mul-agent/extensions/ 状态

- 当前为空或仅有基础结构
- 需要创建基础扩展示例

---

## 六、test/ 目录结构差异

### openclaw/test/ 结构

```
test/
├── fixtures/          # 测试夹具（10 个子目录）
├── helpers/           # 测试辅助（16 个文件）
├── mocks/             # Mock 对象
├── scripts/           # 测试脚本（7 个子目录）
├── *.test.ts          # 测试文件（多个）
├── setup.ts           # 测试设置
├── test-env.ts        # 测试环境
└── global-setup.ts    # 全局设置
```

### mul-agent/test/ 状态

- 已创建基础目录结构
- 缺少实际测试文件和辅助代码

---

## 七、需要创建的配置文件

### 高优先级

1. `AGENTS.md` - 项目主指南
2. `CLAUDE.md` - 符号链接到 AGENTS.md
3. `LICENSE` - 许可证文件
4. `SECURITY.md` - 安全策略
5. `CONTRIBUTING.md` - 贡献指南
6. `.env.example` - 环境变量示例
7. `.pre-commit-config.yaml` - Pre-commit 配置
8. `.detect-secrets.cfg` - 密钥检测配置
9. `vitest.config.ts` - 测试配置
10. `tsconfig.json` - TypeScript 配置
11. `pnpm-workspace.yaml` - pnpm 工作区配置
12. `knip.config.ts` - Knip 配置
13. `.github/` - GitHub 配置目录
14. `openclaw.mjs` 或等效 CLI 入口

### 中优先级

1. `CHANGELOG.md` - 变更日志
2. `VISION.md` - 项目愿景
3. `apps/` - 移动/桌面应用
4. `assets/` - 静态资源
5. `packages/` - npm 包
6. `.gitattributes` - Git 属性
7. `.markdownlint-cli2.jsonc` - Markdown lint
8. `.npmrc` - npm 配置
9. `.oxfmtrc.jsonc` - 格式化配置
10. `.oxlintrc.json` - Lint 配置
11. `.shellcheckrc` - ShellCheck 配置
12. `.vscode/` - VSCode 设置

### 低优先级

1. `docker-compose.yml` - Docker 配置
2. `Dockerfile*` - Docker 镜像
3. `fly.toml` - Fly.io 配置
4. `render.yaml` - Render 配置
5. `patches/` - npm patch 文件
6. `vendor/` - 第三方库
7. `.mailmap` - Git 邮件映射
8. `.pi/` - Pi 配置
9. Swift 相关配置（.swiftformat, .swiftlint.yml）

---

## 八、行动计划

### 阶段一：核心结构（已完成）

- [x] 创建 `.agents/` 目录
- [x] 创建 `.agent/` 目录
- [x] 创建 `channels/` 目录
- [x] 创建 `git-hooks/` 目录
- [x] 创建 `skills/` 目录
- [x] 创建 `test/` 目录
- [x] 创建 `src/` 目录并迁移代码

### 阶段二：配置文件（进行中）

- [ ] 创建 `AGENTS.md`
- [ ] 创建 `CLAUDE.md` 符号链接
- [ ] 创建 `LICENSE`
- [ ] 创建 `SECURITY.md`
- [ ] 创建 `.env.example`
- [ ] 创建 `.pre-commit-config.yaml`
- [ ] 创建测试配置文件

### 阶段三：src/ 重构

- [ ] 将 `src/api/` 移动到 `src/gateway/`
- [ ] 将 `src/core/` 合并到 `src/agents/`
- [ ] 创建 `src/plugin-sdk/`
- [ ] 创建 `src/infra/`
- [ ] 创建 `src/security/`
- [ ] 创建 `src/secrets/`

### 阶段四：docs/ 完善

- [ ] 创建 `docs/install/`
- [ ] 创建 `docs/channels/`
- [ ] 创建 `docs/gateway/`
- [ ] 创建 `docs/security/`
- [ ] 创建 `docs/zh-CN/` 中文文档

### 阶段五：GitHub 配置

- [ ] 创建 `.github/` 目录
- [ ] 创建 Issue 模板
- [ ] 创建 PR 模板
- [ ] 配置 GitHub Actions
- [ ] 配置 labeler.yml

---

## 九、总结

mul-agent 项目已经完成了基础目录结构的创建，但与 openclaw 相比还有以下主要差异：

1. **配置文件缺失**：缺少多个重要的配置文件（AGENTS.md, LICENSE, SECURITY.md 等）
2. **src/ 结构不完整**：缺少约 25 个核心模块
3. **docs/ 分类不细**：需要按照 openclaw 的主题分类完善
4. **skills/ 需要充实**：需要创建更多技能的 SKILL.md 文件
5. **extensions/ 空白**：需要创建基础扩展示例
6. **test/ 待完善**：需要添加测试辅助代码和夹具
7. **GitHub 配置缺失**：.github/ 目录和相关配置

建议按照上述行动计划逐步完成改造。
