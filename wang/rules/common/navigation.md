---
name: navigation
description: 导航规则 - 规定不同情况调用不同的 skill、mcp、agent、command 和 hook
---

# 导航规则

> 规定在什么情况下调用什么 skill、mcp、agent、command 或 hook。

---

## 一、Skill 详细导航

### 通用技能

| Skill | 触发场景 |
|-------|----------|
| `project_control` | - 新项目启动时<br>- 需求不清晰时<br>- 开发过程容易跑偏时<br>- 交付结果和预期不符时<br>- 每次开始新任务前 |
| `coding-standards` | - 写任何代码时<br>- 代码审查时<br>- 重构代码时<br>- 设置 linting/formatting 时 |
| `tdd-workflow` | - 写新功能时<br>- 修复 bug 时<br>- 重构代码时<br>- 需要先写测试再写代码时 |
| `search-first` | - 不知道用什么技术时<br>- 需要研究方案时<br>- 遇到新领域时<br>- 不确定最佳实践时 |
| `verification-loop` | - 部署前<br>- 发布前<br>- 代码合并前<br>- 需要完整验证时 |
| `eval-harness` | - 需要评估 Claude Code 会话时<br>- 需要 formal evaluation 时 |

### 前端技能

| Skill | 触发场景 |
|-------|----------|
| `frontend-patterns` | - React 项目开发时<br>- Next.js 项目开发时<br>- 需要前端组件时<br>- 需要状态管理时 |
| `e2e-testing` | - 需要端到端测试时<br>- Playwright 测试时<br>- 关键用户流程验证时 |

### 后端技能

| Skill | 触发场景 |
|-------|----------|
| `backend-patterns` | - 后端 API 开发时<br>- Node.js/Express 项目时<br>- 需要数据库操作时<br>- 需要设计 API 时 |
| `api-design` | - 设计 REST API 时<br>- 定义接口规范时<br>- 需要 API 文档时 |
| `deployment-patterns` | - 部署应用时<br>- CI/CD 配置时<br>- Docker 容器化时 |
| `docker-patterns` | - 使用 Docker 时<br>- docker-compose 配置时<br>- 容器编排时 |

### Python 技能

| Skill | 触发场景 |
|-------|----------|
| `python-patterns` | - 写 Python 代码时<br>- Flask/FastAPI 项目时<br>- Python 项目审查时 |
| `python-testing` | - 写 pytest 测试时<br>- Python 单元测试时<br>- 需要测试覆盖率时 |

### Go 技能

| Skill | 触发场景 |
|-------|----------|
| `golang-patterns` | - 写 Go 代码时<br>- Go 项目开发时<br>- 需要 Go 惯用模式时 |
| `golang-testing` | - 写 Go 测试时<br>- table-driven tests 时<br>- benchmark 测试时 |

### Java 技能

| Skill | 触发场景 |
|-------|----------|
| `java-coding-standards` | - Java 项目开发时<br>- Spring Boot 项目时 |
| `jpa-patterns` | - JPA/Hibernate 使用时<br>- 数据库 ORM 操作时<br>- Entity 设计时 |

### Django 技能

| Skill | 触发场景 |
|-------|----------|
| `django-patterns` | - Django 项目开发时<br>- DRF API 开发时<br>- Django 模型设计时 |
| `django-security` | - Django 安全配置时<br>- 认证/授权实现时<br>- 安全审查时 |
| `django-tdd` | - Django 项目 TDD 时<br>- Django 测试时 |
| `django-verification` | - Django 项目验证时<br>- 部署前检查时 |

### Spring Boot 技能

| Skill | 触发场景 |
|-------|----------|
| `springboot-patterns` | - Spring Boot 项目开发时<br>- REST API 开发时 |
| `springboot-security` | - Spring Security 配置时<br>- 安全认证实现时 |
| `springboot-tdd` | - Spring Boot TDD 时<br>- JUnit 测试时 |
| `springboot-verification` | - Spring Boot 验证时<br>- 部署前检查时 |

### C++ 技能

| Skill | 触发场景 |
|-------|----------|
| `cpp-coding-standards` | - C++ 项目开发时<br>- C++ 代码审查时 |
| `cpp-testing` | - C++ 测试时<br>- GoogleTest 使用时 |

### 数据库技能

