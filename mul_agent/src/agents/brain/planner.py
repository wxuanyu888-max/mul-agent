"""Autonomous Planner - 自主规划器

实现复杂任务的自动分解、规划、执行和调整
"""

import uuid
import time
import json
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from mul_agent.brain.cot_engine import ChainOfThoughtEngine, ThoughtStatus


class PlanStatus(Enum):
    """计划状态"""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    """步骤状态"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class PlanStep:
    """计划步骤"""
    id: str
    step_number: int
    description: str
    route: str
    params: Dict[str, Any]
    status: StepStatus = StepStatus.PENDING
    result: Optional[Dict] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 2
    expected_outcome: str = ""
    success_criteria: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "step_number": self.step_number,
            "description": self.description,
            "route": self.route,
            "params": self.params,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "retry_count": self.retry_count,
            "expected_outcome": self.expected_outcome,
            "success_criteria": self.success_criteria,
            "duration": (self.completed_at or time.time()) - (self.started_at or self.created_at)
        }


@dataclass
class Plan:
    """执行计划"""
    id: str
    goal: str
    original_request: str
    status: PlanStatus = PlanStatus.PENDING
    steps: List[PlanStep] = field(default_factory=list)
    current_step: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    cot_chain_id: Optional[str] = None  # 关联的推理链

    def add_step(self, description: str, route: str, params: Dict,
                 expected_outcome: str = "", success_criteria: List[str] = None) -> str:
        """添加步骤"""
        step_id = str(uuid.uuid4())[:8]
        step = PlanStep(
            id=step_id,
            step_number=len(self.steps) + 1,
            description=description,
            route=route,
            params=params,
            expected_outcome=expected_outcome,
            success_criteria=success_criteria or []
        )
        self.steps.append(step)
        return step_id

    def get_current_step(self) -> Optional[PlanStep]:
        """获取当前步骤"""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    def get_progress(self) -> Dict[str, Any]:
        """获取进度"""
        total = len(self.steps)
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        failed = sum(1 for s in self.steps if s.status == StepStatus.FAILED)

        return {
            "total_steps": total,
            "completed": completed,
            "failed": failed,
            "pending": total - completed - failed,
            "percentage": (completed / total * 100) if total > 0 else 0
        }

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "goal": self.goal,
            "original_request": self.original_request,
            "status": self.status.value,
            "steps": [s.to_dict() for s in self.steps],
            "current_step": self.current_step,
            "progress": self.get_progress(),
            "context": self.context,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "cot_chain_id": self.cot_chain_id
        }


class AutonomousPlanner:
    """自主规划器

    核心能力:
    1. 使用 LLM 分解复杂任务
    2. 生成可执行的计划
    3. 逐步执行并监控
    4. 根据结果动态调整计划
    """

    def __init__(self, llm_client=None, router=None, cot_engine=None):
        """初始化规划器

        Args:
            llm_client: LLM 客户端
            router: 路由器实例
            cot_engine: 推理链引擎
        """
        self.llm = llm_client
        self.router = router
        self.cot_engine = cot_engine or ChainOfThoughtEngine()

        self.plans: Dict[str, Plan] = {}
        self.history: List[str] = []

        # 配置
        self.max_steps = 20
        self.max_retries = 2
        self.auto_replan = True

    def create_plan(self, goal: str, original_request: str,
                    context: Dict = None, use_llm: bool = True) -> Plan:
        """创建执行计划

        Args:
            goal: 目标描述
            original_request: 原始用户请求
            context: 上下文信息
            use_llm: 是否使用 LLM 分解任务

        Returns:
            Plan 对象
        """
        plan_id = str(uuid.uuid4())
        plan = Plan(
            id=plan_id,
            goal=goal,
            original_request=original_request,
            context=context or {}
        )

        if use_llm and self.llm:
            # 使用 LLM 分解任务
            self._decompose_with_llm(plan, context)
        else:
            # 使用规则分解（简单 fallback）
            self._decompose_with_rules(plan)

        self.plans[plan_id] = plan
        self.history.append(plan_id)

        # 创建关联的推理链
        initial_thoughts = [s.description for s in plan.steps[:5]]
        plan.cot_chain_id = self.cot_engine.create_chain(goal, initial_thoughts)

        return plan

    def _decompose_with_llm(self, plan: Plan, context: Dict) -> None:
        """使用 LLM 分解任务"""
        plan.status = PlanStatus.PLANNING

        # 构建提示词
        prompt = self._build_decomposition_prompt(plan, context)

        try:
            result = self.llm.chat(prompt)
            steps = self._parse_llm_response(result.get("content", ""))

            for step_data in steps[:self.max_steps]:
                plan.add_step(**step_data)

            plan.status = PlanStatus.PENDING

        except Exception as e:
            plan.status = PlanStatus.FAILED
            plan.metadata["planning_error"] = str(e)
            # Fallback 到规则分解
            self._decompose_with_rules(plan)

    def _build_decomposition_prompt(self, plan: Plan, context: Dict) -> str:
        """构建任务分解提示词"""
        available_routes = [
            {"name": "bash", "desc": "执行 shell 命令", "example": {"command": "ls -la"}},
            {"name": "file_edit", "desc": "文件编辑", "example": {"action": "read", "path": "file.py"}},
            {"name": "glob", "desc": "文件名匹配", "example": {"pattern": "*.py"}},
            {"name": "grep", "desc": "内容搜索", "example": {"pattern": "TODO"}},
            {"name": "code_understanding", "desc": "代码分析", "example": {"action": "analyze", "path": "."}},
            {"name": "chat", "desc": "Agent 对话"},
            {"name": "subagent", "desc": "子代理任务"},
        ]

        context_str = json.dumps(context, indent=2, ensure_ascii=False)[:2000]

        return f"""你是一个任务规划专家。请将以下目标分解为可执行的步骤。

