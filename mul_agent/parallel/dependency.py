"""Dependency Manager - 任务依赖管理"""

from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import hashlib


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    READY = "ready"  # 依赖已满足，可以执行
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"  # 因依赖失败而跳过


@dataclass
class Task:
    """任务数据结构"""
    id: str
    name: str
    action: str
    params: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    status: str = TaskStatus.PENDING.value
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    priority: int = 5  # 1-10, 1 最高
    timeout: Optional[int] = None  # 超时时间（秒）
    retry_count: int = 0
    max_retries: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "action": self.action,
            "params": self.params,
            "dependencies": self.dependencies,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "priority": self.priority,
            "timeout": self.timeout,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """从字典创建"""
        return cls(**data)


class DependencyManager:
    """依赖管理器

    功能：
    - 任务依赖图管理
    - 依赖关系验证
    - 拓扑排序
    - 并行组识别
    """

    def __init__(self):
        self.tasks: Dict[str, Task] = {}
        self.dependency_graph: Dict[str, List[str]] = defaultdict(list)  # task_id -> dependent tasks
        self.reverse_graph: Dict[str, List[str]] = defaultdict(list)  # task_id -> dependencies

    def add_task(self, task: Task) -> bool:
        """添加任务

        Args:
            task: 任务对象

        Returns:
            是否成功
        """
        if task.id in self.tasks:
            return False

        self.tasks[task.id] = task

        # 更新依赖图
        for dep in task.dependencies:
            self.dependency_graph[dep].append(task.id)
            self.reverse_graph[task.id].append(dep)

        return True

    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        if task_id not in self.tasks:
            return False

        task = self.tasks[task_id]

        # 从依赖图中移除
        for dep in task.dependencies:
            if task_id in self.dependency_graph[dep]:
                self.dependency_graph[dep].remove(task_id)

        del self.reverse_graph[task_id]
        del self.tasks[task_id]

        return True

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        return self.tasks.get(task_id)

    def list_tasks(self, status: Optional[str] = None) -> List[Task]:
        """列出任务

        Args:
            status: 状态过滤
        """
        tasks = list(self.tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        return tasks

    def get_ready_tasks(self) -> List[Task]:
        """获取所有已就绪（依赖已满足）的任务"""
        ready = []

        for task in self.tasks.values():
            if task.status != TaskStatus.PENDING.value:
                continue

            if self._are_dependencies_met(task):
                task.status = TaskStatus.READY.value
                ready.append(task)

        # 按优先级排序
        ready.sort(key=lambda t: t.priority)

        return ready

    def _are_dependencies_met(self, task: Task) -> bool:
        """检查依赖是否已满足"""
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task:
                # 依赖不存在，视为失败
                return False
            if dep_task.status == TaskStatus.FAILED.value:
                return False
            if dep_task.status != TaskStatus.COMPLETED.value:
                return False

        return True

    def mark_completed(self, task_id: str, result: Optional[Dict] = None) -> bool:
        """标记任务为完成"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        task.status = TaskStatus.COMPLETED.value
        task.result = result

        # 更新依赖此任务的任务状态
        self._update_dependents(task_id)

        return True

    def mark_failed(self, task_id: str, error: str) -> bool:
        """标记任务为失败"""
        task = self.tasks.get(task_id)
        if not task:
            return False

        task.status = TaskStatus.FAILED.value
        task.error = error

        # 标记依赖此任务的任务为跳过
        self._mark_dependents_as_skipped(task_id)

        return True

    def _update_dependents(self, task_id: str) -> None:
        """更新依赖此任务的任务状态"""
        for dependent_id in self.dependency_graph[task_id]:
            dep_task = self.tasks.get(dependent_id)
            if dep_task and dep_task.status == TaskStatus.PENDING.value:
                # 检查是否所有依赖都已完成
                if self._are_dependencies_met(dep_task):
                    dep_task.status = TaskStatus.READY.value

    def _mark_dependents_as_skipped(self, task_id: str) -> None:
        """标记依赖此任务的任务为跳过"""
        for dependent_id in self.dependency_graph[task_id]:
            dep_task = self.tasks.get(dependent_id)
            if dep_task and dep_task.status in [TaskStatus.PENDING.value, TaskStatus.READY.value]:
                dep_task.status = TaskStatus.SKIPPED.value
                dep_task.error = f"Dependency {task_id} failed"
                # 递归标记
                self._mark_dependents_as_skipped(dependent_id)

    def get_execution_order(self) -> List[str]:
        """获取执行顺序（拓扑排序）

        Returns:
            任务 ID 列表，按依赖顺序排列
        """
        # Kahn 算法
        in_degree = {task_id: len(deps) for task_id, deps in self.reverse_graph.items()}

        # 添加入度为 0 的任务
        for task_id in self.tasks:
            if task_id not in in_degree:
                in_degree[task_id] = 0

        queue = [tid for tid, degree in in_degree.items() if degree == 0]
        result = []

        while queue:
            # 按优先级排序
            queue.sort(key=lambda t: self.tasks[t].priority if t in self.tasks else 5)
            task_id = queue.pop(0)
            result.append(task_id)

            for dependent_id in self.dependency_graph[task_id]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    queue.append(dependent_id)

        if len(result) != len(self.tasks):
            # 存在循环依赖
            raise ValueError("Circular dependency detected")

        return result

    def get_parallel_groups(self) -> List[List[str]]:
        """获取并行执行组

        Returns:
            任务 ID 列表的列表，每个子列表中的任务可以并行执行
        """
        groups = []
        remaining = set(self.tasks.keys())

        while remaining:
            # 找到所有入度为 0 的任务
            ready = []
            for task_id in remaining:
                task = self.tasks[task_id]
                deps_met = all(
                    dep not in remaining
                    for dep in task.dependencies
                )
                if deps_met:
                    ready.append(task_id)

            if not ready:
                # 存在循环依赖
                raise ValueError("Circular dependency detected")

            groups.append(ready)
            remaining -= set(ready)

        return groups

    def has_circular_dependency(self) -> bool:
        """检查是否存在循环依赖"""
        try:
            self.get_execution_order()
            return False
        except ValueError:
            return True

    def get_dependency_chain(self, task_id: str) -> List[str]:
        """获取任务的依赖链（所有祖先依赖）

        Args:
            task_id: 任务 ID

        Returns:
            依赖任务 ID 列表
        """
        chain = []
        visited = set()

        def dfs(tid):
            if tid in visited:
                return
            visited.add(tid)

            for dep in self.reverse_graph.get(tid, []):
                chain.append(dep)
                dfs(dep)

        dfs(task_id)
        return list(reversed(chain))

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "total_tasks": len(self.tasks),
            "pending": 0,
            "ready": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "skipped": 0
        }

        for task in self.tasks.values():
            status = task.status
            if status in stats:
                stats[status] += 1

        return stats
