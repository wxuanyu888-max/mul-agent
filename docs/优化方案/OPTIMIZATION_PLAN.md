# Agent 系统优化方案

> 针对"自我成长的 agent"和"能带队的 agent-team"的渐进式披露与工具优化

---

## 一、核心问题诊断

### 1.1 当前架构分析

| 模块 | 状态 | 问题 |
|------|------|------|
| `brain.py` | ✅ 核心逻辑完整 | 路由决策扁平，无渐进式披露 |
| `router.py` | ✅ 路由分发正常 | 缺少用户级别权限控制 |
| `handlers.py` | ✅ 处理器齐全 | 缺少能力披露策略 |
| `mcp_tools.py` | ⚠️ 部分占位实现 | Chrome/WebSearch 未集成真实 API |
| 配置文件 | ⚠️ 基础结构有 | 缺少技能树/用户级别配置 |

### 1.2 核心问题

1. **渐进式披露缺失**: 新用户和专家用户看到的是相同的能力界面
2. **工具能力不完整**: 部分 MCP 工具只有占位实现
3. **提示词结构分散**: soul/user/logic/memory 之间的职责边界不清晰
4. **缺少用户成长路径**: 没有根据用户使用深度动态调整披露策略

---

## 二、渐进式披露方案

### 2.1 三层披露架构

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: 基础交互层 (Novice)                                │
│ - 自动触发：问候响应、bash 执行、直接问答                    │
│ - 用户感知："这个助手能听懂我的话"                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 2: 协作能力层 (Advanced)                              │
│ - 条件解锁：创建过 agent 或使用过协作功能                    │
│ - 披露能力：create_user, chat, create_team, memory          │
│ - 用户感知："这个助手能帮我管理团队"                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Layer 3: 专家能力层 (Expert)                                │
│ - 条件解锁：明确使用 heart 或 network 功能                   │
│ - 披露能力：heart, network_*, token_usage                   │
│ - 用户感知："这个助手能自我进化和协调多 agent"              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 路由决策优化

**当前逻辑** (`brain.py:326-417`):
```python
# 扁平的 if-elif 链
if bash_pattern: return {"route": "bash"}
if greeting: return {"route": "uncertain"}  # → LLM
if help_request: return {"route": "response"}
# ... 所有用户看到相同的逻辑
```

**优化后逻辑**:
```python
def _decide_action(self, user_input: str) -> Dict[str, Any]:
    # 1. 获取用户级别
    user_level = self._get_user_level()

    # 2. 基础意图识别 (所有用户相同)
    action = self._basic_intent_recognition(user_input)

    # 3. 根据级别过滤可用路由
    if action["route"] not in self._get_unlocked_routes(user_level):
        # 引导用户解锁
        return self._guide_to_unlock(action["route"], user_level)

    # 4. 返回行动
    return action
```

### 2.3 用户级别配置模板

创建 `storage/agents/{agent_id}/level.md`:

```yaml
---
version: "1.0"
agent_id: ${agent_id}
---

# User Level Configuration

## 当前级别
current_level: novice
unlocked_routes:
  - response
  - bash
  - memory

## 升级进度
progress:
  create_agent_count: 0
  total_interactions: 5
  advanced_features_used: []

## 升级条件
level_up_conditions:
  novice → advanced:
    - create_agent_count >= 1
    - OR total_interactions >= 10
  advanced → expert:
    - use_heart_explicitly: true
    - OR use_network_feature: true
```

---

## 三、提示词配置优化

### 3.1 配置文件职责划分

| 文件 | 职责 | 包含内容 | 更新频率 |
|------|------|----------|----------|
| `soul.md` | 身份认同 | 使命、性格、价值观、行为模式 | 低频 (进化时更新) |
| `user.md` | 能力边界 | 角色、职责、工具列表、LLM 配置 | 中频 (升级时更新) |
| `logic.md` | 决策逻辑 | 路由规则、意图识别、权限控制 | 低频 (系统更新) |
| `skill.md` | 技能树 | 渐进式能力、解锁条件 | 中频 (成长时更新) |
| `memory.md` | 记忆策略 | 记忆类型、更新规则、检索策略 | 低频 |

