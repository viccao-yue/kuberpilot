from unittest.mock import AsyncMock, Mock

from gateway.alerts.processor import AlarmChangeProcessor
from gateway.delivery.models import DeliveryStatus
from gateway.delivery.store import DeliveryJobStore
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
    database = tmp_path / "tasks.sqlite3"
    store = CollectionTaskStore(database)
    delivery_store = DeliveryJobStore(database)
    callback = Mock()
    callback.build_payload.side_effect = lambda task_id, platform, item: {
        "id": item.event_id,
        "platform": platform,
        "task_id": task_id,
    }
    worker = AsyncMock()

    async def mark_all_succeeded():
        return await _mark_all_succeeded(delivery_store)

    worker.run_once.side_effect = mark_all_succeeded
    processor = AlarmChangeProcessor(store, delivery_store, callback, worker, 4)

    first = await processor.process("task-1", "mock_platform", [alarm("a-1")])
    second = await processor.process("task-2", "mock_platform", [alarm("a-1")])
    third = await processor.process("task-3", "mock_platform", [])

    assert first["new"] == 1
    assert first["queued"] == 1
    assert first["delivered"] == 1
    assert second["ongoing"] == 1
    assert second["delivered"] == 0
    assert third["recovered"] == 1
    assert len(delivery_store.list(status=DeliveryStatus.SUCCEEDED)) == 2


async def test_processor_advances_snapshot_after_durable_enqueue(tmp_path):
    database = tmp_path / "tasks.sqlite3"
    store = CollectionTaskStore(database)
    delivery_store = DeliveryJobStore(database)
    callback = Mock()
    callback.build_payload.return_value = {"id": "event-1"}
    worker = AsyncMock()
    processor = AlarmChangeProcessor(store, delivery_store, callback, worker, 4)

    result = await processor.process("task-1", "mock_platform", [alarm("a-1")])

    assert result["queued"] == 1
    assert set(store.get_alarm_snapshot("mock_platform"))
    assert delivery_store.list()[0].status == DeliveryStatus.PENDING


async def _mark_all_succeeded(store: DeliveryJobStore) -> int:
    jobs = store.claim_due(limit=20)
    for job in jobs:
        store.mark_succeeded(job.job_id)
    return len(jobs)
