"""Operator-facing collection task center API."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from gateway.dependencies import get_task_manager, get_task_store
from gateway.tasks.manager import CollectionTaskManager
from gateway.tasks.models import (
    CollectionTask,
    CollectionTaskAccepted,
    CollectionTaskCreate,
    TaskStatus,
    TaskTrigger,
)
from gateway.tasks.store import CollectionTaskStore
from platforms.loader import PlatformNotFoundError


router = APIRouter(prefix="/api/v1/collection-tasks", tags=["collection-tasks"])


@router.post("", response_model=CollectionTaskAccepted, status_code=status.HTTP_202_ACCEPTED)
async def create_collection_task(
    payload: CollectionTaskCreate,
    manager: CollectionTaskManager = Depends(get_task_manager),
) -> CollectionTaskAccepted:
    try:
        accepted, task = manager.submit(
            payload.platform,
            trigger=TaskTrigger.MANUAL,
            severity=payload.severity,
            limit=payload.limit,
        )
    except PlatformNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Platform is not registered") from exc
    if not accepted:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "The platform already has an active collection task",
                "active_task_id": task.task_id,
            },
        )
    return CollectionTaskAccepted(
        accepted=True,
        task=task,
        message="Collection task accepted",
    )


@router.get("", response_model=list[CollectionTask])
async def list_collection_tasks(
    platform: str | None = None,
    task_status: TaskStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    store: CollectionTaskStore = Depends(get_task_store),
) -> list[CollectionTask]:
    return store.list(platform=platform, status=task_status, limit=limit)


@router.get("/{task_id}", response_model=CollectionTask)
async def get_collection_task(
    task_id: str,
    store: CollectionTaskStore = Depends(get_task_store),
) -> CollectionTask:
    task = store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Collection task not found")
    return task
