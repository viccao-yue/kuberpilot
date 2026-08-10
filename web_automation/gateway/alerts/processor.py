"""Persist alarm changes before reliable background callback delivery."""

from typing import Any

from gateway.alerts.callback import KuberPilotCallbackClient
from gateway.alerts.differ import AlarmChangeType, diff_alarm_snapshots, index_alarms
from gateway.delivery.models import DeliveryStatus
from gateway.delivery.store import DeliveryJobStore
from gateway.delivery.worker import DeliveryWorker
from gateway.tasks.store import CollectionTaskStore


class AlarmChangeProcessor:
    def __init__(
        self,
        store: CollectionTaskStore,
        delivery_store: DeliveryJobStore,
        callback_client: KuberPilotCallbackClient,
        delivery_worker: DeliveryWorker,
        max_attempts: int,
    ):
        self.store = store
        self.delivery_store = delivery_store
        self.callback_client = callback_client
        self.delivery_worker = delivery_worker
        self.max_attempts = max_attempts

    async def process(
        self,
        task_id: str,
        platform: str,
        alarms: list[dict[str, Any]],
    ) -> dict[str, Any]:
        previous = self.store.get_alarm_snapshot(platform)
        current = index_alarms(platform, alarms)
        changes, ongoing_count = diff_alarm_snapshots(previous, current)
        payloads = [
            self.callback_client.build_payload(task_id, platform, change)
            for change in changes
        ]
        jobs = self.delivery_store.enqueue_changes(
            task_id,
            platform,
            changes,
            payloads,
            current,
            max_attempts=self.max_attempts,
        )
        # Advancing the snapshot is safe after the outbox transaction commits: any
        # callback not yet sent can be recovered from delivery_jobs after restart.
        if jobs:
            await self.delivery_worker.run_once()
        refreshed_jobs = [
            job
            for queued_job in jobs
            if (job := self.delivery_store.get(queued_job.job_id)) is not None
        ]
        newly_queued = len([job for job in jobs if job.task_id == task_id])
        return {
            "new": len([item for item in changes if item.change_type == AlarmChangeType.NEW]),
            "ongoing": ongoing_count,
            "recovered": len(
                [item for item in changes if item.change_type == AlarmChangeType.RECOVERED]
            ),
            "queued": newly_queued,
            "deduplicated": len(changes) - newly_queued,
            "delivered": len(
                [job for job in refreshed_jobs if job.status == DeliveryStatus.SUCCEEDED]
            ),
            "retry_wait": len(
                [job for job in refreshed_jobs if job.status == DeliveryStatus.RETRY_WAIT]
            ),
            "dead_letter": len(
                [job for job in refreshed_jobs if job.status == DeliveryStatus.DEAD_LETTER]
            ),
            "delivery_attempts": sum(job.attempt_count for job in refreshed_jobs),
        }
