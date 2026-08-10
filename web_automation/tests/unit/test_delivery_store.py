from datetime import timedelta

from gateway.alerts.differ import AlarmChange, AlarmChangeType
from gateway.delivery.models import DeliveryStatus
from gateway.delivery.store import DeliveryJobStore
from gateway.tasks.store import CollectionTaskStore, utc_now


def change() -> AlarmChange:
    return AlarmChange(
        AlarmChangeType.NEW,
        "stable-fingerprint",
        {"alarm_id": "alarm-1", "occurred_at": "2026-08-07T10:00:00Z"},
    )


def test_jobs_and_snapshot_are_persisted_and_idempotent(tmp_path):
    database = tmp_path / "tasks.sqlite3"
    task_store = CollectionTaskStore(database)
    store = DeliveryJobStore(database)

    first = store.enqueue_changes(
        "task-1",
        "mock_platform",
        [change()],
        [{"id": change().event_id}],
        {"stable-fingerprint": change().alarm},
        max_attempts=4,
    )
    duplicate = store.enqueue_changes(
        "task-2",
        "mock_platform",
        [change()],
        [{"id": change().event_id}],
        {"stable-fingerprint": change().alarm},
        max_attempts=4,
    )

    assert first[0].job_id == duplicate[0].job_id
    assert len(store.list()) == 1
    assert set(task_store.get_alarm_snapshot("mock_platform")) == {"stable-fingerprint"}


def test_interrupted_delivery_is_recovered_after_restart(tmp_path):
    store = DeliveryJobStore(tmp_path / "tasks.sqlite3")
    job = store.enqueue_changes(
        "task-1",
        "mock_platform",
        [change()],
        [{"id": change().event_id}],
        {},
        max_attempts=4,
    )[0]
    claimed = store.claim_due()

    assert claimed[0].status == DeliveryStatus.DELIVERING
    assert store.recover_interrupted_jobs() == 1
    recovered = store.get(job.job_id)
    assert recovered.status == DeliveryStatus.RETRY_WAIT
    assert recovered.last_error_code == "GATEWAY_RESTARTED"


def test_exhausted_job_enters_dead_letter_and_manual_retry_resets_it(tmp_path):
    store = DeliveryJobStore(tmp_path / "tasks.sqlite3")
    job = store.enqueue_changes(
        "task-1",
        "mock_platform",
        [change()],
        [{"id": change().event_id}],
        {},
        max_attempts=1,
    )[0]
    claimed = store.claim_due()[0]
    failed = store.mark_failed(
        claimed.job_id,
        next_attempt_at=utc_now() + timedelta(seconds=10),
        error_code="HTTPSTATUSERROR",
        error_message="KuberPilot callback request failed",
    )

    assert failed.status == DeliveryStatus.DEAD_LETTER
    retried = store.retry_dead_letter(job.job_id)
    assert retried.status == DeliveryStatus.PENDING
    assert retried.attempt_count == 0


def test_later_change_for_same_alarm_waits_behind_dead_letter(tmp_path):
    store = DeliveryJobStore(tmp_path / "tasks.sqlite3")
    first_change = change()
    first = store.enqueue_changes(
        "task-1",
        "mock_platform",
        [first_change],
        [{"id": first_change.event_id, "status": "firing"}],
        {first_change.fingerprint: first_change.alarm},
        max_attempts=1,
    )[0]
    claimed = store.claim_due()[0]
    store.mark_failed(
        claimed.job_id,
        next_attempt_at=utc_now(),
        error_code="HTTPSTATUSERROR",
        error_message="KuberPilot callback request failed",
    )
    recovered_change = AlarmChange(
        AlarmChangeType.RECOVERED,
        first_change.fingerprint,
        first_change.alarm,
    )
    recovered = store.enqueue_changes(
        "task-2",
        "mock_platform",
        [recovered_change],
        [{"id": recovered_change.event_id, "status": "resolved"}],
        {},
        max_attempts=4,
    )[0]

    assert store.claim_due() == []
    store.retry_dead_letter(first.job_id)
    first_retry = store.claim_due()
    assert [job.job_id for job in first_retry] == [first.job_id]
    store.mark_succeeded(first.job_id)
    next_claim = store.claim_due()
    assert [job.job_id for job in next_claim] == [recovered.job_id]
