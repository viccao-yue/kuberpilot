from unittest.mock import AsyncMock

import pytest

from gateway.alerts.callback import CallbackDeliveryError
from gateway.alerts.processor import AlarmChangeProcessor
from gateway.tasks.store import CollectionTaskStore


def alarm(alarm_id: str) -> dict:
    return {
        "alarm_id": alarm_id,
        "severity": "warning",
        "resource_id": "host-1",
        "resource_type": "host",
        "resource_name": "host-1",
        "title": "Memory low",
        "description": "Memory below threshold",
        "occurred_at": "2026-08-05T10:00:00+08:00",
    }


async def test_processor_delivers_only_changes_and_updates_snapshot(tmp_path):
    store = CollectionTaskStore(tmp_path / "tasks.sqlite3")
    callback = AsyncMock()
    callback.deliver.return_value = 1
    processor = AlarmChangeProcessor(store, callback)

    first = await processor.process("task-1", "mock_platform", [alarm("a-1")])
    second = await processor.process("task-2", "mock_platform", [alarm("a-1")])
    third = await processor.process("task-3", "mock_platform", [])

    assert first == {
        "new": 1,
        "ongoing": 0,
        "recovered": 0,
        "delivered": 1,
        "delivery_attempts": 1,
    }
    assert second["ongoing"] == 1
    assert second["delivered"] == 0
    assert third["recovered"] == 1
    assert callback.deliver.await_count == 2


async def test_processor_does_not_advance_snapshot_when_callback_fails(tmp_path):
    store = CollectionTaskStore(tmp_path / "tasks.sqlite3")
    callback = AsyncMock()
    callback.deliver.side_effect = CallbackDeliveryError(4, "HTTPStatusError")
    processor = AlarmChangeProcessor(store, callback)

    with pytest.raises(CallbackDeliveryError):
        await processor.process("task-1", "mock_platform", [alarm("a-1")])

    assert store.get_alarm_snapshot("mock_platform") == {}
