from unittest.mock import AsyncMock, Mock

from gateway.tasks.manager import CollectionTaskManager
from gateway.tasks.models import TaskStatus, TaskTrigger
from gateway.tasks.store import CollectionTaskStore


def make_manager(tmp_path) -> CollectionTaskManager:
    registry = Mock()
    registry.get.return_value = Mock()
    return CollectionTaskManager(
        CollectionTaskStore(tmp_path / "tasks.sqlite3"),
        registry,
        Mock(),
        Mock(),
    )


async def test_submit_and_wait_records_success(monkeypatch, tmp_path):
    manager = make_manager(tmp_path)

    async def successful_call(*_args, **_kwargs):
        return {
            "isError": False,
            "structuredContent": {"ok": True, "platform": "mock_platform", "count": 2},
        }

    monkeypatch.setattr("gateway.tasks.manager.call_alarm_tool", successful_call)
    accepted, task = await manager.submit_and_wait(
        "mock_platform",
        trigger=TaskTrigger.SCHEDULED,
    )

    assert accepted is True
    assert task.status == TaskStatus.SUCCEEDED
    assert task.trigger == TaskTrigger.SCHEDULED
    assert task.result["count"] == 2
    assert task.started_at is not None
    assert task.finished_at is not None
    assert task.duration_ms is not None


async def test_submit_and_wait_records_sanitized_failure(monkeypatch, tmp_path):
    manager = make_manager(tmp_path)

    async def failed_call(*_args, **_kwargs):
        return {
            "isError": True,
            "structuredContent": {
                "ok": False,
                "error_code": "CREDENTIAL_UNAVAILABLE",
                "message": "The read-only platform credential is unavailable.",
            },
        }

    monkeypatch.setattr("gateway.tasks.manager.call_alarm_tool", failed_call)
    accepted, task = await manager.submit_and_wait(
        "mock_platform",
        trigger=TaskTrigger.MANUAL,
    )

    assert accepted is True
    assert task.status == TaskStatus.FAILED
    assert task.error_code == "CREDENTIAL_UNAVAILABLE"
    assert "password" not in task.error_message.lower()


async def test_scheduled_collection_succeeds_while_delivery_waits_for_retry(
    monkeypatch,
    tmp_path,
):
    manager = make_manager(tmp_path)
    manager.change_processor = AsyncMock()
    manager.change_processor.process.return_value = {
        "new": 1,
        "ongoing": 0,
        "recovered": 0,
        "queued": 1,
        "deduplicated": 0,
        "delivered": 0,
        "retry_wait": 1,
        "dead_letter": 0,
        "delivery_attempts": 1,
    }

    async def successful_collection(*_args, **_kwargs):
        return {
            "isError": False,
            "structuredContent": {"ok": True, "alarms": [{"alarm_id": "alarm-1"}]},
        }

    monkeypatch.setattr("gateway.tasks.manager.call_alarm_tool", successful_collection)
    accepted, task = await manager.submit_and_wait(
        "mock_platform",
        trigger=TaskTrigger.SCHEDULED,
    )

    assert accepted is True
    assert task.status == TaskStatus.SUCCEEDED
    assert task.result["alarm_changes"]["retry_wait"] == 1
