---
version: "1.0"
---

# MCP 工具优化方案

## 当前问题分析

查看 `mcp_tools.py`，当前工具层存在以下问题：

1. **ChromeMCP** - 只有占位实现，没有实际集成
2. **WebSearchMCP** - 只有占位实现，没有实际搜索能力
3. **GrepTool** - 实现完整，但缺少更多文件操作工具
4. **工具发现机制** - 缺少动态工具注册和能力广告

---

## 一、工具分类与优先级

### P0: 核心工具（必须完善）

| 工具 | 状态 | 优先级 | 说明 |
|------|------|--------|------|
| BashExecutor | ✅ 完整 | P0 | 已集成，支持所有 shell 命令 |
| GrepTool | ✅ 完整 | P0 | 已集成，支持文件内容搜索 |
| FileTools | ❌ 缺失 | P0 | 需要添加读/写/删除/移动 |

### P1: 网络工具（重点增强）

| 工具 | 状态 | 优先级 | 说明 |
|------|------|--------|------|
| WebSearch | ⚠️ 占位 | P1 | 集成真实搜索 API |
| WebFetch | ⚠️ 占位 | P1 | 集成真实页面抓取 |
| ChromeMCP | ⚠️ 占位 | P1 | 集成 chrome-devtools MCP |

### P2: 专业工具（按需扩展）

| 工具 | 状态 | 优先级 | 说明 |
|------|------|--------|------|
| ImageAnalysis | ❌ 缺失 | P2 | 图片 OCR/分析 |
| CodeExecutor | ❌ 缺失 | P2 | Python/JS 代码沙箱执行 |
| DatabaseTools | ❌ 缺失 | P2 | SQL 查询/数据库操作 |

---

## 二、FileTools 实现方案

### 2.1 工具接口设计

```python
class FileTools(MCPToolBase):
    """文件操作工具集"""

    def read(self, path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        """读取文件内容"""
        pass

    def write(self, path: str, content: str, mode: str = "w") -> Dict[str, Any]:
        """写入文件内容"""
        pass

    def delete(self, path: str) -> Dict[str, Any]:
        """删除文件"""
        pass

    def move(self, src: str, dst: str) -> Dict[str, Any]:
        """移动/重命名文件"""
        pass

    def copy(self, src: str, dst: str) -> Dict[str, Any]:
        """复制文件"""
        pass

    def list_dir(self, path: str, recursive: bool = False) -> Dict[str, Any]:
        """列出目录内容"""
        pass

    def exists(self, path: str) -> Dict[str, Any]:
        """检查文件/目录是否存在"""
        pass

    def get_info(self, path: str) -> Dict[str, Any]:
        """获取文件信息（大小、修改时间等）"""
        pass
```

### 2.2 安全校验

```python
def _is_path_safe(self, path: str) -> bool:
    """检查路径是否安全"""
    # 1. 检查是否在允许的工作目录内
    if not path.startswith(self.working_dir):
        return False

    # 2. 检查是否包含危险路径
    dangerous_paths = ["/etc/", "/root/", "/var/", "/boot/"]
    for dangerous in dangerous_paths:
        if dangerous in path:
            return False

    # 3. 检查文件扩展名（可选）
    if self.allowed_extensions:
        ext = os.path.splitext(path)[1]
        if ext not in self.allowed_extensions:
            return False

    return True
```

---

## 三、WebSearch 实现方案

### 3.1 集成真实搜索 API

```python
class WebSearchMCP(MCPToolBase):
    """Web 搜索工具"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.api_key = config.get("api_key")  # Tavily/Serper API
        self.search_engine = config.get("engine", "tavily")  # tavily/serper/google

    def search(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """执行 Web 搜索"""
        if self.search_engine == "tavily":
            return self._tavily_search(query, max_results)
        elif self.search_engine == "serper":
            return self._serper_search(query, max_results)
        else:
            return {"status": "error", "message": "Unknown search engine"}

    def _tavily_search(self, query: str, max_results: int) -> Dict[str, Any]:
        """使用 Tavily API 搜索"""
        import httpx
        try:
            response = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": max_results,
                    "search_depth": "basic"
                }
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
        import httpx
        try:
            response = httpx.get(url, timeout=10)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            return {
                "status": "success",
                "url": url,
                "title": soup.title.string if soup.title else "",
                "content": soup.get_text(strip=True)[:5000]  # 限制长度
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}
```

---

## 四、Chrome MCP 集成方案

### 4.1 通过 MCP 协议连接

```python
class ChromeMCP(MCPToolBase):
    """Chrome DevTools MCP 集成"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)
        self.mcp_server_url = config.get("server_url", "http://localhost:3000")
        self.session_id = None

    async def _send_mcp_request(self, method: str, params: Dict) -> Dict[str, Any]:
        """发送 MCP 请求"""
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.mcp_server_url}/call",
                json={
                    "method": method,
                    "params": params,
                    "session_id": self.session_id
                }
            )
            return response.json()

    def navigate(self, url: str) -> Dict[str, Any]:
        """导航到 URL"""
        return self._send_mcp_request("navigate", {"url": url})

    def click(self, selector: str) -> Dict[str, Any]:
        """点击元素"""
        return self._send_mcp_request("click", {"selector": selector})

    def fill(self, selector: str, value: str) -> Dict[str, Any]:
        """填写表单"""
        return self._send_mcp_request("fill", {"selector": selector, "value": value})

    def screenshot(self) -> Dict[str, Any]:
        """截图"""
        return self._send_mcp_request("screenshot", {})

    def execute_script(self, script: str) -> Any:
        """执行 JavaScript"""
        return self._send_mcp_request("evaluate", {"script": script})
```

---

## 五、工具发现与广告机制

### 5.1 工具注册表