| Skill | 触发场景 |
|-------|----------|
| `postgres-patterns` | - PostgreSQL 使用时<br>- SQL 优化时<br>- 数据库设计时 |
| `database-migrations` | - 数据库迁移时<br>- Schema 变更时<br>- 数据迁移时 |
| `clickhouse-io` | - ClickHouse 使用时<br>- 分析查询时<br>- 大数据查询时 |

### 安全技能

| Skill | 触发场景 |
|-------|----------|
| `security-review` | - 添加认证时<br>- 处理用户输入时<br>- 实现支付时<br>- 安全审查时 |
| `security-scan` | - 扫描 Claude 配置时<br>- 检查安全漏洞时 |

### 其他技能

| Skill | 触发场景 |
|-------|----------|
| `cost-aware-llm-pipeline` | - LLM API 成本优化时<br>- 模型选择时 |
| `content-hash-cache-pattern` | - 需要缓存时<br>- 文件处理优化时 |
| `continuous-learning` | - 需要学习模式时<br>- 提取技能时 |
| `continuous-learning-v2` | - 基于观察学习时<br>- 本能系统时 |
| `iterative-retrieval` | - 上下文检索时<br>- 需要迭代检索时 |
| `nutrient-document-processing` | - PDF 处理时<br>- DOCX 操作时<br>- OCR 识别时 |
| `project-guidelines-example` | - 参考项目结构时<br>- 示例项目开发时 |
| `regex-vs-llm-structured-text` | - 解析结构化文本时<br>- 正则 vs LLM 选择时 |
| `skill-stocktake` | - 审计 skills 时<br>- 检查 skill 质量时 |
| `strategic-compact` | - 上下文压缩时<br>- 长时间会话时 |
| `swift-actor-persistence` | - Swift 持久化时<br>- 线程安全时 |
| `swift-protocol-di-testing` | - Swift 依赖注入时<br>- Swift 测试时 |
| `configure-ecc` | - 配置 ECC 时<br>- 安装 skill 时 |

---

## 二、Agent 详细导航

| Agent | 触发场景 |
|-------|----------|
| `planner` | - 复杂功能规划时<br>- 需要分步骤实施时<br>- 新功能开发前 |
| `architect` | - 架构设计时<br>- 系统设计时<br>- 技术选型时 |
| `tdd-guide` | - TDD 开发时<br>- 遇到 bug 时<br>- 需要测试指导时 |
| `code-reviewer` | - 代码审查时<br>- 提交代码前<br>- PR 审查时 |
| `python-reviewer` | - Python 代码审查时<br>- PEP 8 检查时 |
| `go-reviewer` | - Go 代码审查时<br>- Go 惯用模式检查时 |
| `security-reviewer` | - 安全审查时<br>- 认证/授权检查时 |
| `build-error-resolver` | - 构建失败时<br>- TypeScript 错误时 |
| `go-build-resolver` | - Go 构建失败时<br>- Go vet 警告时 |
| `e2e-runner` | - E2E 测试时<br>- 关键流程测试时 |
| `refactor-cleaner` | - 死代码清理时<br>- 代码重构时 |
| `doc-updater` | - 文档更新时<br>- 需要同步文档时 |
| `database-reviewer` | - 数据库审查时<br>- SQL 优化时 |

---

## 三、MCP 详细导航

| MCP | 触发场景 |
|-----|----------|
| `github` | - 创建 PR 时<br>- 查看 issues 时<br>- 操作仓库时<br>- 提交代码时 |
| `firecrawl` | - 网页抓取时<br>- 爬取数据时<br>- Web scraping 时 |
| `supabase` | - Supabase 操作时<br>- PostgreSQL 交互时<br>- 实时数据时 |
| `memory` | - 需要持久记忆时<br>- 跨会话记忆时<br>- 保存重要信息时 |
| `sequential-thinking` | - 复杂推理时<br>- 链式思考时<br>- 需要分析问题时 |
| `vercel` | - Vercel 部署时<br>- Next.js 部署时 |
| `railway` | - Railway 部署时 |
| `cloudflare-docs` | - Cloudflare 文档查询时 |
| `cloudflare-workers-builds` | - Workers 构建时 |
| `cloudflare-workers-bindings` | - Workers 绑定时 |
| `cloudflare-observability` | - 日志查看时<br>- 监控数据时 |
| `clickhouse` | - ClickHouse 查询时<br>- 分析数据时 |
| `context7` | - 文档查询时<br>- API 文档查看时<br>- 库文档查找时 |
| `magic` | - 需要 Magic UI 组件时 |
| `filesystem` | - 文件系统操作时 |

---

