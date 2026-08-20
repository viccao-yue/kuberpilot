"""Background worker that resumes durable callback jobs after Gateway restarts."""

import asyncio
import logging
from datetime import timedelta
from typing import Any

from gateway.alerts.callback import CallbackDeliveryError, KuberPilotCallbackClient
from gateway.delivery.models import DeliveryJob
from gateway.delivery.store import DeliveryJobStore
from gateway.tasks.store import utc_now


logger = logging.getLogger(__name__)


class DeliveryWorker:
    def __init__(
        self,
        store: DeliveryJobStore,
        callback_client: KuberPilotCallbackClient,
        *,
        retry_delays_seconds: tuple[float, ...],
        poll_interval_seconds: float,
        batch_size: int,
    ):
        self.store = store
        self.callback_client = callback_client
        self.retry_delays_seconds = retry_delays_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.batch_size = batch_size
        self._task: asyncio.Task | None = None
        self._wake_event = asyncio.Event()
        self._stopping = False
        self._last_error: dict[str, str] | None = None
        self._consecutive_loop_errors = 0
        self._recovery_pending = False

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done() and not self._stopping

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stopping = False
            self._recovery_pending = not self._recover_interrupted_jobs(
                "startup_recovery"
            )
            self._task = asyncio.create_task(self._run())

    async def shutdown(self) -> None:
        self._stopping = True
        self._wake_event.set()
        if self._task is not None:
            try:
                await self._task
            except Exception as exc:
                self._record_error("shutdown", exc)
                logger.exception(
                    "Delivery Worker task had already failed during shutdown",
                    extra={"error_type": type(exc).__name__},
                )
            finally:
                self._task = None

    def wake(self) -> None:
        self._wake_event.set()

    async def run_once(self) -> int:
        jobs = self.store.claim_due(limit=self.batch_size)
        for job in jobs:
            try:
                await self.callback_client.deliver_payload(job.payload)
            except CallbackDeliveryError as exc:
                self._mark_failed(
                    job,
                    error_code=exc.error_code,
                    error_message=exc.public_message,
                )
            except Exception as exc:
                self._record_error("callback", exc)
                logger.exception(
                    "Unexpected callback delivery error",
                    extra={"job_id": job.job_id, "error_type": type(exc).__name__},
                )
                self._mark_failed(
                    job,
                    error_code="DELIVERY_UNEXPECTED_ERROR",
                    error_message="Unexpected callback delivery error",
                )
            else:
                try:
                    self.store.mark_succeeded(job.job_id)
                except Exception as exc:
                    self._record_error("mark_succeeded", exc)
                    logger.exception(
                        "Failed to persist callback delivery success",
                        extra={"job_id": job.job_id, "error_type": type(exc).__name__},
                    )
                    self._recovery_pending = not self._recover_job(
                        job.job_id,
                        error_code="DELIVERY_STATE_UPDATE_FAILED",
                        error_message="Callback result could not be persisted",
                    )
        return len(jobs)

    async def _run(self) -> None:
        while not self._stopping:
            if self._recovery_pending:
                if not self._recover_interrupted_jobs("deferred_recovery"):
                    self._consecutive_loop_errors += 1
                    await self._wait(self._error_backoff_seconds())
                    continue
                self._recovery_pending = False
            try:
                processed = await self.run_once()
            except Exception as exc:
                self._consecutive_loop_errors += 1
                self._record_error("worker_loop", exc)
                logger.exception(
                    "Delivery Worker loop recovered from an unexpected error",
                    extra={"error_type": type(exc).__name__},
                )
                self._recovery_pending = not self._recover_interrupted_jobs(
                    "worker_loop_recovery"
                )
                await self._wait(self._error_backoff_seconds())
                continue
            self._consecutive_loop_errors = 0
            if processed:
                continue
            await self._wait(self.poll_interval_seconds)

    def health(self) -> dict[str, Any]:
        queue_error_type: str | None = None
        try:
            counts = self.store.status_counts()
        except Exception as exc:
            self._record_error("health_queue_status", exc)
            queue_error_type = type(exc).__name__
            counts = {}
        backlog = sum(
            counts.get(status, 0)
            for status in ("pending", "delivering", "retry_wait")
        )
        return {
            "is_running": self.is_running,
            "backlog": backlog,
            "dead_letter": counts.get("dead_letter", 0),
            "queue_error_type": queue_error_type,
            "last_error": self._last_error,
        }

    def _mark_failed(
        self,
        job: DeliveryJob,
        *,
        error_code: str,
        error_message: str,
    ) -> None:
        retry_index = max(0, job.attempt_count - 1)
        delay = (
            self.retry_delays_seconds[retry_index]
            if retry_index < len(self.retry_delays_seconds)
            else 0
        )
        try:
            self.store.mark_failed(
                job.job_id,
                next_attempt_at=utc_now() + timedelta(seconds=delay),
                error_code=error_code,
                error_message=error_message,
            )
        except Exception as exc:
            self._record_error("mark_failed", exc)
            logger.exception(
                "Failed to persist callback delivery failure",
                extra={"job_id": job.job_id, "error_type": type(exc).__name__},
            )
            self._recovery_pending = not self._recover_job(
                job.job_id,
                error_code="DELIVERY_STATE_UPDATE_FAILED",
                error_message="Callback failure could not be persisted",
            )

    def _recover_job(
        self,
        job_id: str,
        *,
        error_code: str,
        error_message: str,
    ) -> bool:
        try:
            return self.store.recover_interrupted_job(
                job_id,
                error_code=error_code,
                error_message=error_message,
            )
        except Exception as exc:
            self._record_error("job_recovery", exc)
            logger.exception(
                "Failed to release an interrupted delivery job",
                extra={"job_id": job_id, "error_type": type(exc).__name__},
            )
            return False

    def _recover_interrupted_jobs(self, stage: str) -> bool:
        try:
            self.store.recover_interrupted_jobs()
            return True
        except Exception as exc:
            self._record_error(stage, exc)
            logger.exception(
                "Failed to recover interrupted delivery jobs",
                extra={"error_type": type(exc).__name__},
            )
            return False

    def _record_error(self, stage: str, exc: Exception) -> None:
        self._last_error = {
            "stage": stage,
            "type": type(exc).__name__,
            "at": utc_now().isoformat(),
        }

    def _error_backoff_seconds(self) -> float:
        multiplier = 2 ** min(max(0, self._consecutive_loop_errors - 1), 5)
        return min(max(self.poll_interval_seconds * multiplier, 0.01), 30.0)

    async def _wait(self, timeout: float) -> None:
        if self._stopping:
            return
        self._wake_event.clear()
        try:
            await asyncio.wait_for(self._wake_event.wait(), timeout=timeout)
        except TimeoutError:
            pass