## 目标
{plan.goal}

## 原始请求
{plan.original_request}

## 当前上下文
{context_str}

## 可用工具/路由
{json.dumps(available_routes, indent=2, ensure_ascii=False)}

## 输出格式
请返回一个 JSON 数组，每个元素包含:
- description: 步骤描述（中文）
- route: 使用的路由名
- params: 路由参数（JSON 对象）
- expected_outcome: 预期结果
- success_criteria: 成功标准（字符串数组）

## 要求
1. 步骤数不超过 {self.max_steps} 个
2. 每个步骤必须是独立的、可执行的
3. 步骤之间要有逻辑顺序
4. 优先使用非破坏性操作（先分析再修改）
5. 复杂操作前要有验证步骤

## 返回 JSON 数组
"""

    def _parse_llm_response(self, response: str) -> List[Dict]:
        """解析 LLM 返回的步骤"""
        import re

        # 尝试提取 JSON
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            try:
                steps = json.loads(json_match.group())
                return steps
            except json.JSONDecodeError:
                pass

        # Fallback: 返回空列表
        return []

    def _decompose_with_rules(self, plan: Plan) -> None:
        """使用规则分解任务（fallback）"""
        goal_lower = plan.goal.lower()

        # 简单规则匹配
        if any(kw in goal_lower for kw in ["分析", "analyze", "查看", "explore"]):
            plan.add_step(
                description="分析项目结构",
                route="code_understanding",
                params={"action": "analyze", "path": "."},
                expected_outcome="项目结构概览"
            )
            plan.add_step(
                description="生成依赖图",
                route="code_understanding",
                params={"action": "dependencies", "path": "."},
                expected_outcome="依赖关系信息"
            )

        elif any(kw in goal_lower for kw in ["搜索", "search", "查找", "find"]):
            if "文件" in goal_lower or "file" in goal_lower:
                plan.add_step(
                    description="搜索文件",
                    route="glob",
                    params={"pattern": "*.*", "path": "."},
                    expected_outcome="匹配的文件列表"
                )
            else:
                plan.add_step(
                    description="搜索内容",
                    route="grep",
                    params={"pattern": plan.goal, "path": "."},
                    expected_outcome="匹配的内容"
                )

        else:
            # 默认：先分析再行动
            plan.add_step(
                description="了解当前情况",
                route="bash",
                params={"command": "ls -la"},
                expected_outcome="目录列表"
            )

    def execute(self, plan_id: str, callback: Callable = None) -> Dict:
        """执行计划

        Args:
            plan_id: 计划 ID
            callback: 每步执行后的回调函数

        Returns:
            执行结果
        """
        plan = self.plans.get(plan_id)
        if not plan:
            return {"status": "error", "message": "Plan not found"}

        plan.status = PlanStatus.EXECUTING
        plan.started_at = time.time()

        results = []

        while plan.current_step < len(plan.steps):
            step = plan.get_current_step()
            if not step:
                break

            # 执行步骤
            result = self._execute_step(plan, step)
            results.append(result)

            # 调用回调
            if callback:
                callback(step, result)

            # 检查是否需要重规划
            if step.status == StepStatus.FAILED and self.auto_replan:
                if step.retry_count >= step.max_retries:
                    # 重试次数用尽，尝试重规划
                    replan_result = self._replan(plan, step, result)
                    if replan_result.get("replan_needed"):
                        continue  # 重规划后继续

            # 移动到下一步
            if step.status == StepStatus.COMPLETED:
                plan.current_step += 1

        # 完成
        plan.completed_at = time.time()
        plan.status = PlanStatus.COMPLETED if plan.current_step >= len(plan.steps) else PlanStatus.FAILED

        # 更新推理链
        if plan.cot_chain_id:
            self.cot_engine.complete_chain(
                plan.cot_chain_id,
                ThoughtStatus.COMPLETED if plan.status == PlanStatus.COMPLETED else ThoughtStatus.FAILED
            )

        return {
            "status": "success",
            "plan_id": plan_id,
            "final_status": plan.status.value,
            "progress": plan.get_progress(),
            "results": results,
            "duration": plan.completed_at - plan.started_at
        }

    def _execute_step(self, plan: Plan, step: PlanStep) -> Dict:
        """执行单个步骤"""
        step.status = StepStatus.IN_PROGRESS
        step.started_at = time.time()

        try:
            # 更新推理链
            if plan.cot_chain_id:
                self.cot_engine.add_reflection(
                    plan.cot_chain_id,
                    f"执行步骤 {step.step_number}: {step.description}"
                )

            # 执行路由
            result = self.router.dispatch(step.route, step.params)

            step.result = result
            step.completed_at = time.time()

            # 判断成功/失败
            if result.get("status") == "success":
                step.status = StepStatus.COMPLETED
            else:
                step.status = StepStatus.FAILED
                step.error = result.get("message", "Execution failed")

            # 更新推理链
            if plan.cot_chain_id:
                self.cot_engine.execute_step(
                    plan.cot_chain_id,
                    step.route,
                    step.params
                )

            return result

        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.completed_at = time.time()

            return {"status": "error", "message": str(e)}

    def _replan(self, plan: Plan, failed_step: PlanStep, error_result: Dict) -> Dict:
        """重规划"""
        failed_step.retry_count += 1

        # 如果还有重试次数，先重试
        if failed_step.retry_count < failed_step.max_retries:
            failed_step.status = StepStatus.RETRYING
            return {"replan_needed": False, "action": "retry"}

        # 尝试调整当前步骤的参数后重试
        if self._can_adjust_step(failed_step, error_result):
            adjusted_params = self._adjust_step_params(failed_step, error_result)
            if adjusted_params:
                failed_step.params = adjusted_params
                failed_step.status = StepStatus.PENDING
                return {"replan_needed": False, "action": "retry_with_adjustment"}

        # 需要重新规划后续步骤
        return self._replan_remaining_steps(plan, failed_step)

    def _can_adjust_step(self, step: PlanStep, error: Dict) -> bool:
        """判断是否可以调整步骤"""
        # 超时错误可以增加超时时间
        if "timeout" in str(error).lower():
            return True
        # 文件不存在可以改变路径
        if "not found" in str(error).lower():
            return True
        return False

    def _adjust_step_params(self, step: PlanStep, error: Dict) -> Optional[Dict]:
        """调整步骤参数"""
        if "timeout" in str(error).lower():
            # 增加超时时间
            new_params = step.params.copy()
            new_params["timeout"] = new_params.get("timeout", 30) * 2
            return new_params
        return None

    def _replan_remaining_steps(self, plan: Plan, failed_step: PlanStep) -> Dict:
        """重新规划后续步骤"""
        if not self.llm:
            return {"replan_needed": False, "action": "fail"}

        # 使用 LLM 重新规划
        prompt = self._build_replan_prompt(plan, failed_step)

        try:
            result = self.llm.chat(prompt)
            new_steps = self._parse_llm_response(result.get("content", ""))

            # 替换后续步骤
            plan.steps = plan.steps[:plan.current_step + 1]
            for step_data in new_steps:
                plan.add_step(**step_data)

            return {"replan_needed": True, "action": "continue_with_new_plan"}

        except Exception:
            return {"replan_needed": False, "action": "fail"}

    def _build_replan_prompt(self, plan: Plan, failed_step: PlanStep) -> str:
        """构建重规划提示词"""
        return f"""任务规划需要调整。

