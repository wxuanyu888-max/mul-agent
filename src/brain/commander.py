"""Commander - 核心指挥官模块

让 core_brain 真正成为团队指挥官：
1. 分析任务类型
2. 自动选择合适的 Agent
3. 生成详细的 To-Do List
4. 委派任务并跟踪进度
5. 汇总结果返回用户
"""

import json
import re
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from mul_agent.brain.llm import LLMClient


class TaskType(Enum):
    """任务类型"""
    CODE = "code"              # 代码实现/修改
    ARCHITECTURE = "architecture"  # 架构设计
    BUGFIX = "bugfix"          # Bug 修复
    EXPLORATION = "exploration"    # 项目探索
    DOCUMENTATION = "documentation" # 文档编写
    SIMPLE = "simple"          # 简单问答
    COMPLEX = "complex"        # 复杂多步骤任务


class AgentRole(Enum):
    """Agent 角色"""
    ALICE = "alice"    # 代码工程师
    BOB = "bob"        # 技术规划师
    WANGYUE = "wangyue"  # 日常助手


@dataclass
class DelegatedTask:
    """委办的任务"""
    agent_id: str
    description: str
    todo_list: List[str]
    priority: str = "medium"  # high/medium/low
    expected_output: str = ""
    deadline: str = ""  # 描述性，如"本次会话内"


@dataclass
class TaskResult:
    """任务结果"""
    agent_id: str
    status: str  # success/failed/pending
    output: str
    todo_completed: List[str] = field(default_factory=list)
    todo_remaining: List[str] = field(default_factory=list)
    error: Optional[str] = None