```python
class ToolRegistry:
    """工具注册表"""

    _tools: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, name: str, tool_class: type, config: Dict = None):
        """注册工具"""
        cls._tools[name] = {
            "class": tool_class,
            "config": config or {},
            "instance": None,
            "enabled": config.get("enabled", True) if config else True
        }

    @classmethod
    def get_tool(cls, name: str) -> MCPToolBase:
        """获取工具实例"""
        if name not in cls._tools:
            return None
        tool_info = cls._tools[name]
        if tool_info["instance"] is None:
            tool_info["instance"] = tool_info["class"](tool_info["config"])
        return tool_info["instance"]

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        """列出所有可用工具（用于能力广告）"""
        return [
            {
                "name": name,
                "enabled": info["enabled"],
                "description": info["class"].__doc__ or "",
                "methods": cls._get_public_methods(info["class"])
            }
            for name, info in cls._tools.items()
        ]

    @classmethod
    def _get_public_methods(cls, tool_class: type) -> List[str]:
        """获取工具的公开方法列表"""
        return [
            name for name in dir(tool_class)
            if not name.startswith("_") and callable(getattr(tool_class, name))
        ]
```

### 5.2 工具能力描述

```yaml
tool_capabilities:
  bash_executor:
    description: "Execute shell commands on the local machine"
    methods:
      - execute
    parameters:
      command: "The shell command to execute"
      timeout: "Timeout in seconds (default: 30)"
      cwd: "Working directory (optional)"

  grep_tool:
    description: "Search for text patterns in files"
    methods:
      - search
      - count
    parameters:
      pattern: "Regular expression or text to search"
      path: "Directory path to search"
      file_pattern: "File pattern (e.g., '*.py')"

  file_tools:
    description: "File operations (read, write, delete, move, copy)"
    methods:
      - read
      - write
      - delete
      - move
      - copy
      - list_dir
      - exists
      - get_info

  web_search:
    description: "Search the web for information"
    methods:
      - search
      - get_page
    parameters:
      query: "Search query"
      max_results: "Maximum number of results"

  chrome_mcp:
    description: "Control Chrome browser via DevTools protocol"
    methods:
      - navigate
      - click
      - fill
      - screenshot
      - execute_script
```

---

## 六、工具调用优化

### 6.1 工具选择提示词

```python
TOOL_SELECTION_PROMPT = """You have access to the following tools:

{tools_description}

Given the user's request, choose the most appropriate tool and action.
Respond in JSON format:
{{
  "tool": "tool_name",
  "action": "action_name",
  "parameters": {{...}},
  "confidence": 0.0-1.0,
  "reason": "Why this tool was chosen"
}}

If no tool is suitable, respond with:
{{
  "tool": null,
  "reason": "Why no tool is suitable"
}}
"""
```

### 6.2 工具执行结果缓存

```python
class ToolCache:
    """工具执行结果缓存"""

    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl = ttl_seconds

    def _generate_key(self, tool_name: str, action: str, params: Dict) -> str:
        """生成缓存键"""
        import hashlib
        key_string = f"{tool_name}:{action}:{json.dumps(params, sort_keys=True)}"
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]

    def get(self, tool_name: str, action: str, params: Dict) -> Optional[Dict]:
        """从缓存获取结果"""
        key = self._generate_key(tool_name, action, params)
        if key in self.cache:
            cached = self.cache[key]
            if time.time() - cached["timestamp"] < self.ttl:
                return cached["result"]
            else:
                del self.cache[key]
        return None

    def set(self, tool_name: str, action: str, params: Dict, result: Dict):
        """设置缓存"""
        key = self._generate_key(tool_name, action, params)
        if len(self.cache) >= self.max_size:
            # 清除最旧的缓存
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["timestamp"])
            del self.cache[oldest_key]
        self.cache[key] = {
            "result": result,
            "timestamp": time.time()
        }
```

---

## 七、配置示例

### 7.1 完整工具配置

```yaml
# 在 user.md 或单独的工具配置文件中
tools:
  enabled:
    - bash_executor
    - grep_tool
    - file_tools
    - web_search

  bash_executor:
    timeout: 30
    cwd: null
    forbidden_commands:
      - "rm -rf /"
      - "sudo rm"

  grep_tool:
    max_results: 100
    default_context: 2
    allowed_extensions:
      - ".py"
      - ".js"
      - ".ts"
      - ".tsx"
      - ".md"

  file_tools:
    working_dir: "/Users/agent/PycharmProjects/mul-agent"
    allowed_extensions: null  # null = 允许所有
    max_file_size: "10MB"

  web_search:
    api_key: "${TAVILY_API_KEY}"
    engine: "tavily"
    max_results: 10

  chrome_mcp:
    enabled: false
    server_url: "http://localhost:3000"
    headless: false
```

---

## 八、实施路线图

### Phase 1: 完善核心工具 (1-2 天)

- [ ] 实现 FileTools（读/写/删除/移动/复制）
- [ ] 添加路径安全校验
- [ ] 完善工具注册表
- [ ] 添加工具能力描述

### Phase 2: 集成网络工具 (2-3 天)

- [ ] 集成 Tavily/Serper Web Search API
- [ ] 实现 WebFetch 页面抓取
- [ ] 集成 Chrome DevTools MCP
- [ ] 添加工具执行缓存

### Phase 3: 优化工具调用 (1-2 天)

- [ ] 改进工具选择提示词
- [ ] 实现工具执行结果缓存
- [ ] 添加工具调用统计
- [ ] 优化错误处理和重试机制

### Phase 4: 扩展专业工具 (按需)

- [ ] ImageAnalysis (OCR/图片分析)
- [ ] CodeExecutor (代码沙箱)
- [ ] DatabaseTools (数据库操作)
