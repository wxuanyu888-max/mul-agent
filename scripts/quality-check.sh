#!/bin/bash
# Mul-Agent Code Quality Check Script
# Run all code quality checks

set -e

echo "======================================"
echo "  Mul-Agent Code Quality Check"
echo "======================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ERRORS=0

# Python checks
echo "🐍 Python Checks"
echo "--------------------------------------"

if command -v ruff &> /dev/null; then
    echo "Running Ruff lint..."
    if ruff check mul_agent/ scripts/; then
        echo -e "${GREEN}✓ Ruff lint passed${NC}"
    else
        echo -e "${RED}✗ Ruff lint failed${NC}"
        ((ERRORS++))
    fi

    echo "Running Ruff format check..."
    if ruff format --check mul_agent/ scripts/; then
        echo -e "${GREEN}✓ Ruff format passed${NC}"
    else
        echo -e "${YELLOW}⚠ Ruff format needs fixes${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Ruff not installed, skipping Python checks${NC}"
fi

echo ""

# TypeScript/JavaScript checks
echo "📦 TypeScript/JavaScript Checks"
echo "--------------------------------------"

if command -v pnpm &> /dev/null && [ -f "package.json" ]; then
    echo "Running Oxlint..."
    if pnpm lint; then
        echo -e "${GREEN}✓ Oxlint passed${NC}"
    else
        echo -e "${YELLOW}⚠ Oxlint has warnings${NC}"
    fi

    echo "Running Oxfmt check..."
    if pnpm format:check; then
        echo -e "${GREEN}✓ Oxfmt passed${NC}"
    else
        echo -e "${YELLOW}⚠ Oxfmt needs formatting${NC}"
    fi

    echo "Running TypeScript type check..."
    if pnpm typecheck 2>/dev/null; then
        echo -e "${GREEN}✓ TypeScript check passed${NC}"
    else
        echo -e "${YELLOW}⚠ TypeScript check has issues${NC}"
    fi
else
    echo -e "${YELLOW}⚠ pnpm not available, skipping TS checks${NC}"
fi

echo ""

# Summary
echo "======================================"
echo "  Summary"
echo "======================================"

if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}✗ Quality check failed with $ERRORS error(s)${NC}"
    exit 1
else
    echo -e "${GREEN}✓ All critical checks passed${NC}"
    echo ""
    echo "Note: Warnings are non-blocking. Consider fixing them for better code quality."
fi
