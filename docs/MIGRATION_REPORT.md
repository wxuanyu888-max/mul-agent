# Wang 文件夹整理报告

## 整理日期
2026-03-07

## 整理目标
将 `wang/` 文件夹结构与 `~/.claude` 保持一致，便于项目级配置管理。

---

## 整理前结构

```
wang/
├── .agent.config
├── .teams/
├── agent-team/
├── skill/           # 旧结构
├── hook/            # 旧结构
├── mcp/             # 旧结构
├── rule/            # 旧结构
├── memory/          # 旧结构
├── CONFIG_EXPLANATION.md
├── QUICKSTART.md
└── README.md
```

---

## 整理后结构

```
wang/
├── settings.json          # 新增：项目设置
├── agent-team/            # 保留：项目 Agent 团队
│   ├── core_brain/        # 新增：从 storage/agents 复制
│   ├── wangyue/
│   ├── lisi/
│   ├── zhangsan/
│   ├── backenddeveloper/
│   └── .templates/
├── commands/              # 新增：从 ~/.claude/commands 同步
├── skills/                # 新增：从 ~/.claude/skills 同步 (125 个)
├── rules/                 # 新增：从 ~/.claude/rules 同步 (16 个)
├── mcp-configs/           # 新增：从 ~/.claude/mcp-configs 同步
├── hooks/                 # 新增：从 ~/.claude/hooks 同步
├── workspace/             # 新增：工作区数据
├── todos/                 # 新增：Todo 数据
├── history/               # 新增：历史记录
├── projects/              # 新增：项目数据
├── file-history/          # 新增：文件历史
├── tasks/                 # 新增：任务数据
├── cache/                 # 新增：缓存数据
├── paste-cache/           # 新增：粘贴缓存
├── session-env/           # 新增：会话环境
├── debug/                 # 新增：调试数据
├── backups/               # 新增：备份数据
├── agents/                # 新增：Agent 配置
├── sync-from-global.sh    # 新增：同步脚本
├── sync-to-global.sh      # 新增：同步脚本
└── README.md              # 更新：新的规范文档
```

---

## 与 ~/.claude 对照

| Wang 文件夹 | ~/.claude 对应 | 同步状态 |
|------------|---------------|---------|
| `skills/` | `skills/` | ✅ 已同步 (125 个) |
| `rules/` | `rules/` | ✅ 已同步 (16 个) |
| `commands/` | `commands/` | ✅ 已同步 (32 个) |
| `mcp-configs/` | `mcp-configs/` | ✅ 已同步 |
| `hooks/` | `hooks/` | ✅ 已同步 |
| `todos/` | `todos/` | ✅ 已创建 |
| `history/` | `history.jsonl` | ✅ 已创建 |
| `projects/` | `projects/` | ✅ 已创建 |
| `file-history/` | `file-history/` | ✅ 已创建 |
| `tasks/` | `tasks/` | ✅ 已创建 |
| `cache/` | `cache/` | ✅ 已创建 |
| `paste-cache/` | `paste-cache/` | ✅ 已创建 |
| `session-env/` | `session-env/` | ✅ 已创建 |
| `debug/` | `debug/` | ✅ 已创建 |
| `backups/` | `backups/` | ✅ 已创建 |
| `agents/` | `agents/` | ✅ 已创建 |
| `agent-team/` | (无) | 🟡 项目特有 |

---

## 已删除的旧目录

- `skill/` → 迁移到 `skills/`
- `rule/` → 迁移到 `rules/`
- `memory/` → 迁移到 `agent-team/*/memory.md`
- `mcp/` → 迁移到 `mcp-configs/`

---

## 新增功能

### 1. 同步脚本

```bash
# 从全局同步到项目
./sync-from-global.sh

# 从项目同步到全局
./sync-to-global.sh
```

### 2. 项目设置

`settings.json` - 项目级 Claude Code 设置

### 3. Agent 团队配置

`agent-team/core_brain/` - 核心大脑 Agent 配置
- `soul.md` - 核心特质
- `user.md` - 职责和能力
- `skill.md` - 可用技能

---

## 使用说明

### 同步配置

```bash
# 从全局同步所有配置到项目
cd wang
./sync-from-global.sh

# 将项目配置同步到全局
./sync-to-global.sh
```

### 添加新 Agent

```bash
# 创建新 Agent 目录
mkdir -p wang/agent-team/my_agent

# 从模板复制配置
cp -r wang/agent-team/.templates/* wang/agent-team/my_agent/

# 或使用现有 Agent 配置
cp -r storage/agents/core_brain/*.md wang/agent-team/my_agent/
```

---

## 配置优先级

1. **项目级配置** (`wang/`) - 最高优先级
2. **全局配置** (`~/.claude/`) - 中等优先级
3. **默认配置** - 最低优先级

---

## 后续工作

1. [ ] 将 `storage/agents/` 中的其他 Agent 迁移到 `wang/agent-team/`
2. [ ] 配置项目专用的 `settings.json`
3. [ ] 添加 Git 忽略规则，排除敏感数据
4. [ ] 创建项目专属的 commands 和 skills

---

## 备注

- 旧的 `skill/`, `rule/`, `memory/`, `mcp/` 目录已重命名为 `.backup` 后缀并删除
- 所有数据已安全迁移到新结构
- 项目现在与 `~/.claude` 结构保持一致
