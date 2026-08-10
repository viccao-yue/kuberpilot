"""Background worker that resumes durable callback jobs after Gateway restarts."""

import asyncio
from datetime import timedelta

from gateway.alerts.callback import CallbackDeliveryError, KuberPilotCallbackClient
from gateway.delivery.store import DeliveryJobStore
from gateway.tasks.store import utc_now


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

    @property
    def is_running(self) -> bool:
        return self._task is not None and not self._task.done() and not self._stopping

    def start(self) -> None:
        if self._task is None or self._task.done():
            self.store.recover_interrupted_jobs()
            self._stopping = False
            self._task = asyncio.create_task(self._run())

    async def shutdown(self) -> None:
        self._stopping = True
        self._wake_event.set()
        if self._task is not None:
            await self._task

    def wake(self) -> None:
        self._wake_event.set()

    async def run_once(self) -> int:
        jobs = self.store.claim_due(limit=self.batch_size)
        for job in jobs:
            try:
                await self.callback_client.deliver_payload(job.payload)
            except CallbackDeliveryError as exc:
                retry_index = max(0, job.attempt_count - 1)
                delay = (
                    self.retry_delays_seconds[retry_index]
                    if retry_index < len(self.retry_delays_seconds)
                    else 0
                )
                self.store.mark_failed(
                    job.job_id,
                    next_attempt_at=utc_now() + timedelta(seconds=delay),
                    error_code=exc.error_code,
                    error_message=exc.public_message,
                )
            else:
                self.store.mark_succeeded(job.job_id)
        return len(jobs)

    async def _run(self) -> None:
        while not self._stopping:
            processed = await self.run_once()
            if processed:
                continue
            self._wake_event.clear()
            try:
                await asyncio.wait_for(
                    self._wake_event.wait(),
                    timeout=self.poll_interval_seconds,
                )
            except TimeoutError:
                pass