## 原目标
{plan.goal}

## 已完成的步骤
{json.dumps([s.to_dict() for s in plan.steps if s.status == StepStatus.COMPLETED], indent=2)}

## 失败的步骤
{failed_step.to_dict()}

## 错误信息
{failed_step.error}

请提供替代的执行方案，绕过当前问题继续完成目标。
返回 JSON 数组，格式同创建计划。
"""

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """获取计划"""
        return self.plans.get(plan_id)

    def get_progress(self, plan_id: str) -> Optional[Dict]:
        """获取进度"""
        plan = self.plans.get(plan_id)
        return plan.get_progress() if plan else None

    def pause_plan(self, plan_id: str) -> bool:
        """暂停计划"""
        plan = self.plans.get(plan_id)
        if plan and plan.status == PlanStatus.EXECUTING:
            plan.status = PlanStatus.PAUSED
            return True
        return False

    def resume_plan(self, plan_id: str) -> bool:
        """恢复计划"""
        plan = self.plans.get(plan_id)
        if plan and plan.status == PlanStatus.PAUSED:
            plan.status = PlanStatus.EXECUTING
            return self.execute(plan_id) is not None
        return False

    def cancel_plan(self, plan_id: str) -> bool:
        """取消计划"""
        plan = self.plans.get(plan_id)
        if plan:
            plan.status = PlanStatus.CANCELLED
            plan.completed_at = time.time()
            return True
        return False

    def get_summary(self, plan_id: str) -> Optional[Dict]:
        """获取计划摘要"""
        plan = self.plans.get(plan_id)
        if not plan:
            return None

        return {
            "id": plan.id,
            "goal": plan.goal,
            "status": plan.status.value,
            "progress": plan.get_progress(),
            "total_steps": len(plan.steps),
            "current_step": plan.current_step,
            "duration": (plan.completed_at or time.time()) - plan.created_at
        }


# 全局实例
planner = AutonomousPlanner()
