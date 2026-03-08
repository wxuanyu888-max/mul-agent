# 安全规则

> 本项目安全最佳实践和约束

---

## 一、核心原则

### 1.1 安全优先级

1. **用户安全 > 任务完成**
2. **用户明确指令 > 自主决策**
3. **透明执行 > 黑箱操作**

---

## 二、禁止执行的命令

### 2.1 绝对禁止

```bash
# 系统破坏性命令
rm -rf /
rm -rf /*
mkfs /dev/sd*
dd if=/dev/zero of=/dev/sd*

# 提权命令
sudo rm -rf /
sudo chmod 777 /etc

# 敏感文件操作
cat /etc/shadow
cat /etc/passwd
```

### 2.2 命令过滤规则

```python
FORBIDDEN_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"mkfs",
    r"dd\s+if=",
    r"chmod\s+777",
    r"sudo\s+.*",
]

def is_safe_command(cmd: str) -> bool:
    """检查命令是否安全"""
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, cmd):
            return False
    return True
```

---

## 三、敏感操作确认

### 3.1 需要确认的操作

| 操作类型 | 确认要求 |
|---------|---------|
| 删除文件 | 确认文件路径和范围 |
| 修改配置 | 确认备份方案 |
| 网络请求 | 确认目标地址 |
| 写入数据 | 确认目标位置 |
| 执行脚本 | 确认脚本来源 |

### 3.2 确认格式

```markdown
⚠️ **安全提醒**

**操作**: 删除目录 `./temp/*`
**风险**: 可能删除重要文件
**影响范围**: 当前目录下所有 temp 文件夹

请回复 **"确认"** 继续执行。
```

---

## 四、密钥管理

### 4.1 存储规范

```python
# ✅ 好：使用环境变量
import os
api_key = os.environ.get("ANTHROPIC_API_KEY")
database_url = os.environ.get("DATABASE_URL")

# ❌ 坏：硬编码
API_KEY = "sk-ant-xxxxx"
DATABASE_URL = "postgresql://user:pass@localhost/db"
```

### 4.2 配置文件

```json
// wang/settings.json
{
  "llm": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-20250514"
    // ❌ 不要在这里存储密钥
  }
}
```

**正确做法**：
```bash
# 使用 .env 文件
export ANTHROPIC_API_KEY="sk-ant-xxxxx"
```

### 4.3 密钥检测

```python
SECRET_PATTERNS = [
    r"sk-[a-zA-Z0-9]{20,}",  # API Key
    r"ghp_[a-zA-Z0-9]{36}",  # GitHub Token
    r"-----BEGIN.*KEY-----", # 私钥
]

def detect_secrets(content: str) -> List[str]:
    """检测内容中的密钥"""
    secrets = []
    for pattern in SECRET_PATTERNS:
        matches = re.findall(pattern, content)
        secrets.extend(matches)
    return secrets
```

---

## 五、文件访问控制

### 5.1 允许访问的路径

```python
ALLOWED_PATHS = [
    os.getcwd(),              # 当前工作目录
    "/tmp",                   # 临时目录
    "/var/tmp",               # 临时目录
]

def is_allowed_path(path: str) -> bool:
    """检查路径是否允许访问"""
    abs_path = os.path.abspath(path)
    for allowed in ALLOWED_PATHS:
        if abs_path.startswith(allowed):
            return True
    return False
```

### 5.2 禁止访问的路径

```python
FORBIDDEN_PATHS = [
    "/etc/passwd",
    "/etc/shadow",
    "/etc/ssh",
    "~/.ssh",
    "~/.gnupg",
    "/root",
]
```

---

## 六、网络安全

### 6.1 请求验证

```python
import urllib.parse

def is_safe_url(url: str) -> bool:
    """检查 URL 是否安全"""
    parsed = urllib.parse.urlparse(url)

    # 禁止内网访问
    if parsed.hostname in ["localhost", "127.0.0.1"]:
        return False

    # 禁止内网 IP
    import ipaddress
    try:
        ip = ipaddress.ip_address(parsed.hostname)
        if ip.is_private:
            return False
    except ValueError:
        pass

    return True
```

### 6.2 SSRF 防护

```python
# ❌ 坏：直接请求用户提供的 URL
requests.get(user_url)

# ✅ 好：验证后请求
if is_safe_url(user_url):
    response = requests.get(user_url, timeout=10)
else:
    return {"error": "URL 不安全"}
```

---

## 七、注入防护

### 7.1 SQL 注入

```python
# ❌ 坏：字符串拼接
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")

# ✅ 好：参数化查询
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

### 7.2 命令注入

```python
# ❌ 坏：直接拼接命令
os.system(f"echo {user_input}")

# ✅ 好：使用 subprocess 并验证
import subprocess
safe_input = shlex.quote(user_input)
subprocess.run(["echo", safe_input], check=True)
```

### 7.3 文件路径注入

```python
# ❌ 坏：直接使用用户输入
with open(f"./data/{filename}") as f:
    content = f.read()

# ✅ 好：验证路径
safe_path = os.path.join("./data", os.path.basename(filename))
if is_allowed_path(safe_path):
    with open(safe_path) as f:
        content = f.read()
```

---

## 八、Agent 行为约束

### 8.1 自主执行边界

```yaml
# Agent 配置中的安全约束
constraints:
  forbidden_actions:
    - "rm -rf /"
    - "sudo 提权"
    - "访问敏感文件"
  boundaries:
    - "safe_execution"
    - "no_destructive_actions"
    - "transparent_logging"
```

### 8.2 越权处理

当检测到 Agent 可能执行越权操作时：

```python
def handle_unauthorized_action(action: str):
    """处理越权操作"""
    logger.warning(f"检测到越权操作：{action}")

    # 1. 阻止操作
    # 2. 记录日志
    # 3. 通知用户
    return {
        "success": False,
        "error": "UNAUTHORIZED",
        "message": f"操作 {action} 未获授权"
    }
```

---

## 九、日志与审计

### 9.1 操作日志

```python
import logging

logger = logging.getLogger("agent_security")

def log_action(agent_id: str, action: str, result: str):
    """记录 Agent 操作日志"""
    logger.info({
        "timestamp": datetime.now().isoformat(),
        "agent_id": agent_id,
        "action": action,
        "result": result
    })
```

### 9.2 审计要求

- 所有敏感操作必须记录
- 日志保留至少 30 天
- 定期审计异常操作

---

## 十、安全检查清单

提交代码前检查：

- [ ] 没有硬编码的密钥
- [ ] 命令执行有过滤
- [ ] 文件访问有验证
- [ ] 网络请求有检查
- [ ] 错误信息不泄露敏感数据
- [ ] 日志不包含密钥

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-03-08 | 初始版本 |
