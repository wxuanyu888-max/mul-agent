# 提示词配置优化报告

> **版本**: v2.0
> **日期**: 2026-03-07
> **变更**: 提示词从代码内移到 `wang/agent-team/.templates/prompt.md.template`

---

## 一、文件结构

```
wang/agent-team/.templates/
├── prompt.md.template      # 标准提示词模板（你可修改）
├── soul.md.template
├── user.md.template
├── skill.md.template
├── logic.md.template
└── memory.md.template

mul_agent/brain/
├── llm.py                  # 从模板读取提示词
└── config_manager.py       # 支持从模板加载
```

---

## 二、提示词模板内容

`wang/agent-team/.templates/prompt.md.template` 包含以下提示词模块：

| 模块名 | 用途 |
|--------|------|
| `default_assistant` | 默认助手提示词（主要使用） |
| `empty_input_style` | 空输入响应 |
| `help_menu_style` | 帮助菜单 |
| `context_prompt` | 上下文提示词 |

---

## 三、如何修改提示词

### 直接编辑 `wang/agent-team/.templates/prompt.md.template`

例如，修改 `default_assistant` 部分：

```markdown
## default_assistant

你是一个名为 {role_title} 的 AI 助手。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【重要】你是运行在用户本地电脑上的 AI 助手，不是云端服务！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 核心特质
- 人格：{personality}
- 职责：{responsibilities}
- 技能：{skills}

...（中间内容可以随意修改）...

## 输出格式要求

你必须严格遵循以下格式，只返回 JSON：

```json
{
  "route": "路由名称",
  "params": {
    "参数名": "参数值"
  },
  "confidence": 0.0-1.0,
  "reason": "选择此路由的简短原因"
}
```
```

---

## 四、代码读取逻辑

### `config_manager.py`

```python
def load_prompt(self, agent_id: str, prompt_name: str) -> Optional[str]:
    """加载指定提示词

    加载优先级：
    1. 先从 wang/agent-team/prompt.md 加载（用户自定义）
    2. 再从 wang/agent-team/.templates/prompt.md.template 加载（标准模板）
    """
```

### `llm.py`

```python
def _load_prompt_template(self) -> str:
    """从配置文件读取提示词模板"""
    prompt_text = self.config_manager.load_prompt(self.agent_id, "default_assistant")
    if prompt_text:
        return prompt_text
    # 返回硬编码备份
    return self._get_default_prompt_template()
```

---

## 五、提示词变量说明

在 `default_assistant` 模板中，以下变量会被动态替换：

| 变量 | 来源 | 说明 |
|------|------|------|
| `{role_title}` | `user.md` 中的 `role.title` | 角色标题 |
| `{personality}` | `soul.md` 中的 `core_traits.personality` | 人格特质 |
| `{responsibilities}` | `user.md` 中的 `role.responsibilities` | 职责列表 |
| `{skills}` | `skill.md` 中的技能列表 | 可用技能 |
| `{routes_desc}` | 代码动态生成 | 可用路由描述 |

---

## 六、修改示例

### 想让 Agent 更友好？

修改 `default_assistant` 开头：

```markdown
## default_assistant

你是一个名为 {role_title} 的 AI 助手，一个热情友好的小伙伴！

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
【重要】你是运行在用户本地电脑上的 AI 助手，不是云端服务！
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 回复风格
- 热情友好，像朋友一样交流
- 耐心细致，不厌其烦地解释
- 幽默风趣，偶尔开个无伤大雅的小玩笑

...
```

### 想增加新的路由？

在 `可用路由` 部分添加：

```markdown
### 7. search_web - 搜索网络
- 参数：query (str), max_results (int)
- 示例：{"route": "search_web", "params": {"query": "Python 教程"}}
- 适用场景：需要搜索网络信息
```

然后在 `路由选择决策树` 中添加对应逻辑。

---

## 七、调试方法

### 查看当前使用的提示词

在 `llm.py` 中添加日志：

```python
def _load_prompt_template(self) -> str:
    prompt_text = self.config_manager.load_prompt(self.agent_id, "default_assistant")
    print(f"Loaded prompt template: {prompt_text[:200]}...")  # 打印前 200 字符
    ...
```

### 测试提示词是否生效

1. 修改 `prompt.md.template`
2. 重启 Agent
3. 发送一条消息，观察响应是否符合新的提示词

---

## 八、最佳实践

### 1. 修改前先备份

```bash
cp wang/agent-team/.templates/prompt.md.template \
   wang/agent-team/.templates/prompt.md.template.backup
```

### 2. 小步迭代

每次只修改一小部分，测试有效后再继续修改。

### 3. 保持变量格式

模板中的 `{variable}` 变量不要删除或改名字，否则代码会报错。

### 4. 记录变更日志

在文件开头添加版本信息：

```markdown
---
version: '2.0'
changelog:
  - 2026-03-07: 初始版本
  - 2026-03-08: 添加更友好的问候语
---
```

---

## 九、常见问题

### Q: 修改后不生效？
A: 检查以下几点：
1. 是否修改了正确的文件（`prompt.md.template`）
2. 是否重启了 Agent
3. 变量名是否正确（`{role_title}` 等）
4. Markdown 格式是否正确（`## default_assistant` 标题）

### Q: 可以为不同 Agent 设置不同提示词吗？
A: 可以。在 `wang/agent-team/{agent_id}/prompt.md` 中创建自定义提示词，会优先使用。

### Q: 提示词太长怎么办？
A: 可以精简，保留核心部分。通常 2000-3000 字足够。

---

## 十、总结

### 优化前
- 提示词硬编码在 `llm.py` 代码里
- 修改需要改代码，容易出错
- 无法根据不同 Agent 定制

### 优化后
- 提示词在 `wang/agent-team/.templates/prompt.md.template`
- 直接编辑文件即可修改
- 支持 Agent 级别自定义（`{agent_id}/prompt.md`）
- 加载优先级：Agent 自定义 > 标准模板 > 代码备份

这就是让 Agent 变聪明的核心配置文件！
