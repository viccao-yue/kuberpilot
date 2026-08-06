"""APScheduler integration for configuration-driven periodic collection."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from gateway.tasks.manager import CollectionTaskManager
from gateway.tasks.models import TaskTrigger
from platforms.loader import PlatformRegistry


class CollectionScheduler:
    def __init__(self, manager: CollectionTaskManager, registry: PlatformRegistry):
        self.manager = manager
        self.registry = registry
        self.scheduler = AsyncIOScheduler(timezone="UTC")

    def start(self) -> None:
        for platform in self.registry.list_enabled():
            interval = platform.alarm_collection_interval_seconds
            if interval is None:
                continue
            self.scheduler.add_job(
                self._run_alarm_collection,
                trigger="interval",
                seconds=interval,
                id=f"{platform.platform}.list_alarms",
                args=[platform.platform],
                coalesce=True,
                max_instances=1,
                misfire_grace_time=max(5, min(120, interval)),
                replace_existing=True,
            )
        self.scheduler.start()

    async def _run_alarm_collection(self, platform: str) -> None:
        await self.manager.submit_and_wait(platform, trigger=TaskTrigger.SCHEDULED)

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