### 3.2 关键配置示例

#### soul.md (身份认同)
```markdown
# 核心身份

## 使命
协调多 Agent 合作，优化任务分配，确保系统稳定运行

## 性格
冷静、分析型、协作导向

## 行为模式
- 遇到问题先分析再行动
- 复杂任务自动拆解委派
- 定期自省改进
```

#### user.md (能力边界)
```yaml
role:
  type: coordinator
  title: Core Brain
  responsibilities: [任务分析，Agent 协调，资源分配]

capabilities:
  max_team_size: 10
  can_create_agent: true
  can_execute_tools: true

tools:
  enabled: [bash_executor, grep_tool, file_tools, web_search]
```

#### logic.md (决策逻辑)
```yaml
routing_rules:
  - pattern: "^\\$ "
    route: bash
    priority: 1

  - pattern: "create|new|创建"
    route: create_user
    unlock_level: novice

  - pattern: "heart|reflect|自省"
    route: heart
    unlock_level: expert
```

#### skill.md (技能树)
```yaml
skill_tree:
  layer_1:
    name: 基础交互
    unlocked: always
    skills: [response, bash, memory]

  layer_2:
    name: 协作能力
    unlock_condition:
      create_agent_count: 1
    skills: [create_user, chat, create_team]

  layer_3:
    name: 专家能力
    unlock_condition:
      use_heart_explicitly: true
    skills: [heart, network_delegate, network_broadcast]
```

---

## 四、外部工具优化

### 4.1 工具优先级矩阵

```
                    重要性
              低 ←────────→ 高
            ┌────────────────────┐
         高 │ FileTools  │  P1    │
            ├────────────┼────────┤
      使    │ ChromeMCP  │ Bash   │
      用    │ WebSearch  │ Grep   │
      频    ├────────────┼────────┤
         低 │ ImageOCR   │  P3    │
            │ CodeExec   │        │
            └────────────────────┘
```

### 4.2 立即可实施的优化

#### 1. 添加 FileTools (`mul_agent/tools/file_tools.py`)

```python
from mul_agent.tools.mcp_tools import MCPToolBase
from typing import Any, Dict, Optional
import os
import shutil

class FileTools(MCPToolBase):
    """文件操作工具集"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.working_dir = config.get("working_dir", os.getcwd())
        self.max_file_size = config.get("max_file_size", 10 * 1024 * 1024)  # 10MB

    def _is_path_safe(self, path: str) -> bool:
        """检查路径安全性"""
        # 确保在允许的工作目录内
        abs_path = os.path.abspath(path)
        if not abs_path.startswith(self.working_dir):
            return False

        # 禁止访问敏感路径
        forbidden = ["/etc/", "/root/", "/var/", "/boot/", ".git/"]
        return not any(f in abs_path for f in forbidden)

    def read(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """读取文件"""
        if not self._is_path_safe(path):
            return {"status": "error", "message": f"Path not allowed: {path}"}

        try:
            with open(path, "r", encoding=encoding) as f:
                content = f.read()
                if len(content) > self.max_file_size:
                    return {"status": "error", "message": "File too large"}
                return {"status": "success", "content": content, "path": path}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def write(self, path: str, content: str, mode: str = "w") -> Dict[str, Any]:
        """写入文件"""
        if not self._is_path_safe(path):
            return {"status": "error", "message": f"Path not allowed: {path}"}

        try:
            with open(path, mode, encoding="utf-8") as f:
                f.write(content)
            return {"status": "success", "path": path, "bytes_written": len(content)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete(self, path: str) -> Dict[str, Any]:
        """删除文件"""
        if not self._is_path_safe(path):
            return {"status": "error", "message": f"Path not allowed: {path}"}

        try:
            os.remove(path)
            return {"status": "success", "path": path, "action": "deleted"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_dir(self, path: str = ".") -> Dict[str, Any]:
        """列出目录内容"""
        if not self._is_path_safe(path):
            return {"status": "error", "message": f"Path not allowed: {path}"}

        try:
            items = os.listdir(path)
            result = []
            for item in items:
                full_path = os.path.join(path, item)
                result.append({
                    "name": item,
                    "type": "dir" if os.path.isdir(full_path) else "file",
                    "size": os.path.getsize(full_path) if os.path.isfile(full_path) else None
                })
            return {"status": "success", "path": path, "items": result}
        except Exception as e:
            return {"status": "error", "message": str(e)}
```

