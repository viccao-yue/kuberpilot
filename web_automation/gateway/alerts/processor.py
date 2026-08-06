"""Coordinate snapshot comparison, callback delivery and durable updates."""

from typing import Any

from gateway.alerts.callback import KuberPilotCallbackClient
from gateway.alerts.differ import AlarmChangeType, diff_alarm_snapshots, index_alarms
from gateway.tasks.store import CollectionTaskStore


class AlarmChangeProcessor:
    def __init__(
        self,
        store: CollectionTaskStore,
        callback_client: KuberPilotCallbackClient,
    ):
        self.store = store
        self.callback_client = callback_client

    async def process(
        self,
        task_id: str,
        platform: str,
        alarms: list[dict[str, Any]],
    ) -> dict[str, Any]:
        previous = self.store.get_alarm_snapshot(platform)
        current = index_alarms(platform, alarms)
        changes, ongoing_count = diff_alarm_snapshots(previous, current)
        attempts = 0
        for change in changes:
            attempts += await self.callback_client.deliver(task_id, platform, change)
        self.store.replace_alarm_snapshot(platform, current)
        return {
            "new": len([item for item in changes if item.change_type == AlarmChangeType.NEW]),
            "ongoing": ongoing_count,
            "recovered": len(
                [item for item in changes if item.change_type == AlarmChangeType.RECOVERED]
            ),
            "delivered": len(changes),
            "delivery_attempts": attempts,
        }
