"""Run a bounded HTTP/SQLite fault-injection soak test for durable delivery."""

import argparse
import asyncio
import json
import sys
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

WEB_ROOT = Path(__file__).resolve().parents[1]
if str(WEB_ROOT) not in sys.path:
    sys.path.insert(0, str(WEB_ROOT))

from gateway.alerts.callback import KuberPilotCallbackClient
from gateway.alerts.differ import AlarmChange, AlarmChangeType
from gateway.delivery.models import DeliveryStatus
from gateway.delivery.store import DeliveryJobStore
from gateway.delivery.worker import DeliveryWorker
from gateway.tasks.store import CollectionTaskStore


class CallbackController:
    def __init__(self):
        self.fail_next_ids: set[str] = set()
        self.always_fail = False
        self.requests: Counter[str] = Counter()
        self.successes: Counter[str] = Counter()
        self._lock = threading.Lock()

    def handle(self, event_id: str) -> int:
        with self._lock:
            self.requests[event_id] += 1
            if self.always_fail or event_id in self.fail_next_ids:
                self.fail_next_ids.discard(event_id)
                return 503
            self.successes[event_id] += 1
            return 202


def build_handler(controller: CallbackController):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - BaseHTTPRequestHandler API
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length) or b"{}")
            status_code = controller.handle(str(payload.get("id") or "missing"))
            body = json.dumps({"success": status_code == 202}).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: Any) -> None:
            return

    return Handler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-seconds", type=int, default=1800)
    parser.add_argument("--progress-seconds", type=int, default=300)
    parser.add_argument("--event-interval-seconds", type=float, default=10)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path(".runtime/verification/reliable-delivery.sqlite3"),
    )
    return parser.parse_args()


def alarm_change(index: int) -> AlarmChange:
    event_time = datetime.now(timezone.utc).isoformat()
    return AlarmChange(
        AlarmChangeType.NEW,
        f"fault-injection-fp-{index}",
        {
            "alarm_id": f"fault-injection-alarm-{index}",
            "severity": "warning",
            "resource_id": "verification-host",
            "resource_type": "host",
            "resource_name": "verification-host",
            "title": f"Reliable delivery verification {index}",
            "description": "Local fault-injection verification event",
            "occurred_at": event_time,
        },
    )


def enqueue(
    store: DeliveryJobStore,
    client: KuberPilotCallbackClient,
    index: int,
    *,
    max_attempts: int = 4,
):
    change = alarm_change(index)
    payload = client.build_payload(f"verification-task-{index}", "mock_platform", change)
    job = store.enqueue_changes(
        f"verification-task-{index}",
        "mock_platform",
        [change],
        [payload],
        {change.fingerprint: change.alarm},
        max_attempts=max_attempts,
    )[0]
    return job, payload["id"]


def build_worker(store, client) -> DeliveryWorker:
    return DeliveryWorker(
        store,
        client,
        retry_delays_seconds=(1, 2, 3),
        poll_interval_seconds=0.2,
        batch_size=20,
    )


