# 文件迁移状态报告

## 已完成的迁移

### 1. Agent 配置文件 (✓ 已完成)

所有 Agent 配置已迁移到 `wang/agent-team/`:

```
wang/agent-team/
├── core_brain/
│   ├── soul.md ✓
│   ├── user.md ✓
│   ├── skill.md ✓
│   ├── memory.md ✓
│   ├── prompt.md ✓
│   ├── token_usage.md ✓
│   └── token_usage.json ✓
├── agent_27d48793/
│   ├── soul.md ✓
│   ├── user.md ✓
│   ├── skill.md ✓
│   └── memory.md ✓
├── agent_33d66327/
├── agent_45cbb803/
└── agent_fe6ceb7a/
```

### 2. 已更新代码

- `mul_agent/brain/handlers.py` - CreateUserHandler 现在同时保存到 `storage/agents` 和 `wang/agent-team`
- `mul_agent/brain/config_manager.py` - 添加 `list_teams()` 方法
- `mul_agent/main.py` - `team` 命令现在显示团队信息

---

## 需要迁移/处理的文件

### 1. storage/ 目录下的文件 (需要决定)

#### A. 记忆文件 - 建议保留
```
storage/memory/
├── short_term/core_brain/    # 短期记忆 (运行时生成)
├── long_term/core_brain/     # 长期记忆 (需要迁移到 wang/memory/)
└── handover/                 # 交接文档 (需要迁移到 wang/memory/handover/)
```

#### B. Agent 配置备份 - 可删除
```
storage/agents/               # 已迁移到 wang/agent-team，可删除
storage/agent_config/         # 旧的配置目录，可删除
```

#### C. 网络队列 - 需要决定
```
storage/network/              # Agent 网络消息队列
storage/message_queue/        # 消息队列
```

#### D. 快照 - 建议保留
```
storage/snapshots/            # 配置快照 (版本回滚用)
```

---

## 建议的迁移操作

### 1. 迁移记忆文件到 wang

```bash
# 创建 wang/memory 目录
mkdir -p wang/memory/long_term
mkdir -p wang/memory/handover

# 迁移长期记忆
cp -r storage/memory/long_term/* wang/memory/long_term/

# 迁移交接文档
cp -r storage/memory/handover/* wang/memory/handover/
```

### 2. 删除旧的 Agent 配置

```bash
# 删除旧目录 (已迁移到 wang/agent-team)
rm -rf storage/agents/
rm -rf storage/agent_config/
```

### 3. 保留的文件

```
storage/memory/short_term/    # 运行时短期记忆 (每次会话生成)
storage/snapshots/            # 配置快照 (版本控制)
storage/network/              # Agent 网络状态 (运行时)
storage/message_queue/        # 消息队列 (运行时)
```

---

## 迁移后目录结构

```
project/
├── wang/                      # 主要配置和数据目录
│   ├── agent-team/           # Agent 团队配置
│   │   ├── core_brain/
│   │   ├── agent_xxx/
│   │   └── .templates/
│   └── memory/               # 持久化记忆
│       ├── long_term/
│       └── handover/
├── storage/                  # 运行时数据 (可缓存清理)
│   ├── memory/short_term/    # 短期记忆 (运行时)
│   ├── snapshots/            # 配置快照
│   └── network/              # Agent 网络状态
└── tests/                    # 测试
└── docs/                     # 文档
```

---

## 代码修改摘要

### handlers.py
- 添加 `team_name` 参数支持
- 启用自我进化 (`can_modify_self: true`)
- 启用 Agent 创建能力 (`can_create_agent: true`)
- 添加团队信息到配置

### config_manager.py
- 添加 `list_teams()` 方法
- 导入 `List` 类型

### main.py
- 更新 `team` 命令显示团队信息

---

## 自检清单

- [x] Agent 配置迁移到 wang/agent-team
- [x] 代码更新支持双保存 (storage + wang)
- [x] 添加团队列出功能
- [ ] 迁移长期记忆到 wang/memory
- [ ] 迁移交接文档到 wang/memory/handover
- [ ] 删除旧的 storage/agents
- [ ] 删除旧的 storage/agent_config
- [ ] 更新文档说明新的目录结构

---

*生成时间：2026-03-06*