class Commander:
    """核心指挥官

    使用场景:
    1. 用户提出复杂任务
    2. Commander 分析并分解
    3. 委派给合适的 Agent
    4. 跟踪进度并聚合结果
    """

    # 任务类型到 Agent 的映射
    TASK_AGENT_MAP = {
        TaskType.CODE: AgentRole.ALICE,
        TaskType.ARCHITECTURE: AgentRole.BOB,
        TaskType.BUGFIX: AgentRole.ALICE,
        TaskType.EXPLORATION: AgentRole.WANGYUE,
        TaskType.DOCUMENTATION: AgentRole.WANGYUE,
        TaskType.SIMPLE: AgentRole.WANGYUE,
        TaskType.COMPLEX: None,  # 需要分解
    }

    # 需要委派给团队的任务关键词
    DELEGATION_KEYWORDS = [
        # 代码实现类
        '实现', '开发', '创建', '构建', '写代码', 'implement', 'develop', 'create', 'build',
        # 架构设计类
        '设计', '架构', '规划', '方案', 'architecture', 'design', 'plan',
        # Bug 修复类
        '修复', '调试', 'bug', 'fix', 'debug', 'error',
        # 复杂任务类
        '完善', '改进', '优化', '重构', 'improve', 'enhance', 'optimize', 'refactor',
    ]

    def __init__(self, brain, llm_client: LLMClient):
        self.brain = brain
        self.llm = llm_client
        self.pending_tasks: Dict[str, DelegatedTask] = {}
        self.completed_tasks: Dict[str, TaskResult] = {}

    def analyze_and_delegate(self, user_input: str) -> Dict[str, Any]:
        """分析用户输入并委派任务

        流程:
        1. 分析任务类型和复杂度
        2. 决定是否需要委派
        3. 如果需要，委派给合适的 Agent
        4. 返回结果或等待

        Args:
            user_input: 用户输入

        Returns:
            执行结果或委派状态
        """
        # 1. 分析任务
        analysis = self._analyze_task(user_input)

        if analysis.get("error"):
            return {"status": "error", "message": analysis["error"]}

        task_type = analysis.get("type")
        complexity = analysis.get("complexity")

        # 2. 简单任务直接处理
        if task_type == TaskType.SIMPLE:
            return self._handle_simple_task(user_input)

        # 3. 复杂任务需要分解和委派
        if complexity in ("medium", "complex") or task_type == TaskType.COMPLEX:
            return self._handle_complex_task(user_input, analysis)

        # 4. 中等任务委派给对应 Agent
        return self._delegate_single_task(user_input, analysis)

    def _is_team_delegation_task(self, user_input: str) -> bool:
        """判断是否需要委派给团队

        判断逻辑：
        1. 包含复杂任务关键词 → 是
        2. 明确提到 Agent 名字（alice/bob）→ 是
        3. 简单问候/问答 → 否
        4. 其他情况用 LLM 判断

        Args:
            user_input: 用户输入

        Returns:
            是否需要委派给团队
        """
        input_lower = user_input.lower()

        # 1. 简单问候/问答 → 不需要委派
        simple_patterns = [
            r'^你好 |^hello|^hi\s',
            r'^谢谢 |^thank',
            r'^再见 |^bye|^goodbye',
            r'^你叫什么 |^who are you',
            r'^你能做什么 |^what can',
        ]
        import re
        for pattern in simple_patterns:
            if re.search(pattern, input_lower, re.IGNORECASE):
                return False

        # 2. 明确提到 Agent 名字 → 需要委派
        agent_mentions = ['alice', 'bob', 'wangyue', '爱丽丝', '鲍勃', '望月']
        if any(agent in input_lower for agent in agent_mentions):
            return True

        # 3. 包含复杂任务关键词 → 需要委派
        if any(kw in input_lower for kw in self.DELEGATION_KEYWORDS):
            return True

        # 4. 使用 LLM 辅助判断（当无法确定时）
        if self.llm.is_available():
            prompt = f"""判断用户输入是否需要委派给团队成员执行：

用户输入：{user_input[:300]}

简单任务：问候、简单问答、闲聊
复杂任务：需要写代码、设计架构、修 bug、项目探索、文档编写

返回 true/false"""
            try:
                result = self.llm.chat(prompt)
                content = result.get("content", "").lower()
                if "true" in content:
                    return True
            except Exception:
                pass

        # 默认：不委派
        return False

    def _analyze_task(self, user_input: str) -> Dict[str, Any]:
        """分析任务类型和复杂度"""
        prompt = f"""分析用户任务的类型和复杂度：

用户输入：{user_input[:500]}

请分析：
1. 任务类型（code/architecture/bugfix/exploration/documentation/simple/complex）
2. 复杂度（simple/medium/complex）
3. 需要什么专业技能的 Agent
4. 是否需要分解成多个子任务

以 JSON 格式返回：
```json
{{
    "type": "code",
    "complexity": "medium",
    "required_agent": "alice",
    "needs_decomposition": false,
    "reason": "分析原因"
}}
```
"""
        try:
            result = self.llm.chat(prompt)
            content = result.get("content", "")

            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                analysis = json.loads(json_match.group())
                analysis["type"] = TaskType(analysis.get("type", "simple"))
                return analysis

            return {"type": TaskType.SIMPLE, "complexity": "simple", "error": "无法解析分析结果"}
        except Exception as e:
            return {"type": TaskType.SIMPLE, "complexity": "simple", "error": str(e)}

    def _handle_simple_task(self, user_input: str) -> Dict[str, Any]:
        """处理简单任务 — 直接回复"""
        return {
            "status": "success",
            "route": "response",
            "data": {"message": "简单任务，直接处理"},
            "delegation": None
        }

    def _handle_complex_task(self, user_input: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """处理复杂任务 — 分解并委派

        这是核心大脑的真正价值：
        1. 将大任务分解成子任务
        2. 为每个子任务选择合适的 Agent
        3. 生成详细的 To-Do List
        4. 并行或串行委派
        5. 聚合结果
        """
        # 1. 分解任务
        decomposition = self._decompose_task(user_input, analysis)

        if decomposition.get("error"):
            return {"status": "error", "message": decomposition["error"]}

        subtasks = decomposition.get("subtasks", [])

        # 2. 为每个子任务创建委派
        delegations = []
        for i, subtask in enumerate(subtasks):
            delegated_task = DelegatedTask(
                agent_id=subtask.get("agent_id", "wangyue"),
                description=subtask.get("description"),
                todo_list=subtask.get("todo_list", []),
                priority=subtask.get("priority", "medium"),
                expected_output=subtask.get("expected_output"),
            )

            # 生成委派消息
            delegation_msg = self._format_delegation_message(delegated_task)
            delegations.append({
                "agent_id": delegated_task.agent_id,
                "message": delegation_msg,
                "task_id": f"task_{i+1}"
            })

            # 保存待办任务
            self.pending_tasks[f"task_{i+1}"] = delegated_task

        # 3. 使用 subagent 路由执行委派
        return self._execute_delegations(user_input, delegations, decomposition)

    def _decompose_task(self, user_input: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """将复杂任务分解成子任务"""
        prompt = f"""将复杂任务分解成可执行的子任务：

**用户任务**: {user_input[:500]}

**任务分析**:
- 类型：{analysis.get("type").value}
- 复杂度：{analysis.get("complexity")}
- 需要 Agent: {analysis.get("required_agent")}

**可用 Agent**:
- alice: 代码工程师（实现功能、修 bug、代码审查）
- bob: 技术规划师（架构设计、技术选型、任务规划）
- wangyue: 日常助手（文档、探索、简单任务）

请分解任务：
1. 每个子任务必须是可执行的原子操作
2. 为每个子任务指定合适的 Agent
3. 标记依赖关系（哪些任务可以并行）
4. 为每个子任务生成 To-Do List

以 JSON 数组格式返回：
[
    {{
        "step": 1,
        "description": "子任务描述",
        "agent_id": "alice/bob/wangyue",
        "todo_list": ["步骤 1", "步骤 2", "步骤 3"],
        "expected_output": "预期输出",
        "priority": "high/medium/low",
        "depends_on": [],
        "can_parallel": true
    }},
    ...
]
"""
        try:
            result = self.llm.chat(prompt)
            content = result.get("content", "")

            json_match = re.search(r'\[[\s\S]*\]', content)
            if json_match:
                subtasks = json.loads(json_match.group())
                return {"subtasks": subtasks, "total": len(subtasks)}

            return {"error": "无法解析分解结果"}
        except Exception as e:
            return {"error": str(e)}

    def _format_delegation_message(self, task: DelegatedTask) -> str:
        """格式化委派消息"""
        todo_items = "\n".join(f"  {i+1}. {item}" for i, item in enumerate(task.todo_list))

        message = f"""【任务委派】

**任务描述**: {task.description}

**待办清单**:
{todo_items}

**预期输出**: {task.expected_output or "完成任务描述的内容"}

**优先级**: {task.priority}

请按照待办清单逐项执行，完成后报告结果。
"""
        return message

    def _execute_delegations(
        self,
        user_input: str,
        delegations: List[Dict[str, Any]],
        decomposition: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行委派任务

        使用 subagent 路由来实际执行委派
        """
        # 构建 subagent.delegate 参数
        delegate_params = {
            "action": "delegate",
            "delegations": delegations,
            "session_id": f"delegation_{int(time.time())}"
        }

        # 通过 router 执行
        result = self.brain.router.dispatch("subagent", delegate_params)

        if result.get("status") == "success":
            return {
                "status": "delegated",
                "route": "subagent",
                "data": {
                    "original_task": user_input[:300],
                    "subtasks_count": len(delegations),
                    "decomposition": decomposition
                },
                "result": result,
                "message": f"已委派 {len(delegations)} 个子任务给团队成员执行"
            }

        return {
            "status": "error",
            "route": "subagent",
            "message": "委派失败",
            "error": result.get("message", "未知错误")
        }

    def _delegate_single_task(
        self,
        user_input: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """委派单个任务给指定 Agent"""
        agent_id = analysis.get("required_agent", "wangyue")

        # 生成 To-Do List
        todo_list = self._generate_todo_list(user_input, analysis)

        task = DelegatedTask(
            agent_id=agent_id,
            description=user_input[:200],
            todo_list=todo_list,
        )

        message = self._format_delegation_message(task)

        # 通过 chat 路由发送
        result = self.brain.router.dispatch("chat", {
            "action": "send",
            "agent_id": agent_id,
            "message": message
        })

        if result.get("status") == "success":
            return {
                "status": "delegated",
                "route": "chat",
                "data": {"agent_id": agent_id, "task": user_input[:200]},
                "result": result,
                "message": f"已委派任务给 {agent_id}"
            }

        return result

    def _generate_todo_list(
        self,
        user_input: str,
        analysis: Dict[str, Any]
    ) -> List[str]:
        """生成待办清单"""
        task_type = analysis.get("type")

        # 根据任务类型生成不同的 To-Do List 模板
        templates = {
            TaskType.CODE: [
                "分析需求，确定输入输出",
                "设计函数/类接口",
                "实现核心逻辑",
                "编写单元测试",
                "运行测试验证"
            ],
            TaskType.ARCHITECTURE: [
                "分析业务需求和技术约束",
                "设计系统架构和组件划分",
                "定义接口和数据流",
                "评估技术选型",
                "输出架构文档"
            ],
            TaskType.BUGFIX: [
                "复现 Bug，确认现象",
                "定位问题根因",
                "设计修复方案",
                "实施修复",
                "验证修复效果"
            ],
            TaskType.EXPLORATION: [
                "了解项目结构",
                "分析关键文件",
                "总结技术栈和依赖",
                "识别潜在问题",
                "输出分析报告"
            ],
        }

        return templates.get(task_type, ["分析任务", "执行任务", "验证结果"])

    def get_delegation_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取委派任务的状态"""
        # 检查待办任务
        if task_id in self.pending_tasks:
            task = self.pending_tasks[task_id]
            return {
                "task_id": task_id,
                "status": "pending",
                "agent_id": task.agent_id,
                "description": task.description,
                "todo_total": len(task.todo_list),
                "todo_completed": len(task.todo_completed) if hasattr(task, 'todo_completed') else 0
            }

        # 检查已完成任务
        if task_id in self.completed_tasks:
            result = self.completed_tasks[task_id]
            return {
                "task_id": task_id,
                "status": result.status,
                "agent_id": result.agent_id,
                "output": result.output[:200] if result.output else "",
                "error": result.error
            }

        return None

    def aggregate_results(self, results: List[TaskResult]) -> str:
        """聚合多个任务结果，生成最终报告"""
        if not results:
            return "没有任务结果"

        # 让 LLM 生成最终报告
        prompt = f"""聚合多个子任务的结果，生成最终报告：

**原始任务**: （用户的大任务）

**子任务结果**:
"""
        for i, r in enumerate(results, 1):
            prompt += f"""
---
任务 {i}: {r.agent_id}
状态：{r.status}
输出：{r.output[:300] if r.output else 'N/A'}
"""
            if r.error:
                prompt += f"错误：{r.error}\n"

        prompt += """
请生成一份完整的报告：
1. 任务总体完成情况
2. 各子任务的成果
3. 最终交付内容
4. 后续建议（如果有）

用 Markdown 格式，简洁明了。
"""
        try:
            result = self.llm.chat(prompt)
            return result.get("content", "任务完成，但生成报告失败")
        except Exception as e:
            return f"任务完成，但生成报告失败：{e}"


# 全局单例
_commander: Optional[Commander] = None


def get_commander(brain, llm_client: LLMClient) -> Commander:
    """获取 Commander 单例"""
    global _commander
    if _commander is None:
        _commander = Commander(brain, llm_client)
    return _commander
