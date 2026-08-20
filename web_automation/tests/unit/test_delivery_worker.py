import asyncio
from unittest.mock import AsyncMock

import httpx

from gateway.alerts.callback import KuberPilotCallbackClient
from gateway.alerts.differ import AlarmChange, AlarmChangeType
from gateway.delivery.models import DeliveryStatus
from gateway.delivery.store import DeliveryJobStore
from gateway.delivery.worker import DeliveryWorker


def enqueue(
    store: DeliveryJobStore,
    *,
    max_attempts: int = 2,
    fingerprint: str = "fp-1",
):
    change = AlarmChange(
        AlarmChangeType.NEW,
        fingerprint,
        {"alarm_id": "alarm-1", "occurred_at": "2026-08-07T10:00:00Z"},
    )
    return store.enqueue_changes(
        "task-1",
        "mock_platform",
        [change],
        [{"id": change.event_id}],
        {},
        max_attempts=max_attempts,
    )[0]


async def test_worker_retries_then_succeeds_without_duplicate_job(tmp_path):
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503 if calls == 1 else 202)

    store = DeliveryJobStore(tmp_path / "tasks.sqlite3")
    job = enqueue(store)
    client = KuberPilotCallbackClient(
        "http://kuberpilot.local/callback",
        "token",
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )
    worker = DeliveryWorker(
        store,
        client,
        retry_delays_seconds=(0,),
        poll_interval_seconds=0.01,
        batch_size=20,
    )

    await worker.run_once()
    assert store.get(job.job_id).status == DeliveryStatus.RETRY_WAIT
    await worker.run_once()

    assert calls == 2
    assert store.get(job.job_id).status == DeliveryStatus.SUCCEEDED
    assert len(store.list()) == 1


async def test_worker_moves_exhausted_job_to_dead_letter(tmp_path):
    store = DeliveryJobStore(tmp_path / "tasks.sqlite3")
    job = enqueue(store, max_attempts=1)
    client = KuberPilotCallbackClient(
        "http://kuberpilot.local/callback",
        "token",
        timeout_seconds=1,
        transport=httpx.MockTransport(lambda _request: httpx.Response(503)),
    )
    worker = DeliveryWorker(
        store,
        client,
        retry_delays_seconds=(),
        poll_interval_seconds=0.01,
        batch_size=20,
    )

    await worker.run_once()

    assert store.get(job.job_id).status == DeliveryStatus.DEAD_LETTER


async def test_background_worker_recovers_interrupted_job_on_start(tmp_path):
    database = tmp_path / "tasks.sqlite3"
    store = DeliveryJobStore(database)
    job = enqueue(store)
    store.claim_due()
    client = KuberPilotCallbackClient(
        "http://kuberpilot.local/callback",
        "token",
        timeout_seconds=1,
        transport=httpx.MockTransport(lambda _request: httpx.Response(202)),
    )
    restarted_store = DeliveryJobStore(database)
    worker = DeliveryWorker(
        restarted_store,
        client,
        retry_delays_seconds=(0,),
        poll_interval_seconds=0.01,
        batch_size=20,
    )

    worker.start()
    for _ in range(20):
        if restarted_store.get(job.job_id).status == DeliveryStatus.SUCCEEDED:
            break
        await asyncio.sleep(0.01)
    await worker.shutdown()

    assert restarted_store.get(job.job_id).status == DeliveryStatus.SUCCEEDED


async def test_background_worker_survives_claim_error_and_processes_job(
    tmp_path,
    monkeypatch,
):
    store = DeliveryJobStore(tmp_path / "tasks.sqlite3")
    job = enqueue(store)
    original_claim_due = store.claim_due
    claim_calls = 0

    def flaky_claim_due(*, limit: int):
        nonlocal claim_calls
        claim_calls += 1
        if claim_calls == 1:
            raise RuntimeError("temporary database error")
        return original_claim_due(limit=limit)

    monkeypatch.setattr(store, "claim_due", flaky_claim_due)
    client = KuberPilotCallbackClient(
        "http://kuberpilot.local/callback",
        "token",
        timeout_seconds=1,
        transport=httpx.MockTransport(lambda _request: httpx.Response(202)),
    )
    worker = DeliveryWorker(
        store,
        client,
        retry_delays_seconds=(0,),
        poll_interval_seconds=0.01,
        batch_size=20,
    )

    worker.start()
    for _ in range(50):
        if store.get(job.job_id).status == DeliveryStatus.SUCCEEDED:
            break
        await asyncio.sleep(0.01)

    assert worker.is_running is True
    assert store.get(job.job_id).status == DeliveryStatus.SUCCEEDED
    assert worker.health()["last_error"]["stage"] == "worker_loop"
    await worker.shutdown()


