# Agent 系统优化方案

> 针对"自我成长的 agent"和"能带队的 agent-team"的渐进式披露与工具优化

---

## 文件清单

| 文件 | 说明 |
|------|------|
| [OPTIMIZATION_PLAN.md](./OPTIMIZATION_PLAN.md) | 完整优化方案汇总 |
| [mcp_tools_optimization.md](./mcp_tools_optimization.md) | MCP 工具优化详细方案 |
| [.templates/skill.md.template](../../wang/agent-team/.templates/skill.md.template) | 技能树配置模板 |
| [.templates/logic.md.template](../../wang/agent-team/.templates/logic.md.template) | 路由决策配置模板 |

---

## 核心问题

1. **渐进式披露缺失**: 新用户和专家用户看到相同的能力界面
2. **工具能力不完整**: Chrome/WebSearch 只有占位实现
3. **提示词结构分散**: soul/user/logic/memory 职责边界不清晰

---

## 快速开始

### 1. 渐进式披露架构

```
Layer 1 (Novice):     response, bash, memory
                      ↓ 创建第一个 Agent 后解锁
Layer 2 (Advanced):   + create_user, chat, create_team
                      ↓ 使用 heart/自省后解锁
Layer 3 (Expert):     + heart, network_*, token_usage
```

### 2. 配置文件职责

| 文件 | 职责 |
|------|------|
| `soul.md` | 身份认同 (使命、性格、价值观) |
| `user.md` | 能力边界 (角色、工具、LLM) |
| `logic.md` | 决策逻辑 (路由规则、意图识别) |
| `skill.md` | 技能树 (渐进式能力、解锁条件) |
| `level.md` | 用户级别 (当前级别、升级进度) |

### 3. 实施优先级

1. 完善 `FileTools` - 文件操作工具
2. 集成 `Tavily API` - WebSearch
3. 添加 `skill.md` 和 `level.md` 配置
4. 修改 `brain.py` - 实现渐进式披露

详细方案见 [OPTIMIZATION_PLAN.md](./OPTIMIZATION_PLAN.md)
