"""Planner Handler - 规划器处理器"""

from typing import Any, Dict

from .base import BaseHandler
from mul_agent.brain.planner import planner as global_planner, AutonomousPlanner


class PlannerHandler(BaseHandler):
    """规划器处理器

    使用场景:
    - 复杂任务自动分解
    - 多步骤执行计划
    - 执行进度跟踪
    - 动态重规划
    """

    def __init__(self, config_manager, agent_id: str = None):
        super().__init__(config_manager, agent_id)

        # 初始化规划器（如果有 LLM）
        try:
            from mul_agent.brain.llm import LLMClient
            from mul_agent.brain.router import Router
            from mul_agent.brain.cot_engine import cot_engine

            llm = LLMClient(config_manager=config_manager, agent_id=agent_id)
            router = Router(config_manager, agent_id)

            self.planner = AutonomousPlanner(llm, router, cot_engine)
        except Exception:
            # Fallback 到全局实例
            self.planner = global_planner

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}

        action = params.get("action", "create")

        if action == "create":
            return self._create(params)
        elif action == "execute":
            return self._execute(params)
        elif action == "progress":
            return self._progress(params)
        elif action == "pause":
            return self._pause(params)
        elif action == "resume":
            return self._resume(params)
        elif action == "cancel":
            return self._cancel(params)
        elif action == "summary":
            return self._summary(params)
        else:
            return {"status": "error", "error_code": 1005, "message": f"Unknown action: {action}"}

    def _create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建计划"""
        goal = params.get("goal", "")
        request = params.get("request", goal)
        context = params.get("context", {})
        use_llm = params.get("use_llm", True)

        if not goal:
            return {"status": "error", "error_code": 1004, "message": "Missing: goal"}

        plan = self.planner.create_plan(goal, request, context, use_llm)

        return {
            "status": "success",
            "plan_id": plan.id,
            "goal": plan.goal,
            "steps": len(plan.steps),
            "plan": plan.to_dict()
        }

    def _execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行计划"""
        plan_id = params.get("plan_id")

        if not plan_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: plan_id"}

        result = self.planner.execute(plan_id)

        return result

    def _progress(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取进度"""
        plan_id = params.get("plan_id")

        if not plan_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: plan_id"}

        progress = self.planner.get_progress(plan_id)

        if progress:
            return {"status": "success", **progress}
        return {"status": "error", "message": "Plan not found"}

    def _pause(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """暂停计划"""
        plan_id = params.get("plan_id")

        if not plan_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: plan_id"}

        success = self.planner.pause_plan(plan_id)

        return {
            "status": "success" if success else "error",
            "plan_id": plan_id,
            "paused": success
        }

    def _resume(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """恢复计划"""
        plan_id = params.get("plan_id")

        if not plan_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: plan_id"}

        success = self.planner.resume_plan(plan_id)

        return {
            "status": "success" if success else "error",
            "plan_id": plan_id,
            "resumed": success
        }

    def _cancel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """取消计划"""
        plan_id = params.get("plan_id")

        if not plan_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: plan_id"}

        success = self.planner.cancel_plan(plan_id)

        return {
            "status": "success" if success else "error",
            "plan_id": plan_id,
            "cancelled": success
        }

    def _summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取计划摘要"""
        plan_id = params.get("plan_id")

        if not plan_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: plan_id"}

        summary = self.planner.get_summary(plan_id)

        if summary:
            return {"status": "success", **summary}
        return {"status": "error", "message": "Plan not found"}
