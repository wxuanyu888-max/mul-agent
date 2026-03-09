"""Subagent Handler - 子代理路由器处理器"""

import asyncio
from typing import Any, Dict, List
from .base import BaseHandler


class SubagentHandler(BaseHandler):
    """Subagent 路由处理器

    支持的操作：
    - spawn: 创建子代理任务
    - delegate: 委派任务给子代理
    - gather: 聚合子代理结果
    - list: 列出活跃的子代理会话
    - cancel: 取消子代理任务
    """

    def __init__(self, config_manager, agent_id: str = None):
        self.config_manager = config_manager
        self.agent_id = agent_id
        self._brain = None

    @property
    def brain(self):
        """懒加载 brain 实例"""
        if self._brain is None:
            from mul_agent.brain.brain import Brain
            self._brain = Brain(
                agent_id=self.agent_id or "core_brain",
                config_manager=self.config_manager
            )
        return self._brain

    def handle(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 subagent 路由请求"""
        if not params:
            return {"status": "error", "error_code": 1004, "message": "Missing params"}

        action = params.get("action", "list")

        if action == "spawn":
            return self._handle_spawn(params)
        elif action == "delegate":
            return self._handle_delegate(params)
        elif action == "gather":
            return self._handle_gather(params)
        elif action == "list":
            return self._handle_list(params)
        elif action == "cancel":
            return self._handle_cancel(params)
        elif action == "stats":
            return self._handle_stats(params)
        else:
            return {
                "status": "error",
                "error_code": 3001,
                "message": f"Unknown action: {action}",
                "details": {
                    "available_actions": ["spawn", "delegate", "gather", "list", "cancel", "stats"]
                }
            }

    def _handle_spawn(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 spawn 操作 - 创建单个子代理任务"""
        agent_id = params.get("agent_id")
        task_description = params.get("description", "")
        task_input = params.get("input", "")
        timeout = params.get("timeout", 300)

        if not agent_id:
            return {
                "status": "error",
                "error_code": 3002,
                "message": "agent_id is required for spawn action"
            }

        try:
            # 创建任务
            task = self.brain.subagent.spawn(
                agent_id=agent_id,
                task_description=task_description,
                params={"input": task_input},
                timeout=timeout
            )

            return {
                "status": "success",
                "task_id": task.task_id,
                "session_id": task.task_id.split("_")[1] if "_" in task.task_id else None,
                "agent_id": agent_id,
                "description": task_description,
                "status": task.status.value,
                "timeout": timeout
            }
        except Exception as e:
            return {
                "status": "error",
                "error_code": 3003,
                "message": f"Failed to spawn subagent: {str(e)}"
            }

    def _handle_delegate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 delegate 操作 - 委派多个任务并等待结果"""
        delegations = params.get("delegations", [])
        session_id = params.get("session_id")

        if not delegations:
            return {
                "status": "error",
                "error_code": 3002,
                "message": "delegations list is required for delegate action"
            }

        try:
            # 异步执行委派
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            result = loop.run_until_complete(
                self.brain.subagent.delegate_and_wait(
                    delegations=delegations,
                    session_id=session_id
                )
            )

            loop.close()

            return {
                "status": "success",
                "action": "delegate",
                "data": result
            }
        except Exception as e:
            return {
                "status": "error",
                "error_code": 3003,
                "message": f"Failed to delegate tasks: {str(e)}"
            }

    def _handle_gather(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 gather 操作 - 获取子代理结果"""
        session_id = params.get("session_id")
        task_id = params.get("task_id")

        if task_id:
            # 获取单个任务结果
            task = self.brain.subagent.get_task(task_id)
            if not task:
                return {
                    "status": "error",
                    "error_code": 3004,
                    "message": f"Task not found: {task_id}"
                }

            return {
                "status": "success",
                "action": "gather",
                "data": {
                    "task_id": task.task_id,
                    "agent_id": task.agent_id,
                    "description": task.description,
                    "status": task.status.value,
                    "result": task.result,
                    "error": task.error,
                    "execution_time": (task.completed_at - task.started_at) if task.completed_at and task.started_at else None
                }
            }

        elif session_id:
            # 获取会话结果
            session = self.brain.subagent.get_session(session_id)
            if not session:
                return {
                    "status": "error",
                    "error_code": 3004,
                    "message": f"Session not found: {session_id}"
                }

            results = [
                {
                    "task_id": t.task_id,
                    "agent_id": t.agent_id,
                    "description": t.description,
                    "status": t.status.value,
                    "result": t.result,
                    "error": t.error
                }
                for t in session.tasks
            ]

            return {
                "status": "success",
                "action": "gather",
                "data": {
                    "session_id": session.session_id,
                    "status": session.status.value,
                    "task_count": len(session.tasks),
                    "results": results
                }
            }

        else:
            return {
                "status": "error",
                "error_code": 3002,
                "message": "session_id or task_id is required for gather action"
            }

    def _handle_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 list 操作 - 列出活跃的子代理会话"""
        active_sessions = self.brain.subagent.list_active_sessions()

        return {
            "status": "success",
            "active_sessions": active_sessions,
            "total_count": len(active_sessions)
        }

    def _handle_cancel(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 cancel 操作 - 取消子代理任务"""
        task_id = params.get("task_id")
        session_id = params.get("session_id")

        if not task_id and not session_id:
            return {
                "status": "error",
                "error_code": 3002,
                "message": "task_id or session_id is required for cancel action"
            }

        try:
            if task_id:
                # 取消单个任务（标记为失败）
                task = self.brain.subagent.get_task(task_id)
                if task:
                    task.status = SubagentStatus.FAILED
                    task.error = "Cancelled by user"
                    return {
                        "status": "success",
                        "action": "cancel",
                        "data": {"task_id": task_id, "status": "cancelled"}
                    }
                return {
                    "status": "error",
                    "error_code": 3004,
                    "message": f"Task not found: {task_id}"
                }

            if session_id:
                # 取消整个会话
                session = self.brain.subagent.get_session(session_id)
                if session:
                    for task in session.tasks:
                        if task.status not in (SubagentStatus.COMPLETED, SubagentStatus.FAILED):
                            task.status = SubagentStatus.FAILED
                            task.error = "Session cancelled by user"
                    return {
                        "status": "success",
                        "action": "cancel",
                        "data": {"session_id": session_id, "status": "cancelled"}
                    }
                return {
                    "status": "error",
                    "error_code": 3004,
                    "message": f"Session not found: {session_id}"
                }

        except Exception as e:
            return {
                "status": "error",
                "error_code": 3003,
                "message": f"Failed to cancel: {str(e)}"
            }

    def _handle_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理 stats 操作 - 获取统计信息"""
        stats = self.brain.subagent.get_stats()

        return {
            "status": "success",
            "action": "stats",
            "data": stats
        }


# 导入状态枚举用于 cancel 操作
from mul_agent.brain.subagent import SubagentStatus
