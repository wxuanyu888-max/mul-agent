#!/bin/bash
# Mul-Agent 代码质量检查脚本

set -e

echo "🔍 Mul-Agent 代码质量检查"
echo "========================"

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 计数器
ERRORS=0
WARNINGS=0

# Python 检查
echo ""
echo "🐍 Python 代码检查..."
if command -v ruff &> /dev/null; then
    echo "  运行 Ruff 检查..."
    if ! ruff check mul_agent/; then
        ((ERRORS++)) || true
        echo -e "${RED}  Python 检查失败${NC}"
    else
        echo -e "${GREEN}  Python 检查通过${NC}"
    fi

    echo "  运行 Ruff 格式化检查..."
    if ! ruff format --check mul_agent/; then
        ((WARNINGS++)) || true
        echo -e "${YELLOW}  Python 代码需要格式化${NC}"
    else
        echo -e "${GREEN}  Python 格式化通过${NC}"
    fi
else
    echo -e "${YELLOW}  ⚠️ Ruff 未安装，跳过 Python 检查${NC}"
    echo "  安装：pip install ruff"
fi

# TypeScript/JavaScript 检查
echo ""
echo "📦 TypeScript/JavaScript 检查..."
if command -v pnpm &> /dev/null; then
    if [ -f "package.json" ]; then
        echo "  运行 Oxlint..."
        if ! pnpm run lint; then
            ((ERRORS++)) || true
            echo -e "${RED}  TypeScript 检查失败${NC}"
        else
            echo -e "${GREEN}  TypeScript 检查通过${NC}"
        fi

        echo "  运行 Oxfmt 检查..."
        if ! pnpm run format:check; then
            ((WARNINGS++)) || true
            echo -e "${YELLOW}  代码需要格式化${NC}"
        else
            echo -e "${GREEN}  格式化检查通过${NC}"
        fi
    fi

    # Frontend 检查
    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        echo ""
        echo "🌐 Frontend 检查..."
        cd frontend

        echo "  运行 Oxlint..."
        if ! pnpm run lint; then
            ((ERRORS++)) || true
            echo -e "${RED}  Frontend 检查失败${NC}"
        else
            echo -e "${GREEN}  Frontend 检查通过${NC}"
        fi

        echo "  运行 Oxfmt 检查..."
        if ! pnpm run format:check; then
            ((WARNINGS++)) || true
            echo -e "${YELLOW}  Frontend 代码需要格式化${NC}"
        else
            echo -e "${GREEN}  Frontend 格式化通过${NC}"
        fi

        cd ..
    fi
else
    echo -e "${YELLOW}  ⚠️ pnpm 未安装，跳过 TypeScript 检查${NC}"
    echo "  安装：npm install -g pnpm"
fi

# 总结
echo ""
echo "========================"
echo "检查完成!"
echo "  错误：$ERRORS"
echo "  警告：$WARNINGS"

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}❌ 检查失败${NC}"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️ 检查通过但有警告${NC}"
else
    echo -e "${GREEN}✅ 所有检查通过${NC}"
fi
