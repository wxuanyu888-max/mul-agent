#!/bin/bash
# 同步项目配置到全局 ~/.claude
# 用法：./sync-to-global.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WANG_DIR="$SCRIPT_DIR"
GLOBAL_DIR="$HOME/.claude"

echo "=== 同步项目配置到全局 ~/.claude ==="
echo "源目录：$WANG_DIR"
echo "目标目录：$GLOBAL_DIR"
echo ""

# 同步技能库
if [ -d "$WANG_DIR/skills" ]; then
    echo "同步技能库到全局..."
    cp -r "$WANG_DIR/skills/"* "$GLOBAL_DIR/skills/" 2>/dev/null || true
    echo "  ✓ 技能库同步完成"
fi

# 同步规则库
if [ -d "$WANG_DIR/rules" ]; then
    echo "同步规则库到全局..."
    cp -r "$WANG_DIR/rules/"* "$GLOBAL_DIR/rules/" 2>/dev/null || true
    echo "  ✓ 规则库同步完成"
fi

# 同步命令
if [ -d "$WANG_DIR/commands" ]; then
    echo "同步命令到全局..."
    cp -r "$WANG_DIR/commands/"* "$GLOBAL_DIR/commands/" 2>/dev/null || true
    echo "  ✓ 命令同步完成"
fi

# 同步 MCP 配置
if [ -d "$WANG_DIR/mcp-configs" ]; then
    echo "同步 MCP 配置到全局..."
    cp -r "$WANG_DIR/mcp-configs/"* "$GLOBAL_DIR/mcp-configs/" 2>/dev/null || true
    echo "  ✓ MCP 配置同步完成"
fi

# 同步 Hooks
if [ -d "$WANG_DIR/hooks" ]; then
    echo "同步 Hooks 到全局..."
    cp -r "$WANG_DIR/hooks/"* "$GLOBAL_DIR/hooks/" 2>/dev/null || true
    echo "  ✓ Hooks 同步完成"
fi

echo ""
echo "=== 同步完成 ==="
