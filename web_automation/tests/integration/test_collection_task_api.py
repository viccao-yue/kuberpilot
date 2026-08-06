from unittest.mock import Mock

import httpx

from gateway.app import app
from gateway.dependencies import get_task_manager, get_task_store
from gateway.tasks.models import CollectionTask, TaskStatus, TaskTrigger
from gateway.tasks.store import CollectionTaskStore, utc_now
from platforms.loader import PlatformNotFoundError


async def request(method: str, path: str, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def queued_task() -> CollectionTask:
    return CollectionTask(
        task_id="accepted-task",
        platform="mock_platform",
        trigger=TaskTrigger.MANUAL,
        status=TaskStatus.QUEUED,
        severity="all",
        limit=20,
        created_at=utc_now(),
    )


async def test_create_and_query_collection_task(tmp_path):
    store = CollectionTaskStore(tmp_path / "tasks.sqlite3")
    task = queued_task()
    store.create_if_platform_idle(task)
    manager = Mock()
    manager.submit.return_value = (True, task)
    app.dependency_overrides[get_task_manager] = lambda: manager
    app.dependency_overrides[get_task_store] = lambda: store
    try:
        created = await request(
            "POST",
            "/api/v1/collection-tasks",
            json={"platform": "mock_platform", "severity": "all", "limit": 20},
        )
        listed = await request("GET", "/api/v1/collection-tasks?status=queued")
        detail = await request("GET", "/api/v1/collection-tasks/accepted-task")
    finally:
        app.dependency_overrides.clear()

    assert created.status_code == 202
    assert created.json()["task"]["task_id"] == "accepted-task"
    assert [item["task_id"] for item in listed.json()] == ["accepted-task"]
    assert detail.json()["status"] == "queued"


async def test_create_rejects_overlap_and_invalid_input(tmp_path):
    store = CollectionTaskStore(tmp_path / "tasks.sqlite3")
    manager = Mock()
    manager.submit.return_value = (False, queued_task())
    app.dependency_overrides[get_task_manager] = lambda: manager
    app.dependency_overrides[get_task_store] = lambda: store
    try:
        overlap = await request(
            "POST",
            "/api/v1/collection-tasks",
            json={"platform": "mock_platform"},
        )
        invalid = await request(
            "POST",
            "/api/v1/collection-tasks",
            json={"platform": "mock_platform", "limit": 500},
        )
        missing = await request("GET", "/api/v1/collection-tasks/not-found")
    finally:
        app.dependency_overrides.clear()

    assert overlap.status_code == 409
    assert overlap.json()["detail"]["active_task_id"] == "accepted-task"
    assert invalid.status_code == 422
    assert missing.status_code == 404


async def test_create_rejects_unregistered_platform_before_starting_task(tmp_path):
    store = CollectionTaskStore(tmp_path / "tasks.sqlite3")
    manager = Mock()
    manager.submit.side_effect = PlatformNotFoundError("unknown_platform")
    app.dependency_overrides[get_task_manager] = lambda: manager
    app.dependency_overrides[get_task_store] = lambda: store
    try:
        response = await request(
            "POST",
            "/api/v1/collection-tasks",
            json={"platform": "unknown_platform"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert store.list() == []
