# Mul-Agent 代码质量和文档系统

本文档说明如何在 mul-agent 项目中使用代码质量工具和文档系统。

---

## 目录

1. [Oxlint - TypeScript/JavaScript 检查](#oxlint---typescriptjavascript-检查)
2. [Oxfmt - TypeScript/JavaScript 格式化](#oxfmt---typescriptjavascript-格式化)
3. [Ruff - Python 检查和格式化](#ruff---python-检查和格式化)
4. [Mintlify - 文档系统](#mintlify---文档系统)
5. [快捷脚本](#快捷脚本)

---

## Oxlint - TypeScript/JavaScript 检查

**Oxlint** 是一个快速的 JavaScript/TypeScript linter。

### 安装

```bash
# 安装项目依赖
pnpm install
```

### 使用

```bash
# 根目录
pnpm lint          # 运行检查
pnpm lint:fix      # 自动修复问题
pnpm lint:ci       # CI 格式输出

# Frontend
cd frontend
pnpm lint
pnpm lint:fix
```

### 配置

配置文件：`oxlint.json`

```json
{
  "rules": {
    "no-unused-vars": "warn",
    "no-console": "off",
    "prefer-const": "warn"
  }
}
```

---

## Oxfmt - TypeScript/JavaScript 格式化

**Oxfmt** 是一个快速的代码格式化工具。

### 使用

```bash
# 根目录
pnpm format          # 格式化代码
pnpm format:check    # 检查格式
pnpm format:write    # 写入格式化

# Frontend
cd frontend
pnpm format
```

### 配置

配置文件：`oxfmt.config.json`

```json
{
  "include": ["**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules", "dist"],
  "indent_width": 2,
  "line_width": 100
}
```

---

## Ruff - Python 检查和格式化

**Ruff** 是一个快速的 Python linter 和 formatter。

### 安装

```bash
pip install ruff
```

### 使用

```bash
# 检查
ruff check mul_agent/
ruff check tests/

# 格式化
ruff format mul_agent/
ruff format tests/

# 自动修复
ruff check --fix mul_agent/
```

### 配置

配置文件：`ruff.toml`

```toml
[tool.ruff]
line-length = 100
target-version = "py313"
```

---

## Mintlify - 文档系统

**Mintlify** 是一个现代化的文档平台。

### 设置

```bash
# 运行设置脚本
./scripts/setup-docs.sh
```

### 启动本地服务器

```bash
npx mintlify dev
```

### 添加新文档

1. 在 `docs/` 目录创建 `.mdx` 文件
2. 在 `mint.json` 中注册页面

示例文档：

```mdx
---
title: 页面标题
description: 页面描述
---

# 标题

内容...
```

### 配置

配置文件：`mint.json`

```json
{
  "pages": [
    {
      "group": "快速开始",
      "pages": ["introduction", "getting-started"]
    }
  ]
}
```

---

## 快捷脚本

### quality-check.sh

运行所有代码质量检查：

```bash
./scripts/quality-check.sh
```

输出示例：

```
🔍 Mul-Agent 代码质量检查
========================

🐍 Python 代码检查...
  运行 Ruff 检查...
  ✅ Python 检查通过

📦 TypeScript/JavaScript 检查...
  运行 Oxlint...
  ✅ TypeScript 检查通过

========================
检查完成!
  错误：0
  警告：0
✅ 所有检查通过
```

### setup-docs.sh

设置文档系统：

```bash
./scripts/setup-docs.sh
```

---

## CI/CD 集成

### GitHub Actions 示例

```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'

      - name: Install dependencies
        run: |
          npm install -g pnpm
          pnpm install
          pip install ruff

      - name: Run quality checks
        run: ./scripts/quality-check.sh
```

---

## 最佳实践

1. **提交前运行检查** - 确保代码质量
2. **使用自动格式化** - 保持代码风格一致
3. **文档与代码同步** - 及时更新文档
4. **CI 检查** - 自动化质量保障

---

## 故障排除

### Oxlint 不工作

确保已安装依赖：
```bash
pnpm install
```

### Mintlify 不启动

检查 Node.js 版本：
```bash
node --version  # 需要 18+
```

### Ruff 未找到

安装 Ruff：
```bash
pip install ruff
```
