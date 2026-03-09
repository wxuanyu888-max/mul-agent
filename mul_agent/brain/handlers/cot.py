"""Chain of Thought Handler - 推理链处理器"""

from typing import Any, Dict

from .base import BaseHandler
from mul_agent.brain.cot_engine import cot_engine, ThoughtStatus


class ChainOfThoughtHandler(BaseHandler):
    """推理链处理器

    使用场景:
    - 多步骤复杂任务
    - 需要记录思考过程
    - 需要回溯和反思
    """

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}

        action = params.get("action", "create")

        if action == "create":
            return self._create(params)
        elif action == "execute":
            return self._execute(params)
        elif action == "backtrack":
            return self._backtrack(params)
        elif action == "reflect":
            return self._reflect(params)
        elif action == "complete":
            return self._complete(params)
        elif action == "summary":
            return self._summary(params)
        elif action == "visualize":
            return self._visualize(params)
        elif action == "export":
            return self._export(params)
        else:
            return {"status": "error", "error_code": 1005, "message": f"Unknown action: {action}"}

    def _create(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建思考链"""
        goal = params.get("goal", "")
        initial_thoughts = params.get("thoughts", [])

        if not goal:
            return {"status": "error", "error_code": 1004, "message": "Missing: goal"}

        chain_id = cot_engine.create_chain(goal, initial_thoughts)

        return {
            "status": "success",
            "chain_id": chain_id,
            "goal": goal,
            "initial_steps": len(initial_thoughts)
        }

    def _execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行步骤"""
        chain_id = params.get("chain_id")
        action = params.get("route")
        route_params = params.get("params", {})

        if not chain_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: chain_id"}
        if not action:
            return {"status": "error", "error_code": 1004, "message": "Missing: route"}

        # 使用 router 执行
        from mul_agent.brain.router import Router
        router = Router(self.config_manager, self.agent_id)
        result = router.dispatch(action, route_params)

        # 记录到思考链
        cot_engine.execute_step(chain_id, action, route_params)

        return result

    def _backtrack(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """回溯"""
        chain_id = params.get("chain_id")
        steps = params.get("steps", 1)

        if not chain_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: chain_id"}

        node_id = cot_engine.backtrack(chain_id, steps)

        return {
            "status": "success",
            "chain_id": chain_id,
            "backtracked_to": node_id,
            "steps": steps
        }

    def _reflect(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """添加反思"""
        chain_id = params.get("chain_id")
        reflection = params.get("reflection", "")

        if not chain_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: chain_id"}

        node_id = cot_engine.add_reflection(chain_id, reflection)

        return {
            "status": "success",
            "chain_id": chain_id,
            "reflection_node": node_id
        }

    def _complete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """完成思考链"""
        chain_id = params.get("chain_id")
        status = params.get("status", "completed")

        if not chain_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: chain_id"}

        cot_engine.complete_chain(chain_id, ThoughtStatus[status.upper()])

        return {
            "status": "success",
            "chain_id": chain_id,
            "final_status": status
        }

    def _summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取摘要"""
        chain_id = params.get("chain_id")

        if not chain_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: chain_id"}

        return cot_engine.get_summary(chain_id)

    def _visualize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """ASCII 可视化"""
        chain_id = params.get("chain_id")

        if not chain_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: chain_id"}

        ascii_art = cot_engine.visualize_ascii(chain_id)

        return {
            "status": "success",
            "chain_id": chain_id,
            "visualization": ascii_art
        }

    def _export(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """导出轨迹"""
        chain_id = params.get("chain_id")
        output_path = params.get("output")

        if not chain_id:
            return {"status": "error", "error_code": 1004, "message": "Missing: chain_id"}

        trace = cot_engine.export_trace(chain_id)

        if output_path:
            from pathlib import Path
            Path(output_path).write_text(trace, encoding='utf-8')
            return {
                "status": "success",
                "chain_id": chain_id,
                "exported_to": output_path
            }

        return {
            "status": "success",
            "chain_id": chain_id,
            "trace": trace
        }
