"""Operator-facing APIs for callback delivery jobs and dead letters."""

from fastapi import APIRouter, Depends, HTTPException, Query, status

from gateway.delivery.models import DeliveryJob, DeliveryRetryAccepted, DeliveryStatus
from gateway.delivery.store import DeliveryJobStore
from gateway.delivery.worker import DeliveryWorker
from gateway.dependencies import get_delivery_store, get_delivery_worker


router = APIRouter(prefix="/api/v1/delivery-jobs", tags=["delivery-jobs"])


@router.get("", response_model=list[DeliveryJob])
async def list_delivery_jobs(
    platform: str | None = None,
    delivery_status: DeliveryStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    store: DeliveryJobStore = Depends(get_delivery_store),
) -> list[DeliveryJob]:
    return store.list(platform=platform, status=delivery_status, limit=limit)


@router.get("/{job_id}", response_model=DeliveryJob)
async def get_delivery_job(
    job_id: str,
    store: DeliveryJobStore = Depends(get_delivery_store),
) -> DeliveryJob:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Delivery job not found")
    return job


@router.post(
    "/{job_id}/retry",
    response_model=DeliveryRetryAccepted,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_delivery_job(
    job_id: str,
    store: DeliveryJobStore = Depends(get_delivery_store),
    worker: DeliveryWorker = Depends(get_delivery_worker),
) -> DeliveryRetryAccepted:
    existing = store.get(job_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Delivery job not found")
    if not worker.is_running:
        raise HTTPException(
            status_code=503,
            detail="Callback delivery worker is not running",
        )
    retried = store.retry_dead_letter(job_id)
    if retried is None:
        raise HTTPException(
            status_code=409,
            detail="Only dead-letter delivery jobs can be retried manually",
        )
    worker.wake()
    return DeliveryRetryAccepted(
        accepted=True,
        job=retried,
        message="Dead-letter delivery job queued for retry",
    )
