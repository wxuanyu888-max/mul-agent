"""Subagent Manager - 子代理管理器

实现多子代理并发执行能力：
1. 动态创建子代理（基于 agent-team 配置）
2. 任务委派给子代理
3. 并发执行多个子代理
4. 结果聚合和报告
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class SubagentStatus(Enum):
    """子代理状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class SubagentTask:
    """子代理任务"""
    task_id: str
    agent_id: str
    description: str
    params: Dict[str, Any]
    status: SubagentStatus = SubagentStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    timeout: int = 300  # 5 分钟超时


@dataclass
class SubagentSession:
    """子代理会话（用于追踪一组相关任务）"""
    session_id: str
    parent_agent_id: str
    description: str = ""
    tasks: List[SubagentTask] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    status: SubagentStatus = SubagentStatus.PENDING


class SubagentManager:
    """子代理管理器

    职责：
    1. 管理子代理生命周期
    2. 并发执行子代理任务
    3. 聚合子代理结果
    4. 错误处理和重试
    """

    def __init__(self, parent_brain):
        """初始化子代理管理器

        Args:
            parent_brain: 父脑实例，用于创建和调用子代理
        """
        self.parent_brain = parent_brain
        self.sessions: Dict[str, SubagentSession] = {}
        self.tasks: Dict[str, SubagentTask] = {}
        self.max_concurrent = 5  # 最大并发子代理数
        self.default_timeout = 300  # 默认超时时间（秒）

    def create_session(self, description: str = "") -> SubagentSession:
        """创建子代理会话

        Args:
            description: 会话描述

        Returns:
            新创建的会话
        """
        session_id = f"subsession_{uuid.uuid4().hex[:8]}"
        session = SubagentSession(
            session_id=session_id,
            parent_agent_id=self.parent_brain.agent_id,
            description=description,
            tasks=[],
            status=SubagentStatus.PENDING
        )
        self.sessions[session_id] = session
        return session

    def spawn(
        self,
        agent_id: str,
        task_description: str,
        params: Dict[str, Any],
        session_id: str = None,
        timeout: int = None
    ) -> SubagentTask:
        """派发生子代理任务

        Args:
            agent_id: 子代理 ID（必须是已注册的 agent）
            task_description: 任务描述
            params: 任务参数（将传递给子代理的 think 方法）
            session_id: 可选的会话 ID，不传则创建新会话
            timeout: 超时时间（秒）

        Returns:
            创建的子代理任务
        """
        # 创建或获取会话
        if session_id is None:
            session = self.create_session(description=task_description)
            session_id = session.session_id
        else:
            session = self.sessions.get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

        # 创建任务
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = SubagentTask(
            task_id=task_id,
            agent_id=agent_id,
            description=task_description,
            params=params,
            timeout=timeout or self.default_timeout
        )

        # 注册任务
        self.tasks[task_id] = task
        session.tasks.append(task)
        session.status = SubagentStatus.RUNNING

        return task

    async def execute(self, task: SubagentTask) -> SubagentTask:
        """执行单个子代理任务

        Args:
            task: 要执行的任务

        Returns:
            执行后的任务（包含结果或错误）
        """
        task.status = SubagentStatus.RUNNING
        task.started_at = time.time()

        try:
            # 创建子代理实例
            from mul_agent.brain.brain import Brain
            subagent = Brain(
                agent_id=task.agent_id,
                config_manager=self.parent_brain.config_manager
            )

            # 设置超时
            timeout = task.timeout
            elapsed = time.time() - task.started_at
            remaining_timeout = max(1, timeout - elapsed)

            # 使用 run_in_executor 在后台线程执行同步的 think 方法
            import asyncio
            loop = asyncio.get_event_loop()

            def run_think():
                return subagent.think(task.params.get("input", task.description))

            result = await asyncio.wait_for(
                loop.run_in_executor(None, run_think),
                timeout=remaining_timeout
            )

            task.status = SubagentStatus.COMPLETED
            task.result = {
                "output": result,
                "agent_id": task.agent_id,
                "execution_time": time.time() - task.started_at
            }

        except asyncio.TimeoutError:
            task.status = SubagentStatus.TIMEOUT
            task.error = f"Task execution timed out after {task.timeout}s"
        except Exception as e:
            task.status = SubagentStatus.FAILED
            task.error = str(e)

        task.completed_at = time.time()
        return task

    async def execute_batch(
        self,
        tasks: List[SubagentTask],
        max_concurrent: int = None
    ) -> List[SubagentTask]:
        """批量执行子代理任务（并发）

        Args:
            tasks: 任务列表
            max_concurrent: 最大并发数

        Returns:
            执行后的任务列表
        """
        max_concurrent = max_concurrent or self.max_concurrent

        # 创建信号量限制并发数
        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(task):
            async with semaphore:
                return await self.execute(task)

        # 并发执行
        results = await asyncio.gather(
            *[execute_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )

        # 处理异常
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                tasks[i].status = SubagentStatus.FAILED
                tasks[i].error = str(result)
                tasks[i].completed_at = time.time()
            processed_results.append(tasks[i])

        return processed_results

    async def delegate_and_wait(
        self,
        delegations: List[Dict[str, Any]],
        session_id: str = None
    ) -> Dict[str, Any]:
        """委派多个任务并等待结果

        Args:
            delegations: 委派列表，每个元素包含：
                - agent_id: 子代理 ID
                - description: 任务描述
                - params: 任务参数
                - timeout: 超时时间（可选）
            session_id: 可选的会话 ID

        Returns:
            聚合结果
        """
        # 创建会话
        if session_id is None:
            session = self.create_session(description="Batch delegation")
        else:
            session = self.sessions.get(session_id)
            if not session:
                raise ValueError(f"Session not found: {session_id}")

        # 创建任务
        tasks = []
        for delegation in delegations:
            task = self.spawn(
                agent_id=delegation.get("agent_id"),
                task_description=delegation.get("description", ""),
                params=delegation.get("params", {}),
                session_id=session.session_id,
                timeout=delegation.get("timeout")
            )
            tasks.append(task)

        # 并发执行
        results = await self.execute_batch(tasks)

        # 更新会话状态
        all_completed = all(t.status == SubagentStatus.COMPLETED for t in results)
        any_failed = any(t.status in (SubagentStatus.FAILED, SubagentStatus.TIMEOUT) for t in results)

        if all_completed:
            session.status = SubagentStatus.COMPLETED
        elif any_failed:
            session.status = SubagentStatus.FAILED
        else:
            session.status = SubagentStatus.COMPLETED

        # 聚合结果
        return self._aggregate_results(session, results)

    def _aggregate_results(
        self,
        session: SubagentSession,
        results: List[SubagentTask]
    ) -> Dict[str, Any]:
        """聚合任务结果

        Args:
            session: 会话
            results: 任务结果列表

        Returns:
            聚合结果
        """
        successful = [t for t in results if t.status == SubagentStatus.COMPLETED]
        failed = [t for t in results if t.status in (SubagentStatus.FAILED, SubagentStatus.TIMEOUT)]

        return {
            "session_id": session.session_id,
            "parent_agent_id": session.parent_agent_id,
            "total_tasks": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "execution_time": time.time() - session.created_at,
            "results": [
                {
                    "task_id": t.task_id,
                    "agent_id": t.agent_id,
                    "description": t.description,
                    "status": t.status.value,
                    "result": t.result,
                    "error": t.error,
                    "execution_time": (t.completed_at - t.started_at) if t.completed_at and t.started_at else None
                }
                for t in results
            ],
            "summary": self._generate_summary(successful, failed)
        }

    def _generate_summary(
        self,
        successful: List[SubagentTask],
        failed: List[SubagentTask]
    ) -> str:
        """生成执行摘要

        Args:
            successful: 成功任务列表
            failed: 失败任务列表

        Returns:
            摘要文本
        """
        if not successful and not failed:
            return "No tasks executed"

        parts = []

        if successful:
            parts.append(f"Successfully completed {len(successful)} task(s)")
            for task in successful:
                if task.result:
                    parts.append(f"  - {task.agent_id}: {task.description[:50]}...")

        if failed:
            parts.append(f"Failed {len(failed)} task(s)")
            for task in failed:
                parts.append(f"  - {task.agent_id}: {task.error}")

        return "\n".join(parts)

    def get_session(self, session_id: str) -> Optional[SubagentSession]:
        """获取会话"""
        return self.sessions.get(session_id)

    def get_task(self, task_id: str) -> Optional[SubagentTask]:
        """获取任务"""
        return self.tasks.get(task_id)

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """列出活跃的会话"""
        active = []
        for session in self.sessions.values():
            if session.status in (SubagentStatus.PENDING, SubagentStatus.RUNNING):
                active.append({
                    "session_id": session.session_id,
                    "parent_agent_id": session.parent_agent_id,
                    "description": session.description,
                    "task_count": len(session.tasks),
                    "status": session.status.value,
                    "created_at": session.created_at
                })
        return active

    def cleanup_session(self, session_id: str) -> bool:
        """清理会话（释放资源）

        Args:
            session_id: 会话 ID

        Returns:
            是否成功清理
        """
        session = self.sessions.get(session_id)
        if not session:
            return False

        # 只能在会话完成后清理
        if session.status not in (SubagentStatus.COMPLETED, SubagentStatus.FAILED):
            return False

        # 删除任务
        for task in session.tasks:
            if task.task_id in self.tasks:
                del self.tasks[task.task_id]

        # 删除会话
        del self.sessions[session_id]
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_sessions = len(self.sessions)
        total_tasks = len(self.tasks)

        completed_sessions = sum(
            1 for s in self.sessions.values()
            if s.status == SubagentStatus.COMPLETED
        )
        failed_sessions = sum(
            1 for s in self.sessions.values()
            if s.status == SubagentStatus.FAILED
        )

        completed_tasks = sum(
            1 for t in self.tasks.values()
            if t.status == SubagentStatus.COMPLETED
        )
        failed_tasks = sum(
            1 for t in self.tasks.values()
            if t.status in (SubagentStatus.FAILED, SubagentStatus.TIMEOUT)
        )

        return {
            "total_sessions": total_sessions,
            "active_sessions": total_sessions - completed_sessions - failed_sessions,
            "completed_sessions": completed_sessions,
            "failed_sessions": failed_sessions,
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": completed_tasks / total_tasks if total_tasks > 0 else 0
        }
