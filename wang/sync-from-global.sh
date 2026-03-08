#!/bin/bash
# 同步全局配置到项目 wang 文件夹
# 用法：./sync-from-global.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WANG_DIR="$SCRIPT_DIR"
GLOBAL_DIR="$HOME/.claude"

echo "=== 同步全局配置到项目 wang 文件夹 ==="
echo "源目录：$GLOBAL_DIR"
echo "目标目录：$WANG_DIR"
echo ""

# 创建目录结构
echo "创建目录结构..."
mkdir -p "$WANG_DIR"/{commands,skills,rules,mcp-configs,hooks,workspace,todos,history,projects,file-history,tasks,cache,paste-cache,session-env,debug,backups,agents}

# 同步技能库
if [ -d "$GLOBAL_DIR/skills" ]; then
    echo "同步技能库..."
    cp -r "$GLOBAL_DIR/skills/"* "$WANG_DIR/skills/" 2>/dev/null || true
    echo "  ✓ 技能库同步完成"
fi

# 同步规则库
if [ -d "$GLOBAL_DIR/rules" ]; then
    echo "同步规则库..."
    cp -r "$GLOBAL_DIR/rules/"* "$WANG_DIR/rules/" 2>/dev/null || true
    echo "  ✓ 规则库同步完成"
fi

# 同步命令
if [ -d "$GLOBAL_DIR/commands" ]; then
    echo "同步命令..."
    cp -r "$GLOBAL_DIR/commands/"* "$WANG_DIR/commands/" 2>/dev/null || true
    echo "  ✓ 命令同步完成"
fi

# 同步 MCP 配置
if [ -d "$GLOBAL_DIR/mcp-configs" ]; then
    echo "同步 MCP 配置..."
    cp -r "$GLOBAL_DIR/mcp-configs/"* "$WANG_DIR/mcp-configs/" 2>/dev/null || true
    echo "  ✓ MCP 配置同步完成"
fi

# 同步 Hooks
if [ -d "$GLOBAL_DIR/hooks" ]; then
    echo "同步 Hooks..."
    cp -r "$GLOBAL_DIR/hooks/"* "$WANG_DIR/hooks/" 2>/dev/null || true
    echo "  ✓ Hooks 同步完成"
fi

echo ""
echo "=== 同步完成 ==="
echo ""
echo "目录结构:"
ls -la "$WANG_DIR" | head -20
