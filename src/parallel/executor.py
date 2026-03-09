"""Parallel Executor - 并行任务执行器"""

import asyncio
import concurrent.futures
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime
from mul_agent.parallel.dependency import DependencyManager, Task, TaskStatus


class ParallelExecutor:
    """并行执行器

    功能：
    - 并发执行任务
    - 依赖感知调度
    - 超时控制
    - 重试机制
    - 进度跟踪
    """

    def __init__(self, max_workers: int = 4,
                 default_timeout: int = 60,
                 default_retries: int = 0):
        """初始化执行器

        Args:
            max_workers: 最大并发数
            default_timeout: 默认超时时间（秒）
            default_retries: 默认重试次数
        """
        self.max_workers = max_workers
        self.default_timeout = default_timeout
        self.default_retries = default_retries

        self.dependency_manager = DependencyManager()
        self.task_handlers: Dict[str, Callable] = {}  # action -> handler

        # 执行状态
        self.execution_id: Optional[str] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

        # 进度回调
        self.progress_callback: Optional[Callable] = None

    def register_handler(self, action: str, handler: Callable) -> None:
        """注册任务处理器

        Args:
            action: 动作名称
            handler: 处理函数，接收 params 参数，返回结果字典
        """
        self.task_handlers[action] = handler

    def add_task(self, task_id: str, action: str, params: Dict[str, Any],
                 dependencies: Optional[List[str]] = None,
                 priority: int = 5,
                 timeout: Optional[int] = None,
                 retries: int = 0) -> bool:
        """添加任务

        Args:
            task_id: 任务 ID
            action: 动作名称
            params: 参数
            dependencies: 依赖任务 ID 列表
            priority: 优先级（1-10）
            timeout: 超时时间（秒）
            retries: 重试次数

        Returns:
            是否成功添加
        """
        if dependencies is None:
            dependencies = []

        task = Task(
            id=task_id,
            name=task_id,
            action=action,
            params=params,
            dependencies=dependencies,
            priority=priority,
            timeout=timeout or self.default_timeout,
            max_retries=retries or self.default_retries
        )

        return self.dependency_manager.add_task(task)

    def _execute_task(self, task: Task) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """执行单个任务

        Args:
            task: 任务对象

        Returns:
            (成功标志，结果，错误信息)
        """
        handler = self.task_handlers.get(task.action)

        if not handler:
            return False, None, f"No handler registered for action: {task.action}"

        try:
            # 执行任务
            result = handler(task.params)
            return True, result, None
        except Exception as e:
            return False, None, str(e)

    async def _execute_task_async(self, task: Task) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """异步执行任务

        Args:
            task: 任务对象

        Returns:
            (成功标志，结果，错误信息)
        """
        loop = asyncio.get_event_loop()

        # 在线程池中执行
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = loop.run_in_executor(executor, self._execute_task, task)

            try:
                success, result, error = await asyncio.wait_for(
                    future,
                    timeout=task.timeout
                )
                return success, result, error
            except asyncio.TimeoutError:
                return False, None, f"Task timed out after {task.timeout} seconds"

    async def execute_all(self) -> Dict[str, Any]:
        """执行所有任务（并行，遵循依赖）

        Returns:
            执行结果
        """
        import uuid
        self.execution_id = str(uuid.uuid4())[:8]
        self.start_time = datetime.now()

        results = {}

        try:
            # 获取并行组
            parallel_groups = self.dependency_manager.get_parallel_groups()

            # 逐组执行
            for group_idx, group in enumerate(parallel_groups):
                group_id = f"group_{group_idx + 1}"

                # 并行执行组内任务
                group_tasks = [self.dependency_manager.get_task(tid) for tid in group]
                group_tasks = [t for t in group_tasks if t is not None]

                group_results = await self._execute_group(group_tasks)

                results[group_id] = {
                    "tasks": group,
                    "results": group_results
                }

                # 通知进度
                if self.progress_callback:
                    self.progress_callback({
                        "event": "group_completed",
                        "group_id": group_id,
                        "tasks": group,
                        "progress": (group_idx + 1) / len(parallel_groups)
                    })

        except ValueError as e:
            # 循环依赖
            return {
                "status": "error",
                "error": str(e),
                "execution_id": self.execution_id
            }

        self.end_time = datetime.now()

        return {
            "status": "success",
            "execution_id": self.execution_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            "results": results,
            "statistics": self.dependency_manager.get_statistics()
        }

    async def _execute_group(self, tasks: List[Task]) -> Dict[str, Any]:
        """执行一组任务（并行）

        Args:
            tasks: 任务列表

        Returns:
            执行结果
        """
        async def execute_with_retry(task: Task) -> Tuple[str, bool, Optional[Dict], Optional[str]]:
            """带重试的执行"""
            last_error = None

            for attempt in range(task.max_retries + 1):
                task.status = TaskStatus.RUNNING.value

                # 通知进度
                if self.progress_callback:
                    self.progress_callback({
                        "event": "task_started",
                        "task_id": task.id,
                        "attempt": attempt + 1
                    })

                success, result, error = await self._execute_task_async(task)

                if success:
                    self.dependency_manager.mark_completed(task.id, result)
                    return task.id, True, result, None

                last_error = error
                task.retry_count = attempt + 1

                # 通知进度
                if self.progress_callback:
                    self.progress_callback({
                        "event": "task_failed",
                        "task_id": task.id,
                        "attempt": attempt + 1,
                        "error": error,
                        "will_retry": attempt < task.max_retries
                    })

            # 所有重试都失败
            self.dependency_manager.mark_failed(task.id, last_error or "Unknown error")
            return task.id, False, None, last_error

        # 并行执行所有任务
        coroutines = [execute_with_retry(task) for task in tasks]
        task_results = await asyncio.gather(*coroutines, return_exceptions=True)

        # 整理结果
        results = {}
        for task_result in task_results:
            if isinstance(task_result, Exception):
                results[f"exception_{id(task_result)}"] = {
                    "success": False,
                    "error": str(task_result)
                }
            else:
                task_id, success, result, error = task_result
                results[task_id] = {
                    "success": success,
                    "result": result,
                    "error": error
                }

        return results

    def execute_sync(self) -> Dict[str, Any]:
        """同步执行所有任务

        Returns:
            执行结果
        """
        return asyncio.run(self.execute_all())

    def get_execution_plan(self) -> Dict[str, Any]:
        """获取执行计划（不执行）

        Returns:
            执行计划
        """
        try:
            parallel_groups = self.dependency_manager.get_parallel_groups()
            execution_order = self.dependency_manager.get_execution_order()
        except ValueError as e:
            return {
                "status": "error",
                "error": str(e)
            }

        return {
            "status": "success",
            "total_tasks": len(self.dependency_manager.tasks),
            "parallel_groups": parallel_groups,
            "execution_order": execution_order,
            "statistics": self.dependency_manager.get_statistics()
        }

    def cancel(self) -> None:
        """取消执行"""
        # 标记所有 pending/ready 任务为跳过
        for task in self.dependency_manager.list_tasks():
            if task.status in [TaskStatus.PENDING.value, TaskStatus.READY.value]:
                task.status = TaskStatus.SKIPPED.value

    def get_progress(self) -> Dict[str, Any]:
        """获取执行进度"""
        stats = self.dependency_manager.get_statistics()
        total = stats["total_tasks"]
        completed = stats["completed"]
        failed = stats["failed"]

        progress = {
            "total": total,
            "completed": completed,
            "failed": failed,
            "remaining": total - completed - failed,
            "percentage": (completed + failed) / total * 100 if total > 0 else 0
        }

        if self.start_time:
            progress["start_time"] = self.start_time.isoformat()
        if self.end_time:
            progress["end_time"] = self.end_time.isoformat()

        return progress