async def test_unexpected_callback_error_is_isolated_and_retried(tmp_path):
    store = DeliveryJobStore(tmp_path / "tasks.sqlite3")
    job = enqueue(store)
    client = AsyncMock()
    client.deliver_payload.side_effect = [RuntimeError("unexpected"), None]
    worker = DeliveryWorker(
        store,
        client,
        retry_delays_seconds=(0,),
        poll_interval_seconds=0.01,
        batch_size=20,
    )

    await worker.run_once()
    assert store.get(job.job_id).status == DeliveryStatus.RETRY_WAIT
    await worker.run_once()

    assert store.get(job.job_id).status == DeliveryStatus.SUCCEEDED
    assert client.deliver_payload.await_count == 2
    assert worker.health()["last_error"]["stage"] == "callback"


async def test_unexpected_callback_error_does_not_block_later_job_in_batch(tmp_path):
    store = DeliveryJobStore(tmp_path / "tasks.sqlite3")
    first = enqueue(store, fingerprint="fp-1")
    second = enqueue(store, fingerprint="fp-2")
    client = AsyncMock()
    client.deliver_payload.side_effect = [RuntimeError("unexpected"), None]
    worker = DeliveryWorker(
        store,
        client,
        retry_delays_seconds=(0,),
        poll_interval_seconds=0.01,
        batch_size=20,
    )

    await worker.run_once()

    assert store.get(first.job_id).status == DeliveryStatus.RETRY_WAIT
    assert store.get(second.job_id).status == DeliveryStatus.SUCCEEDED
    assert client.deliver_payload.await_count == 2


async def test_failure_state_write_error_releases_job_for_retry(tmp_path, monkeypatch):
    store = DeliveryJobStore(tmp_path / "tasks.sqlite3")
    job = enqueue(store)
    original_mark_failed = store.mark_failed
    update_calls = 0

    def flaky_mark_failed(*args, **kwargs):
        nonlocal update_calls
        update_calls += 1
        if update_calls == 1:
            raise RuntimeError("temporary failure state write error")
        return original_mark_failed(*args, **kwargs)

    monkeypatch.setattr(store, "mark_failed", flaky_mark_failed)
    client = KuberPilotCallbackClient(
        "http://kuberpilot.local/callback",
        "token",
        timeout_seconds=1,
        transport=httpx.MockTransport(lambda _request: httpx.Response(503)),
    )
    worker = DeliveryWorker(
        store,
        client,
        retry_delays_seconds=(0,),
        poll_interval_seconds=0.01,
        batch_size=20,
    )

    await worker.run_once()

    recovered = store.get(job.job_id)
    assert recovered.status == DeliveryStatus.RETRY_WAIT
    assert recovered.last_error_code == "DELIVERY_STATE_UPDATE_FAILED"
    assert worker.health()["last_error"]["stage"] == "mark_failed"


async def test_success_state_write_error_releases_job_for_retry(tmp_path, monkeypatch):
    store = DeliveryJobStore(tmp_path / "tasks.sqlite3")
    job = enqueue(store)
    original_mark_succeeded = store.mark_succeeded
    update_calls = 0

    def flaky_mark_succeeded(job_id: str):
        nonlocal update_calls
        update_calls += 1
        if update_calls == 1:
            raise RuntimeError("temporary state write error")
        return original_mark_succeeded(job_id)

    monkeypatch.setattr(store, "mark_succeeded", flaky_mark_succeeded)
    client = AsyncMock()
    worker = DeliveryWorker(
        store,
        client,
        retry_delays_seconds=(0,),
        poll_interval_seconds=0.01,
        batch_size=20,
    )

    await worker.run_once()
    recovered = store.get(job.job_id)
    assert recovered.status == DeliveryStatus.RETRY_WAIT
    assert recovered.last_error_code == "DELIVERY_STATE_UPDATE_FAILED"
    await worker.run_once()

    assert store.get(job.job_id).status == DeliveryStatus.SUCCEEDED
    assert client.deliver_payload.await_count == 2


async def test_shutdown_does_not_reraise_failed_background_task(tmp_path):
    store = DeliveryJobStore(tmp_path / "tasks.sqlite3")
    client = AsyncMock()
    worker = DeliveryWorker(
        store,
        client,
        retry_delays_seconds=(0,),
        poll_interval_seconds=0.01,
        batch_size=20,
    )

    async def failed_task():
        raise RuntimeError("background failure")

    worker._task = asyncio.create_task(failed_task())
    await asyncio.sleep(0)
    await worker.shutdown()

    assert worker.is_running is False
    assert worker.health()["last_error"]["stage"] == "shutdown"
