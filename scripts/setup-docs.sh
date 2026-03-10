#!/bin/bash
# Mul-Agent 文档设置脚本
# 用于初始化 Mintlify 文档系统

set -e

echo "🦄 Mul-Agent 文档设置"
echo "===================="

# 检查 Node.js 版本
if ! command -v node &> /dev/null; then
    echo "❌ 错误：需要 Node.js"
    echo "请先安装 Node.js (https://nodejs.org/)"
    exit 1
fi

# 检查 pnpm
if ! command -v pnpm &> /dev/null; then
    echo "📦 安装 pnpm..."
    npm install -g pnpm
fi

# 安装根目录依赖
echo "📦 安装项目依赖..."
pnpm install

# 安装 ui 依赖
echo "📦 安装 Frontend 依赖..."
cd ui && pnpm install && cd ..

# 创建文档目录结构
echo "📁 创建文档目录结构..."

DOCS_DIR="docs"

# 创建 Mintlify 所需的目录
mkdir -p "$DOCS_DIR/assets"
mkdir -p "$DOCS_DIR/logo"
mkdir -p "$DOCS_DIR/introduction"
mkdir -p "$DOCS_DIR/getting-started"
mkdir -p "$DOCS_DIR/installation"
mkdir -p "$DOCS_DIR/concepts"
mkdir -p "$DOCS_DIR/guide"
mkdir -p "$DOCS_DIR/api"
mkdir -p "$DOCS_DIR/deploy"

echo "✅ 文档设置完成!"
echo ""
echo "启动文档服务器:"
echo "  npx mintlify dev"
echo ""
echo "添加新文档:"
echo "  在 docs/ 目录下创建 .mdx 文件"
echo "  并在 mint.json 中注册页面"
