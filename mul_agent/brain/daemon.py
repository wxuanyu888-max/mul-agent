"""Agent Daemon - 后台守护机制"""

import time
import threading
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from mul_agent.brain.router import Router
from mul_agent.brain.config_manager import ConfigManager


class AgentState(Enum):
    """Agent 状态"""
    WORKING = "working"   # 工作状态
    RESTING = "resting"   # 休息状态


@dataclass
class ScheduledTask:
    """定时任务"""
    id: str
    name: str
    action: str          # heart, bash, 或其他路由
    params: Dict[str, Any]
    interval: int         # 间隔秒数
    enabled: bool = True
    last_run: Optional[float] = None
    next_run: Optional[float] = None
    created_at: float = field(default_factory=time.time)


class AgentDaemon:
    """
    Agent 守护进程

    功能：
    1. 状态管理：工作/休息切换
    2. 空闲检测：自动进入休息状态
    3. 定时任务：定期执行任务
    4. 自我成长：调用 heart 路由
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        idle_timeout: int = 300,      # 5分钟无活动进入休息
        grow_interval: int = 3600,     # 1小时自我成长一次
        check_interval: int = 10       # 10秒检查一次
    ):
        self.config_manager = config_manager
        self.router = Router(config_manager)

        # 状态配置
        self.idle_timeout = idle_timeout
        self.grow_interval = grow_interval
        self.check_interval = check_interval

        # 运行时状态
        self.state = AgentState.WORKING
        self.last_activity = time.time()
        self.last_growth = time.time()

        # 定时任务
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self._task_lock = threading.Lock()

        # 回调函数
        self.on_state_change: Optional[Callable[[AgentState, AgentState], None]] = None
        self.on_task_complete: Optional[Callable[[str, Dict], None]] = None
        self.on_growth_complete: Optional[Callable[[Dict], None]] = None

        # 控制标志
        self._running = False
        self._daemon_thread: Optional[threading.Thread] = None

    def add_scheduled_task(
        self,
        name: str,
        action: str,
        params: Dict[str, Any],
        interval: int
    ) -> str:
        """
        添加定时任务

        Args:
            name: 任务名称
            action: 路由动作 (heart, bash, memory 等)
            params: 路由参数
            interval: 执行间隔(秒)

        Returns:
            任务 ID
        """
        task_id = str(uuid.uuid4())[:8]
        task = ScheduledTask(
            id=task_id,
            name=name,
            action=action,
            params=params,
            interval=interval,
            next_run=time.time() + interval
        )

        with self._task_lock:
            self.scheduled_tasks[task_id] = task

        return task_id

    def remove_scheduled_task(self, task_id: str) -> bool:
        """移除定时任务"""
        with self._task_lock:
            if task_id in self.scheduled_tasks:
                del self.scheduled_tasks[task_id]
                return True
        return False

    def list_scheduled_tasks(self) -> list:
        """列出所有定时任务"""
        with self._task_lock:
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "action": t.action,
                    "interval": t.interval,
                    "enabled": t.enabled,
                    "last_run": t.last_run,
                    "next_run": t.next_run
                }
                for t in self.scheduled_tasks.values()
            ]

    def add_default_growth_task(self):
        """添加默认的自我成长任务"""
        self.add_scheduled_task(
            name="自我成长",
            action="heart",
            params={"trigger": "scheduled", "focus": "growth"},
            interval=self.grow_interval
        )

    def record_activity(self):
        """记录用户活动，切换到工作状态"""
        self.last_activity = time.time()
        if self.state == AgentState.RESTING:
            old_state = self.state
            self.state = AgentState.WORKING
            if self.on_state_change:
                self.on_state_change(old_state, self.state)

    def get_status(self) -> Dict[str, Any]:
        """获取守护进程状态"""
        idle_time = time.time() - self.last_activity

        return {
            "state": self.state.value,
            "idle_time": idle_time,
            "should_rest": idle_time >= self.idle_timeout and self.state == AgentState.WORKING,
            "last_growth": self.last_growth,
            "time_since_growth": time.time() - self.last_growth,
            "scheduled_tasks_count": len(self.scheduled_tasks),
            "scheduled_tasks": self.list_scheduled_tasks()
        }

    def _check_idle(self) -> bool:
        """检查是否应该进入休息状态"""
        idle_time = time.time() - self.last_activity
        return idle_time >= self.idle_timeout

    def _execute_task(self, task: ScheduledTask) -> Dict[str, Any]:
        """执行定时任务"""
        try:
            result = self.router.dispatch(task.action, task.params)
            task.last_run = time.time()
            task.next_run = time.time() + task.interval

            if self.on_task_complete:
                self.on_task_complete(task.id, result)

            return result
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _run_growth(self) -> Dict[str, Any]:
        """执行自我成长"""
        result = self.router.dispatch("heart", {
            "trigger": "scheduled",
            "focus": "growth"
        })
        self.last_growth = time.time()

        if self.on_growth_complete:
            self.on_growth_complete(result)

        return result

    def _daemon_loop(self):
        """守护进程主循环"""
        while self._running:
            try:
                # 检查是否应该进入休息状态
                if self.state == AgentState.WORKING and self._check_idle():
                    old_state = self.state
                    self.state = AgentState.RESTING
                    if self.on_state_change:
                        self.on_state_change(old_state, self.state)

                # 休息状态下执行定时任务
                if self.state == AgentState.RESTING:
                    current_time = time.time()

                    # 检查并执行到期的任务
                    with self._task_lock:
                        for task in self.scheduled_tasks.values():
                            if task.enabled and task.next_run and current_time >= task.next_run:
                                self._execute_task(task)

                time.sleep(self.check_interval)

            except Exception as e:
                print(f"Daemon error: {e}")
                time.sleep(self.check_interval)

    def start(self):
        """启动守护进程"""
        if self._running:
            return

        self._running = True
        self._daemon_thread = threading.Thread(target=self._daemon_loop, daemon=True)
        self._daemon_thread.start()

    def stop(self):
        """停止守护进程"""
        self._running = False
        if self._daemon_thread:
            self._daemon_thread.join(timeout=5)

    def force_rest(self):
        """强制进入休息状态"""
        if self.state == AgentState.WORKING:
            old_state = self.state
            self.state = AgentState.RESTING
            if self.on_state_change:
                self.on_state_change(old_state, self.state)

    def force_work(self):
        """强制进入工作状态"""
        self.record_activity()
        if self.state == AgentState.RESTING:
            old_state = self.state
            self.state = AgentState.WORKING
            if self.on_state_change:
                self.on_state_change(old_state, self.state)


def create_daemon(
    config_dir: Path,
    idle_timeout: int = 300,
    grow_interval: int = 3600
) -> AgentDaemon:
    """创建并配置守护进程"""
    config_manager = ConfigManager(config_dir)
    daemon = AgentDaemon(
        config_manager=config_manager,
        idle_timeout=idle_timeout,
        grow_interval=grow_interval
    )
    return daemon