async def wait_for_status(
    store: DeliveryJobStore,
    worker: DeliveryWorker,
    job_id: str,
    expected: DeliveryStatus,
    *,
    timeout_seconds: float = 10,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        await worker.run_once()
        job = store.get(job_id)
        if job is not None and job.status == expected:
            return
        await asyncio.sleep(0.2)
    raise RuntimeError(f"Delivery job {job_id} did not reach {expected.value}")


async def verify(args: argparse.Namespace) -> dict[str, Any]:
    database = args.database.resolve()
    if not database.is_relative_to(WEB_ROOT):
        raise ValueError("Verification database must stay inside web_automation")
    database.parent.mkdir(parents=True, exist_ok=True)
    if database.exists():
        database.unlink()
    CollectionTaskStore(database)
    store = DeliveryJobStore(database)
    controller = CallbackController()
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(controller))
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    callback_url = f"http://127.0.0.1:{server.server_port}/callback"
    client = KuberPilotCallbackClient(callback_url, "local-test-token", timeout_seconds=2)
    worker = build_worker(store, client)
    phases: dict[str, bool] = {}

    try:
        controller.always_fail = True
        retry_job, _ = enqueue(store, client, 1)
        await worker.run_once()
        phases["http_failure_persisted"] = (
            store.get(retry_job.job_id).status == DeliveryStatus.RETRY_WAIT
        )
        store = DeliveryJobStore(database)
        worker = build_worker(store, client)
        controller.always_fail = False
        await wait_for_status(store, worker, retry_job.job_id, DeliveryStatus.SUCCEEDED)
        phases["retry_survived_store_reopen"] = True

        interrupted_job, _ = enqueue(store, client, 2)
        claimed = store.claim_due(limit=20)
        phases["interrupted_job_claimed"] = any(
            job.job_id == interrupted_job.job_id for job in claimed
        )
        store = DeliveryJobStore(database)
        phases["restart_recovered_delivering"] = store.recover_interrupted_jobs() >= 1
        worker = build_worker(store, client)
        await wait_for_status(
            store,
            worker,
            interrupted_job.job_id,
            DeliveryStatus.SUCCEEDED,
        )

        controller.always_fail = True
        dead_job, _ = enqueue(store, client, 3, max_attempts=1)
        await wait_for_status(store, worker, dead_job.job_id, DeliveryStatus.DEAD_LETTER)
        phases["exhausted_to_dead_letter"] = True
        controller.always_fail = False
        retried = store.retry_dead_letter(dead_job.job_id)
        phases["manual_retry_accepted"] = retried is not None
        await wait_for_status(store, worker, dead_job.job_id, DeliveryStatus.SUCCEEDED)

        duplicate_change = AlarmChange(
            AlarmChangeType.NEW,
            dead_job.fingerprint,
            {"occurred_at": dead_job.payload.get("starts_at")},
        )
        duplicate = store.enqueue_changes(
            "verification-task-duplicate",
            "mock_platform",
            [duplicate_change],
            [dead_job.payload],
            {duplicate_change.fingerprint: duplicate_change.alarm},
            max_attempts=1,
        )[0]
        phases["idempotency_reused_job"] = duplicate.job_id == dead_job.job_id

        started = time.monotonic()
        deadline = started + args.duration_seconds
        next_event = started
        next_progress = started + args.progress_seconds
        event_index = 100
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now >= next_event:
                job, event_id = enqueue(store, client, event_index)
                if event_index % 5 == 0:
                    controller.fail_next_ids.add(event_id)
                event_index += 1
                next_event = now + args.event_interval_seconds
            await worker.run_once()
            if now >= next_progress:
                counts = Counter(job.status.value for job in store.list(limit=200))
                print(
                    f"progress elapsed={round(now - started)}s statuses={dict(counts)}",
                    flush=True,
                )
                store = DeliveryJobStore(database)
                store.recover_interrupted_jobs()
                worker = build_worker(store, client)
                next_progress = now + args.progress_seconds
            await asyncio.sleep(0.2)

        drain_deadline = time.monotonic() + 10
        while time.monotonic() < drain_deadline:
            await worker.run_once()
            unfinished = store.list(status=DeliveryStatus.PENDING, limit=200)
            unfinished += store.list(status=DeliveryStatus.RETRY_WAIT, limit=200)
            if not unfinished:
                break
            await asyncio.sleep(0.2)

        jobs = store.list(limit=200)
        statuses = Counter(job.status.value for job in jobs)
        elapsed = round(time.monotonic() - started, 1)
        summary = {
            "ok": all(phases.values())
            and statuses[DeliveryStatus.DEAD_LETTER.value] == 0
            and statuses[DeliveryStatus.PENDING.value] == 0
            and statuses[DeliveryStatus.RETRY_WAIT.value] == 0
            and elapsed >= args.duration_seconds,
            "requested_duration_seconds": args.duration_seconds,
            "elapsed_seconds": elapsed,
            "phases": phases,
            "delivery_status_counts": dict(statuses),
            "callback_request_count": sum(controller.requests.values()),
            "callback_success_count": sum(controller.successes.values()),
            "database": str(database),
        }
        return summary
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)


def main() -> int:
    args = parse_args()
    summary = asyncio.run(verify(args))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
