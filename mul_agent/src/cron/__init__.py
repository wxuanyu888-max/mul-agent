"""
Cron - 定时任务系统
"""

__all__ = ["CronScheduler", "CronJob"]


class CronJob:
    """定时任务"""

    def __init__(self, name: str, cron_expression: str, callback: callable, enabled: bool = True):
        self.name = name
        self.cron_expression = cron_expression
        self.callback = callback
        self.enabled = enabled

    async def run(self) -> None:
        if self.enabled:
            await self.callback()


class CronScheduler:
    """调度器"""

    def __init__(self):
        self._jobs: dict[str, CronJob] = {}
        self._running = False

    def add(self, job: CronJob) -> None:
        self._jobs[job.name] = job

    def remove(self, name: str) -> None:
        self._jobs.pop(name, None)

    def list(self) -> list[str]:
        return list(self._jobs.keys())