#### 2. 完善 WebSearch (`mul_agent/tools/web_search.py`)

```python
from mul_agent.tools.mcp_tools import MCPToolBase
from typing import Any, Dict, Optional
import httpx

class WebSearchMCP(MCPToolBase):
    """Web 搜索工具 - 集成 Tavily API"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = config.get("api_key") or os.getenv("TAVILY_API_KEY")
        self.max_results = config.get("max_results", 10)

    def search(self, query: str, max_results: Optional[int] = None) -> Dict[str, Any]:
        """使用 Tavily API 搜索"""
        if not self.api_key:
            return {
                "status": "error",
                "message": "TAVILY_API_KEY not configured"
            }

        try:
            response = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results or self.max_results
                },
                timeout=30
            )
            data = response.json()

            return {
                "status": "success",
                "query": query,
                "results": [
                    {
                        "title": r.get("title"),
                        "url": r.get("url"),
                        "content": r.get("content"),
                        "score": r.get("score")
                    }
                    for r in data.get("results", [])
                ]
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_page(self, url: str) -> Dict[str, Any]:
        """获取页面内容"""
        try:
            response = httpx.get(url, timeout=10)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")

            return {
                "status": "success",
                "url": url,
                "title": soup.title.string if soup.title else "",
                "content": soup.get_text(strip=True)[:5000]
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
```

### 4.3 工具注册与发现

在 `mul_agent/tools/mcp_tools.py` 中添加注册表:

```python
class MCPToolRegistry:
    """工具注册表 - 单例模式"""

    _instance = None
    _tools: Dict[str, Dict[str, Any]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, name: str, tool_class: type, config: Dict = None):
        """注册工具"""
        cls._tools[name] = {
            "class": tool_class,
            "config": config or {},
            "instance": None
        }

    @classmethod
    def get_tool(cls, name: str) -> Optional[MCPToolBase]:
        """获取工具实例"""
        if name not in cls._tools:
            return None
        tool_info = cls._tools[name]
        if tool_info["instance"] is None:
            tool_info["instance"] = tool_info["class"](tool_info["config"])
        return tool_info["instance"]

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        """列出所有可用工具及其能力"""
        return [
            {
                "name": name,
                "enabled": True,
                "description": info["class"].__doc__ or "",
                "methods": [
                    m for m in dir(info["class"])
                    if not m.startswith("_") and m != "execute"
                ]
            }
            for name, info in cls._tools.items()
        ]


# 注册默认工具
MCPToolRegistry.register("bash", BashExecutor)
MCPToolRegistry.register("grep", GrepTool)
MCPToolRegistry.register("file_tools", FileTools)
MCPToolRegistry.register("web_search", WebSearchMCP)
```

---

## 五、实施路线图

### Phase 1: 基础架构 (1-2 天)

- [ ] 创建 `skill.md.template` 和 `level.md` 配置
- [ ] 修改 `brain.py` 添加用户级别判断逻辑
- [ ] 实现 `FileTools` 类
- [ ] 添加工具注册表 `MCPToolRegistry`

### Phase 2: 渐进式披露 (2-3 天)

- [ ] 完善 `logic.md` 路由决策规则
- [ ] 实现用户级别升级逻辑
- [ ] 添加解锁引导提示
- [ ] 测试不同级别的披露效果

### Phase 3: 工具增强 (3-5 天)

- [ ] 集成 Tavily Web Search API
- [ ] 集成 Chrome DevTools MCP
- [ ] 添加工具执行缓存
- [ ] 完善工具错误处理

