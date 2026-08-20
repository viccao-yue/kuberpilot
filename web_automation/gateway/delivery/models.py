"""Models exposed by the durable delivery task API."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel


class DeliveryStatus(str, Enum):
    PENDING = "pending"
    DELIVERING = "delivering"
    RETRY_WAIT = "retry_wait"
    SUCCEEDED = "succeeded"
    DEAD_LETTER = "dead_letter"


class DeliveryJob(BaseModel):
    job_id: str
    idempotency_key: str
    task_id: str
    platform: str
    change_type: str
    fingerprint: str
    payload: dict[str, Any]
    status: DeliveryStatus
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime
    created_at: datetime
    updated_at: datetime
    delivered_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None


class DeliveryRetryAccepted(BaseModel):
    accepted: bool
    job: DeliveryJob
    message: str
