from concurrent.futures import ThreadPoolExecutor

from gateway.tasks.models import CollectionTask, TaskStatus, TaskTrigger
from gateway.tasks.store import CollectionTaskStore, utc_now


def make_task(task_id: str = "task-1", platform: str = "mock_platform") -> CollectionTask:
    return CollectionTask(
        task_id=task_id,
        platform=platform,
        trigger=TaskTrigger.MANUAL,
        status=TaskStatus.QUEUED,
        severity="all",
        limit=20,
        created_at=utc_now(),
    )


def test_task_history_persists_across_store_instances(tmp_path):
    database = tmp_path / "tasks.sqlite3"
    store = CollectionTaskStore(database)
    accepted, _ = store.create_if_platform_idle(make_task())
    assert accepted is True

    store.mark_running("task-1", utc_now())
    store.mark_succeeded("task-1", utc_now(), 18, {"ok": True, "count": 3})

    reopened = CollectionTaskStore(database)
    task = reopened.get("task-1")
    assert task is not None
    assert task.status == TaskStatus.SUCCEEDED
    assert task.result == {"ok": True, "count": 3}
    assert task.duration_ms == 18


def test_same_platform_cannot_create_overlapping_active_tasks(tmp_path):
    store = CollectionTaskStore(tmp_path / "tasks.sqlite3")
    accepted, first = store.create_if_platform_idle(make_task())
    duplicate_accepted, active = store.create_if_platform_idle(make_task("task-2"))

    assert accepted is True
    assert duplicate_accepted is False
    assert active.task_id == first.task_id

    store.mark_failed("task-1", utc_now(), 5, "TEST_ERROR", "failed")
    accepted_after_finish, second = store.create_if_platform_idle(make_task("task-2"))
    assert accepted_after_finish is True
    assert second.task_id == "task-2"


def test_task_list_filters_platform_and_status(tmp_path):
    store = CollectionTaskStore(tmp_path / "tasks.sqlite3")
    store.create_if_platform_idle(make_task("task-1", "mock_platform"))
    store.mark_succeeded("task-1", utc_now(), 5, {"ok": True})
    store.create_if_platform_idle(make_task("task-2", "legacy_ops_platform"))

    succeeded = store.list(status=TaskStatus.SUCCEEDED)
    legacy = store.list(platform="legacy_ops_platform")

    assert [task.task_id for task in succeeded] == ["task-1"]
    assert [task.task_id for task in legacy] == ["task-2"]


def test_interrupted_tasks_are_failed_and_no_longer_block_platform(tmp_path):
    store = CollectionTaskStore(tmp_path / "tasks.sqlite3")
    store.create_if_platform_idle(make_task())

    recovered = store.fail_interrupted_tasks()
    interrupted = store.get("task-1")
    accepted, _ = store.create_if_platform_idle(make_task("task-2"))

    assert recovered == 1
    assert interrupted.status == TaskStatus.FAILED
    assert interrupted.error_code == "GATEWAY_RESTARTED"
    assert accepted is True


def test_separate_store_instances_atomically_prevent_overlap(tmp_path):
    database = tmp_path / "tasks.sqlite3"
    first_store = CollectionTaskStore(database)
    second_store = CollectionTaskStore(database)

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_result = executor.submit(
            first_store.create_if_platform_idle,
            make_task("task-1"),
        )
        second_result = executor.submit(
            second_store.create_if_platform_idle,
            make_task("task-2"),
        )
        accepted = [first_result.result()[0], second_result.result()[0]]

    assert sorted(accepted) == [False, True]
    assert len(first_store.list(platform="mock_platform")) == 1


def test_alarm_snapshot_replacement_is_platform_scoped_and_persistent(tmp_path):
    database = tmp_path / "tasks.sqlite3"
    store = CollectionTaskStore(database)
    store.replace_alarm_snapshot(
        "mock_platform",
        {"fp-1": {"alarm_id": "a-1", "title": "CPU high"}},
    )
    store.replace_alarm_snapshot(
        "legacy_ops_platform",
        {"fp-2": {"alarm_id": "a-2", "title": "DB high"}},
    )
    store.replace_alarm_snapshot(
        "mock_platform",
        {"fp-3": {"alarm_id": "a-3", "title": "Memory low"}},
    )

    reopened = CollectionTaskStore(database)

    assert set(reopened.get_alarm_snapshot("mock_platform")) == {"fp-3"}
    assert set(reopened.get_alarm_snapshot("legacy_ops_platform")) == {"fp-2"}