### Phase 4: 自我成长 (持续)

- [ ] 实现基于使用模式的自动升级
- [ ] 添加 agent 自省改进建议
- [ ] 收集用户反馈优化披露策略
- [ ] 建立工具使用统计

---

## 六、关键代码变更

### 6.1 brain.py 修改

在 `_decide_action` 方法前添加级别判断:

```python
def _get_user_level(self) -> str:
    """获取当前用户级别"""
    try:
        level_config = self.config_manager.load(self.agent_id, "level")
        return level_config.get("current_level", "novice")
    except Exception:
        return "novice"

def _get_unlocked_routes(self, user_level: str) -> List[str]:
    """获取用户级别对应的可用路由"""
    route_map = {
        "novice": ["response", "bash", "memory"],
        "advanced": ["response", "bash", "memory", "create_user", "chat", "create_team"],
        "expert": "all"  # 所有路由
    }
    routes = route_map.get(user_level, ["response", "bash", "memory"])
    if routes == "all":
        return list(self.router.handlers.keys())
    return routes

def _guide_to_unlock(self, desired_route: str, current_level: str) -> Dict[str, Any]:
    """引导用户解锁能力"""
    unlock_requirements = {
        "create_user": "创建第一个 Agent 后解锁",
        "chat": "创建 Agent 后可用",
        "heart": "使用自省功能解锁",
        "network_delegate": "专家级别可用"
    }

    return {
        "route": "response",
        "params": {
            "message": f"这个功能需要 {unlock_requirements.get(desired_route, '升级后')} 可用。"
                       f"当前级别：{current_level}"
        }
    }
```

### 6.2 handlers.py 修改

在 `CreateUserHandler` 中添加升级逻辑:

```python
def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
    # ... 现有创建逻辑 ...

    # 创建成功后，更新用户级别
    try:
        level_config = self.config_manager.load(self.agent_id, "level")
        level_config["progress"]["create_agent_count"] = \
            level_config["progress"].get("create_agent_count", 0) + 1

        # 检查是否满足升级条件
        if level_config["current_level"] == "novice" and \
           level_config["progress"]["create_agent_count"] >= 1:
            level_config["current_level"] = "advanced"
            level_config["unlocked_routes"] = [
                "response", "bash", "memory", "create_user", "chat", "create_team"
            ]

        self.config_manager.save(self.agent_id, "level", level_config)
    except Exception:
        pass  # 级别更新失败不影响 Agent 创建

    return result
```

---

## 七、预期效果

### 7.1 用户体验改善

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 新用户上手难度 | 高 (面对所有能力不知所措) | 低 (逐步引导) |
| 能力发现效率 | 依赖用户主动探索 | 系统主动引导 |
| 专家用户效率 | 无差别 | 快速访问高级功能 |

### 7.2 系统能力提升

| 能力 | 优化前 | 优化后 |
|------|--------|--------|
| 工具完整性 | 部分占位 | 完整实现 |
| Web 搜索 | ❌ | ✅ Tavily API |
| 文件操作 | ❌ | ✅ 完整 CRUD |
| Chrome 控制 | ❌ | ✅ MCP 集成 |

---

## 八、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 配置复杂化 | 中 | 提供默认配置模板 |
| 工具集成成本 | 中 | 分阶段实施 |
| 用户成长路径设计不当 | 低 | 收集反馈迭代优化 |

---

## 九、总结

本方案针对你的多 agent 系统提出了以下核心优化：

1. **渐进式披露**: 三层架构 (基础→协作→专家)，根据用户使用深度动态调整
2. **提示词结构化**: 明确 soul/user/logic/skill/memory 的职责边界
3. **工具完善**: FileTools、WebSearch、Chrome MCP 真实集成
4. **用户成长路径**: 从 novice 到 expert 的清晰升级路线

优先实施建议：
1. 先完善 `FileTools` (立即可用)
2. 添加 `skill.md` 和 `level.md` 配置
3. 修改 `brain.py` 实现渐进式披露
4. 集成 Tavily API 完善 WebSearch
