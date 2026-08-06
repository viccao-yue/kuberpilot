"""Task-center request and response models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TaskTrigger(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"


class CollectionTaskCreate(BaseModel):
    platform: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    severity: str = Field(default="all", pattern=r"^(all|critical|warning|info)$")
    limit: int = Field(default=20, ge=1, le=50)


class CollectionTask(BaseModel):
    task_id: str
    platform: str
    action: str = "list_alarms"
    trigger: TaskTrigger
    status: TaskStatus
    severity: str
    limit: int
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    result: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None


class CollectionTaskAccepted(BaseModel):
    accepted: bool
    task: CollectionTask
    message: str