## 四、Command 详细导航

| Command | 触发场景 |
|---------|----------|
| `/tdd` | - 开始 TDD 开发时<br>- 先写测试时 |
| `/code-review` | - 代码审查时 |
| `/build-fix` | - 构建失败时 |
| `/go-build` | - Go 构建失败时 |
| `/go-review` | - Go 代码审查时 |
| `/go-test` | - Go 测试时<br>- 需要覆盖率时 |
| `/e2e` | - E2E 测试时 |
| `/verify` | - 验证时<br>- 部署前检查时 |
| `/test-coverage` | - 检查覆盖率时 |
| `/plan` | - 制定计划时<br>- 规划任务时 |
| `/multi-plan` | - 多模型协作规划时 |
| `/multi-execute` | - 多模型协作执行时 |
| `/multi-workflow` | - 多模型工作流时 |
| `/multi-backend` | - 后端开发时 |
| `/multi-frontend` | - 前端开发时 |
| `/learn` | - 提取模式时<br>- 学习新模式时 |
| `/learn-eval` | - 评估学习质量时 |
| `/evolve` | - 聚合成 skill 时 |
| `/skill-create` | - 创建 skill 时 |
| `/refactor-clean` | - 清理死代码时 |
| `/checkpoint` | - 保存检查点时 |
| `/sessions` | - 会话管理时 |
| `/eval` | - 评估会话时 |
| `/pm2` | - PM2 管理时 |
| `/python-review` | - Python 代码审查时 |
| `/update-docs` | - 更新文档时 |
| `/update-codemaps` | - 更新 codemaps 时 |

---

## 五、Hook 详细导航

### PreToolUse（执行前）

| Hook | 触发场景 |
|------|----------|
| 阻止非 tmux 运行 dev server | - 执行 `npm run dev` 时<br>- 执行 `pnpm dev` 时<br>- 执行 `yarn dev` 时 |
| 提醒使用 tmux | - 执行 `npm install` 时<br>- 执行 `pytest` 时<br>- 执行 `docker` 时 |
| 提醒 git push | - 执行 `git push` 时 |
| 阻止创建随机 .md 文件 | - 创建不必要的 markdown 文件时 |
| 建议压缩 | - Edit/Write 操作频繁时 |

### PostToolUse（执行后）

| Hook | 触发场景 |
|------|----------|
| 记录 PR URL | - 创建 PR 后 |
| 异步构建分析 | - `npm run build` 执行后 |
| 自动格式化 | - Edit .ts/.tsx 文件后 |
| 类型检查 | - Edit .ts/.tsx 文件后 |
| console 警告 | - Edit 操作后 |

### SessionStart

| Hook | 触发场景 |
|------|----------|
| 加载上次上下文 | - 新会话开始时 |
| 检测包管理器 | - 新会话开始时 |

### SessionEnd

| Hook | 触发场景 |
|------|----------|
| 持久化状态 | - 会话结束时 |
| 评估模式 | - 会话结束时 |

---

## 六、常用场景组合

| 场景 | 推荐调用 |
|------|----------|
| 新项目启动 | `project_control` → `search-first` |
| 新功能开发 | `planner` → `project_control` → `/tdd` → `coding-standards` |
| Bug 修复 | `tdd-guide` → `/build-fix` → `code-reviewer` |
| 代码审查 | `code-reviewer` → `security-reviewer` |
| 性能优化 | `backend-patterns` → `database-reviewer` |
| 部署上线 | `deployment-patterns` → `/verify` |
| 学习新框架 | `search-first` → `context7` MCP |
| 需要记忆 | `memory` MCP |
| 需要推理 | `sequential-thinking` MCP |
| Python 开发 | `python-patterns` → `/tdd` → `python-testing` |
| Go 开发 | `golang-patterns` → `/tdd` → `/go-test` |
| 前端开发 | `frontend-patterns` → `e2e-testing` |
| Django 开发 | `django-patterns` → `django-tdd` → `django-verification` |
| Spring Boot 开发 | `springboot-patterns` → `springboot-tdd` → `springboot-verification` |

---

## 七、执行原则

1. **先判断任务类型** - 再选择对应 Skill/Agent
2. **不知道用什么时** - 先用 `search-first`
3. **复杂任务** - 使用多个 Agent 并行执行
4. **完成后** - 触发对应 Hook 进行检查
5. **需要持久记忆** - 使用 `memory` MCP
6. **需要推理** - 使用 `sequential-thinking` MCP
