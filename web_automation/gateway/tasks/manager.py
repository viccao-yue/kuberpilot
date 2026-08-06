"""Execute alarm collections while recording their lifecycle."""

import asyncio
from collections.abc import Coroutine
from time import perf_counter
from typing import Any
from uuid import uuid4

from credentials.environment import EnvironmentCredentialProvider
from gateway.alerts.callback import CallbackDeliveryError
from gateway.alerts.processor import AlarmChangeProcessor
from gateway.mcp.alarm_tool import call_alarm_tool
from gateway.tasks.models import CollectionTask, TaskStatus, TaskTrigger
from gateway.tasks.store import CollectionTaskStore, utc_now
from network.checker import ConnectivityChecker
from platforms.loader import PlatformNotFoundError, PlatformRegistry


class CollectionTaskManager:
    def __init__(
        self,
        store: CollectionTaskStore,
        registry: PlatformRegistry,
        checker: ConnectivityChecker,
        credential_provider: EnvironmentCredentialProvider,
        change_processor: AlarmChangeProcessor | None = None,
    ):
        self.store = store
        self.registry = registry
        self.checker = checker
        self.credential_provider = credential_provider
        self.change_processor = change_processor
        self._background_tasks: set[asyncio.Task] = set()

    def submit(
        self,
        platform: str,
        *,
        trigger: TaskTrigger,
        severity: str = "all",
        limit: int = 20,
    ) -> tuple[bool, CollectionTask]:
        self.registry.get(platform)
        task = CollectionTask(
            task_id=str(uuid4()),
            platform=platform,
            trigger=trigger,
            status=TaskStatus.QUEUED,
            severity=severity,
            limit=limit,
            created_at=utc_now(),
        )
        accepted, stored_task = self.store.create_if_platform_idle(task)
        if accepted:
            self._start_background(self._execute(task))
        return accepted, stored_task

    async def submit_and_wait(
        self,
        platform: str,
        *,
        trigger: TaskTrigger,
        severity: str = "all",
        limit: int = 20,
    ) -> tuple[bool, CollectionTask]:
        """Deterministic entry point used by scheduler jobs and integration tests."""
        self.registry.get(platform)
        task = CollectionTask(
            task_id=str(uuid4()),
            platform=platform,
            trigger=trigger,
            status=TaskStatus.QUEUED,
            severity=severity,
            limit=limit,
            created_at=utc_now(),
        )
        accepted, stored_task = self.store.create_if_platform_idle(task)
        if not accepted:
            return False, stored_task
        await self._execute(task)
        return True, self.store.get(task.task_id) or task

    async def _execute(self, task: CollectionTask) -> None:
        started_at = utc_now()
        started_counter = perf_counter()
        self.store.mark_running(task.task_id, started_at)
        try:
            result = await call_alarm_tool(
                {
                    "platform": task.platform,
                    "severity": task.severity,
                    "limit": task.limit,
                },
                self.registry,
                self.checker,
                self.credential_provider,
            )
            payload = result.get("structuredContent") or {}
            if result.get("isError"):
                duration_ms = max(0, round((perf_counter() - started_counter) * 1000))
                self.store.mark_failed(
                    task.task_id,
                    utc_now(),
                    duration_ms,
                    str(payload.get("error_code") or "ALARM_COLLECTION_FAILED"),
                    str(payload.get("message") or "Alarm collection failed"),
                )
                return
            if task.trigger == TaskTrigger.SCHEDULED and self.change_processor:
                try:
                    payload["alarm_changes"] = await self.change_processor.process(
                        task.task_id,
                        task.platform,
                        list(payload.get("alarms") or []),
                    )
                except CallbackDeliveryError as exc:
                    duration_ms = max(0, round((perf_counter() - started_counter) * 1000))
                    self.store.mark_failed(
                        task.task_id,
                        utc_now(),
                        duration_ms,
                        "CALLBACK_DELIVERY_FAILED",
                        f"KuberPilot callback failed after {exc.attempts} attempts",
                    )
                    return
            duration_ms = max(0, round((perf_counter() - started_counter) * 1000))
            self.store.mark_succeeded(task.task_id, utc_now(), duration_ms, payload)
        except Exception as exc:
            duration_ms = max(0, round((perf_counter() - started_counter) * 1000))
            self.store.mark_failed(
                task.task_id,
                utc_now(),
                duration_ms,
                "UNEXPECTED_COLLECTION_ERROR",
                f"Alarm collection failed: {type(exc).__name__}",
            )

    def _start_background(self, coroutine: Coroutine[Any, Any, None]) -> None:
        background_task = asyncio.create_task(coroutine)
        self._background_tasks.add(background_task)
        background_task.add_done_callback(self._background_tasks.discard)

    async def drain(self) -> None:
        if self._background_tasks:
            await asyncio.gather(*tuple(self._background_tasks), return_exceptions=True)


def is_unknown_platform(exc: Exception) -> bool:
    return isinstance(exc, PlatformNotFoundError)
