# Git 工作流

> 本项目 Git 版本控制规范

---

## 一、分支管理

### 1.1 分支模型

```
main              # 主分支，随时可部署
  ├── develop     # 开发分支
  │     ├── feature/login        # 功能分支
  │     ├── feature/dashboard    # 功能分支
  │     └── fix/auth-bug         # 修复分支
  └── release/v1.0              # 发布分支
```

### 1.2 分支命名

| 分支类型 | 命名格式 | 示例 |
|---------|---------|------|
| 主分支 | `main` | main |
| 开发分支 | `develop` | develop |
| 功能分支 | `feature/<name>` | feature/user-auth |
| 修复分支 | `fix/<name>` | fix/login-bug |
| 发布分支 | `release/<version>` | release/v1.0.0 |
| 热修复 | `hotfix/<name>` | hotfix/critical-bug |

---

## 二、提交规范

### 2.1 提交格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 2.2 Type 类型

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响功能） |
| `refactor` | 重构 |
| `test` | 测试相关 |
| `chore` | 构建/工具/配置 |

### 2.3 示例

```bash
# 新功能
git commit -m "feat(agent): 添加新的 bash 处理器"

# Bug 修复
git commit -m "fix(memory): 修复记忆泄漏问题"

# 文档更新
git commit -m "docs(readme): 更新快速开始指南"

# 重构
git commit -m "refactor(router): 简化路由分发逻辑"
```

### 2.4 完整提交示例

```bash
git commit -m "feat(agent): 添加 Agent 自省功能

实现 #heart 路由，支持 Agent 自我反思和改进

主要变更:
- 添加 HeartHandler 类
- 实现自省分析逻辑
- 添加配置优化建议

Closes #123"
```

---

## 三、工作流程

### 3.1 开发新功能

```bash
# 1. 从 main 创建功能分支
git checkout main
git pull origin main
git checkout -b feature/new-skill

# 2. 开发并提交
git add .
git commit -m "feat(skill): 添加新的搜索技能"

# 3. 推送到远程
git push -u origin feature/new-skill

# 4. 创建 Pull Request
# 在 GitHub/GitLab 上创建 PR

# 5. 合并后删除分支
git checkout main
git pull origin main
git branch -d feature/new-skill
```

### 3.2 修复 Bug

```bash
# 1. 从 main 创建修复分支
git checkout -b fix/memory-leak

# 2. 修复并提交
git commit -m "fix(memory): 修复长期记忆泄漏问题"

# 3. 推送并创建 PR
git push -u origin fix/memory-leak
```

---

## 四、Pull Request 规范

### 4.1 PR 标题

```
<type>: <简短描述>

示例:
feat: 添加用户登录功能
fix: 修复会话超时问题
```

### 4.2 PR 描述模板

```markdown
## 变更说明
- 变更 1
- 变更 2

## 测试计划
- [ ] 单元测试
- [ ] 集成测试
- [ ] 手动测试

## 检查清单
- [ ] 代码通过 lint
- [ ] 测试覆盖率 > 80%
- [ ] 文档已更新
```

---

## 五、版本管理

### 5.1 语义化版本

```
MAJOR.MINOR.PATCH
  │     │     │
  │     │     └─ 向后兼容的 Bug 修复
  │     └─────── 向后兼容的新功能
  └───────────── 不兼容的变更

示例:
1.0.0  # 初始版本
1.1.0  # 添加新功能
1.1.1  # Bug 修复
2.0.0  # 不兼容变更
```

### 5.2 打标签

```bash
# 创建标签
git tag -a v1.0.0 -m "Release v1.0.0"

# 推送标签
git push origin v1.0.0
```

---

## 六、Code Review

### 6.1 Review 要点

- [ ] 代码正确性
- [ ] 代码可读性
- [ ] 性能影响
- [ ] 安全性
- [ ] 测试覆盖

### 6.2 Review 评论

```markdown
## 代码审查意见

### ✅ 优点
- 代码结构清晰
- 测试完整

### ⚠️ 建议改进
- 第 23 行：函数过长，建议拆分
- 第 45 行：缺少错误处理

### ❌ 必须修复
- 第 67 行：硬编码的密钥，需要使用环境变量
```

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-03-08 | 初始版本 |
