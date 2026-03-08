# 代码规范

> 本项目编码规范和最佳实践

---

## 一、Python 代码规范

### 1.1 基本规范

- 遵循 **PEP 8** 编码风格
- 使用 **4 空格** 缩进
- 行宽限制 **100 字符**
- 使用 **UTF-8** 编码

### 1.2 命名规范

```python
# 类名：大驼峰
class UserService:
    pass

# 函数/方法：小写 + 下划线
def get_user_info():
    pass

# 常量：全大写 + 下划线
MAX_RETRY_COUNT = 3

# 私有成员：单下划线前缀
def _internal_method():
    pass
```

### 1.3 类型注解

```python
# 函数必须有类型注解
def calculate_total(items: List[Dict[str, Any]]) -> float:
    total = sum(item['price'] for item in items)
    return total

# 使用 Optional 表示可为空
def find_user(user_id: Optional[str]) -> Optional[User]:
    pass
```

### 1.4 函数设计

```python
# ✅ 好：单一职责，函数短小
def process_user_data(data: Dict) -> Dict:
    """处理用户数据"""
    validated = validate_data(data)
    transformed = transform_data(validated)
    return transformed

# ❌ 坏：函数过长，职责不清
def process_data(data):
    # 100 行代码...
    pass
```

**原则**：
- 函数不超过 **50 行**
- 嵌套不超过 **4 层**
- 参数不超过 **5 个**

---

## 二、项目结构规范

### 2.1 目录组织

```
mul_agent/
├── api/                    # API 层
│   ├── routes/             # 路由定义
│   └── server.py           # 服务器入口
├── brain/                  # Agent 核心
│   ├── brain.py            # Agent 主类
│   ├── llm.py              # LLM 客户端
│   └── router.py           # 路由分发
├── handlers/               # 路由处理器
├── skills/                 # 技能系统
├── commands/               # 命令系统
└── common/                 # 公共工具
```

### 2.2 文件组织

- 每个文件不超过 **800 行**
- 相关功能放在同一模块
- 使用 `__init__.py` 导出公共接口

```python
# mul_agent/brain/__init__.py
from .brain import Brain
from .config_manager import ConfigManager

__all__ = ['Brain', 'ConfigManager']
```

---

## 三、错误处理

### 3.1 异常处理

```python
# ✅ 好：具体的异常处理
try:
    result = process_data(data)
except ValueError as e:
    logger.error(f"Invalid data: {e}")
    return create_error_response("INVALID_DATA")
except TimeoutError as e:
    logger.error(f"Timeout: {e}")
    return create_error_response("TIMEOUT")

# ❌ 坏：捕获所有异常
try:
    process_data(data)
except Exception:
    pass
```

### 3.2 错误消息

```python
# ✅ 好：清晰的错误消息
return {
    "success": False,
    "error": "FILE_NOT_FOUND",
    "message": f"文件不存在：{file_path}",
    "suggestion": "请检查文件路径是否正确"
}
```

---

## 四、测试规范

### 4.1 测试要求

- 覆盖率 **> 80%**
- 先写测试再写代码（TDD）
- 测试文件命名：`test_*.py`

### 4.2 测试结构

```python
def test_bash_handler_success():
    """测试 bash 处理器成功执行"""
    # Given
    handler = BashHandler(config_manager, "test_agent")
    params = {"command": "echo hello"}

    # When
    result = handler.execute(params)

    # Then
    assert result["success"] is True
    assert "hello" in result["output"]
```

---

## 五、文档规范

### 5.1 文档字符串

```python
class ConfigManager:
    """配置管理器

    负责加载、保存和管理 Agent 配置文件。
    支持 YAML front matter 格式的 Markdown 文件。

    Attributes:
        config_dir: 配置文件目录
        agent_id: 当前 Agent ID
    """

    def load(self, agent_id: str, config_type: str) -> Dict:
        """加载配置文件

        Args:
            agent_id: Agent 标识符
            config_type: 配置类型 (soul/user/skill/memory)

        Returns:
            配置字典

        Raises:
            FileNotFoundError: 文件不存在时抛出
        """
        pass
```

### 5.2 Markdown 文档

- 使用清晰的标题层级
- 代码块指定语言
- 表格对齐

---

## 六、安全规范

### 6.1 敏感信息

```python
# ✅ 好：使用环境变量
import os
api_key = os.environ.get("ANTHROPIC_API_KEY")

# ❌ 坏：硬编码密钥
api_key = "sk-ant-xxxxx"
```

### 6.2 命令执行

```python
# ✅ 好：验证和限制命令
FORBIDDEN_COMMANDS = ["rm -rf /", "sudo", "mkfs"]

def is_safe_command(cmd: str) -> bool:
    return not any(bad in cmd for bad in FORBIDDEN_COMMANDS)

# ❌ 坏：直接执行用户输入
os.system(user_input)
```

---

## 七、Git 工作流

### 7.1 提交规范

```
<type>: <description>

[optional body]
```

**type 类型**：
- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

**示例**：
```bash
git commit -m "feat: 添加新的 bash 处理器

- 实现 BashHandler 类
- 添加超时处理
- 支持命令白名单"
```

### 7.2 分支管理

```bash
# 主分支
main        # 生产环境

# 功能分支
feature/add-new-agent
feature/improve-memory

# 修复分支
fix/login-bug
fix/memory-leak
```

---

## 八、代码审查清单

提交代码前检查：

- [ ] 代码通过 lint 检查
- [ ] 测试覆盖率 > 80%
- [ ] 没有硬编码的密钥
- [ ] 函数有类型注解
- [ ] 有文档字符串
- [ ] 没有深度嵌套
- [ ] 错误处理完整
- [ ] 提交信息规范

---

## 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-03-08 | 初始版本 |
