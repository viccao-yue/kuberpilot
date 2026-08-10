from unittest.mock import Mock

import httpx

from gateway.alerts.differ import AlarmChange, AlarmChangeType
from gateway.app import app
from gateway.delivery.models import DeliveryStatus
from gateway.delivery.store import DeliveryJobStore
from gateway.dependencies import get_delivery_store, get_delivery_worker
from gateway.tasks.store import utc_now


async def request(method: str, path: str, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def make_dead_letter(store: DeliveryJobStore):
    change = AlarmChange(
        AlarmChangeType.NEW,
        "fp-1",
        {"alarm_id": "alarm-1", "occurred_at": "2026-08-07T10:00:00Z"},
    )
    job = store.enqueue_changes(
        "task-1",
        "mock_platform",
        [change],
        [{"id": change.event_id}],
        {},
        max_attempts=1,
    )[0]
    claimed = store.claim_due()[0]
    return store.mark_failed(
        claimed.job_id,
        next_attempt_at=utc_now(),
        error_code="HTTPSTATUSERROR",
        error_message="KuberPilot callback request failed",
    )


async def test_list_detail_and_manual_dead_letter_retry(tmp_path):
    store = DeliveryJobStore(tmp_path / "tasks.sqlite3")
    dead_letter = make_dead_letter(store)
    worker = Mock()
    worker.is_running = True
    app.dependency_overrides[get_delivery_store] = lambda: store
    app.dependency_overrides[get_delivery_worker] = lambda: worker
    try:
        listed = await request("GET", "/api/v1/delivery-jobs?status=dead_letter")
        detail = await request("GET", f"/api/v1/delivery-jobs/{dead_letter.job_id}")
        retried = await request(
            "POST",
            f"/api/v1/delivery-jobs/{dead_letter.job_id}/retry",
        )
    finally:
        app.dependency_overrides.clear()

    assert listed.status_code == 200
    assert [item["job_id"] for item in listed.json()] == [dead_letter.job_id]
    assert detail.json()["status"] == DeliveryStatus.DEAD_LETTER.value
    assert retried.status_code == 202
    assert retried.json()["job"]["status"] == DeliveryStatus.PENDING.value
    worker.wake.assert_called_once_with()


async def test_retry_rejects_non_dead_letter_and_missing_job(tmp_path):
    store = DeliveryJobStore(tmp_path / "tasks.sqlite3")
    dead_letter = make_dead_letter(store)
    store.retry_dead_letter(dead_letter.job_id)
    worker = Mock()
    worker.is_running = True
    app.dependency_overrides[get_delivery_store] = lambda: store
    app.dependency_overrides[get_delivery_worker] = lambda: worker
    try:
        conflict = await request(
            "POST",
            f"/api/v1/delivery-jobs/{dead_letter.job_id}/retry",
        )
        missing = await request("POST", "/api/v1/delivery-jobs/missing/retry")
    finally:
        app.dependency_overrides.clear()

    assert conflict.status_code == 409
    assert missing.status_code == 404


async def test_retry_keeps_dead_letter_when_worker_is_disabled(tmp_path):
    store = DeliveryJobStore(tmp_path / "tasks.sqlite3")
    dead_letter = make_dead_letter(store)
    worker = Mock()
    worker.is_running = False
    app.dependency_overrides[get_delivery_store] = lambda: store
    app.dependency_overrides[get_delivery_worker] = lambda: worker
    try:
        response = await request(
            "POST",
            f"/api/v1/delivery-jobs/{dead_letter.job_id}/retry",
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert store.get(dead_letter.job_id).status == DeliveryStatus.DEAD_LETTER
