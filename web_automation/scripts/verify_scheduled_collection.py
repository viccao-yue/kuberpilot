"""Observe scheduled collections for a bounded local soak-test window."""

import argparse
import json
import time
from datetime import datetime, timezone

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gateway-url", default="http://127.0.0.1:8010")
    parser.add_argument("--duration-seconds", type=int, default=1800)
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--progress-seconds", type=int, default=300)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = time.monotonic()
    started_wall_clock = datetime.now(timezone.utc)
    deadline = started_at + args.duration_seconds
    next_progress = started_at + args.progress_seconds
    observed: dict[str, set[str]] = {
        "mock_platform": set(),
        "legacy_ops_platform": set(),
    }
    failed_tasks: list[str] = []

    with httpx.Client(base_url=args.gateway_url, timeout=10, trust_env=False) as client:
        health = client.get("/healthz")
        health.raise_for_status()
        while time.monotonic() < deadline:
            response = client.get(
                "/api/v1/collection-tasks",
                params={"limit": 200},
            )
            response.raise_for_status()
            for task in response.json():
                if task["trigger"] != "scheduled" or task["platform"] not in observed:
                    continue
                if datetime.fromisoformat(task["created_at"]) < started_wall_clock:
                    continue
                if task["status"] == "succeeded":
                    observed[task["platform"]].add(task["task_id"])
                elif task["status"] == "failed":
                    failed_tasks.append(task["task_id"])
            now = time.monotonic()
            if now >= next_progress:
                counts = {platform: len(task_ids) for platform, task_ids in observed.items()}
                print(f"progress elapsed={round(now - started_at)}s counts={counts}", flush=True)
                next_progress = now + args.progress_seconds
            time.sleep(min(args.poll_seconds, max(0, deadline - time.monotonic())))

    elapsed_seconds = round(time.monotonic() - started_at, 1)
    summary = {
        "gateway_health": "ok",
        "requested_duration_seconds": args.duration_seconds,
        "elapsed_seconds": elapsed_seconds,
        "scheduled_success_counts": {
            platform: len(task_ids) for platform, task_ids in observed.items()
        },
        "failed_task_ids": sorted(set(failed_tasks)),
    }
    summary["ok"] = (
        all(summary["scheduled_success_counts"].values())
        and not summary["failed_task_ids"]
        and elapsed_seconds >= args.duration_seconds
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
