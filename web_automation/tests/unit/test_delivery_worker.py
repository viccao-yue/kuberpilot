import asyncio

import httpx

from gateway.alerts.callback import KuberPilotCallbackClient
from gateway.alerts.differ import AlarmChange, AlarmChangeType
from gateway.delivery.models import DeliveryStatus
from gateway.delivery.store import DeliveryJobStore
from gateway.delivery.worker import DeliveryWorker


def enqueue(store: DeliveryJobStore, *, max_attempts: int = 2):
    change = AlarmChange(
        AlarmChangeType.NEW,
        "fp-1",
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
