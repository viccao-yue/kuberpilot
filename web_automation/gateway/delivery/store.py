"""SQLite-backed outbox for reliable KuberPilot callback delivery."""

from dataclasses import replace
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
from threading import Lock
from typing import Any
from uuid import uuid4

from gateway.alerts.differ import AlarmChange, AlarmChangeType
from gateway.delivery.models import DeliveryJob, DeliveryStatus
from gateway.tasks.store import utc_now


class DeliveryJobStore:
    def __init__(self, database_path: Path):
        self.database_path = database_path
        self._lock = Lock()
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS alarm_snapshots (
                    platform TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    alarm_json TEXT NOT NULL,
                    PRIMARY KEY (platform, fingerprint)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS delivery_jobs (
                    job_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    task_id TEXT NOT NULL,
                    platform TEXT NOT NULL,
                    change_type TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    next_attempt_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    delivered_at TEXT,
                    last_error_code TEXT,
                    last_error_message TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_delivery_jobs_due "
                "ON delivery_jobs(status, next_attempt_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_delivery_jobs_task "
                "ON delivery_jobs(task_id, created_at)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_delivery_jobs_platform "
                "ON delivery_jobs(platform, created_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_delivery_jobs_alarm "
                "ON delivery_jobs(platform, fingerprint)"
            )

    def enqueue_changes(
        self,
        task_id: str,
        platform: str,
        changes: list[AlarmChange],
        payloads: list[dict[str, Any]],
        current_snapshot: dict[str, dict[str, Any]],
        *,
        max_attempts: int,
    ) -> list[DeliveryJob]:
        """Persist callback jobs before the caller advances its alarm snapshot."""
        now = utc_now()
        job_ids: list[str] = []
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for change, payload in zip(changes, payloads, strict=True):
                idempotency_key = self.build_idempotency_key(platform, change.event_id)
                job_id = str(uuid4())
                cursor = connection.execute(
                    """
                    INSERT OR IGNORE INTO delivery_jobs (
                        job_id, idempotency_key, task_id, platform, change_type,
                        fingerprint, payload_json, status, attempt_count,
                        max_attempts, next_attempt_at, created_at, updated_at,
                        delivered_at, last_error_code, last_error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL)
                    """,
                    (
                        job_id,
                        idempotency_key,
                        task_id,
                        platform,
                        change.change_type.value,
                        change.fingerprint,
                        json.dumps(payload, ensure_ascii=False),
                        DeliveryStatus.PENDING.value,
                        0,
                        max_attempts,
                        now.isoformat(),
                        now.isoformat(),
                        now.isoformat(),
                    ),
                )
                if cursor.rowcount:
                    job_ids.append(job_id)
                else:
                    row = connection.execute(
                        "SELECT job_id FROM delivery_jobs WHERE idempotency_key = ?",
                        (idempotency_key,),
                    ).fetchone()
                    if row is not None:
                        job_ids.append(row["job_id"])
            connection.execute(
                "DELETE FROM alarm_snapshots WHERE platform = ?",
                (platform,),
            )
            connection.executemany(
                "INSERT INTO alarm_snapshots (platform, fingerprint, alarm_json) "
                "VALUES (?, ?, ?)",
                [
                    (platform, fingerprint, json.dumps(alarm, ensure_ascii=False))
                    for fingerprint, alarm in current_snapshot.items()
                ],
            )
            connection.commit()
        return [job for job_id in job_ids if (job := self.get(job_id)) is not None]

    def assign_lifecycle_sequences(
        self,
        platform: str,
        changes: list[AlarmChange],
    ) -> list[AlarmChange]:
        """Distinguish repeated alarm lifecycles without breaking transition deduplication."""
        assigned: list[AlarmChange] = []
        with self._connect() as connection:
            for change in changes:
                new_count = connection.execute(
                    """
                    SELECT COUNT(*) AS count FROM delivery_jobs
                    WHERE platform = ? AND fingerprint = ? AND change_type = ?
                    """,
                    (platform, change.fingerprint, AlarmChangeType.NEW.value),
                ).fetchone()["count"]
                latest = connection.execute(
                    """
                    SELECT change_type FROM delivery_jobs
                    WHERE platform = ? AND fingerprint = ?
                    ORDER BY rowid DESC LIMIT 1
                    """,
                    (platform, change.fingerprint),
                ).fetchone()
                latest_change_type = latest["change_type"] if latest else None
                if change.change_type == AlarmChangeType.NEW:
                    sequence = (
                        max(1, new_count)
                        if latest_change_type == AlarmChangeType.NEW.value
                        else new_count + 1
                    )
                else:
                    sequence = max(1, new_count)
                assigned.append(replace(change, lifecycle_sequence=sequence))
        return assigned

    def recover_interrupted_jobs(self) -> int:
        now = utc_now().isoformat()
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE delivery_jobs
                SET status = ?, next_attempt_at = ?, updated_at = ?,
                    last_error_code = ?, last_error_message = ?
                WHERE status = ?
                """,
                (
                    DeliveryStatus.RETRY_WAIT.value,
                    now,
                    now,
                    "GATEWAY_RESTARTED",
                    "Delivery was interrupted and will be retried",
                    DeliveryStatus.DELIVERING.value,
                ),
            )
        return cursor.rowcount

    def recover_interrupted_job(
        self,
        job_id: str,
        *,
        error_code: str,
        error_message: str,
    ) -> bool:
        """Release one claimed job after an unexpected callback or state-write error."""
        now = utc_now().isoformat()
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE delivery_jobs
                SET status = CASE
                        WHEN attempt_count >= max_attempts THEN ?
                        ELSE ?
                    END,
                    next_attempt_at = ?, updated_at = ?,
                    last_error_code = ?, last_error_message = ?
                WHERE job_id = ? AND status = ?
                """,
                (
                    DeliveryStatus.DEAD_LETTER.value,
                    DeliveryStatus.RETRY_WAIT.value,
                    now,
                    now,
                    error_code,
                    error_message,
                    job_id,
                    DeliveryStatus.DELIVERING.value,
                ),
            )
        return bool(cursor.rowcount)

    def claim_due(self, *, limit: int = 20) -> list[DeliveryJob]:
        now = utc_now().isoformat()
        claimed_ids: list[str] = []
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT candidate.job_id FROM delivery_jobs AS candidate
                WHERE candidate.status IN (?, ?)
                  AND candidate.next_attempt_at <= ?
                  AND NOT EXISTS (
                      SELECT 1 FROM delivery_jobs AS earlier
                      WHERE earlier.platform = candidate.platform
                        AND earlier.fingerprint = candidate.fingerprint
                        AND earlier.rowid < candidate.rowid
                        AND earlier.status != ?
                  )
                ORDER BY candidate.next_attempt_at, candidate.created_at
                LIMIT ?
                """,
                (
                    DeliveryStatus.PENDING.value,
                    DeliveryStatus.RETRY_WAIT.value,
                    now,
                    DeliveryStatus.SUCCEEDED.value,
                    limit,
                ),
            ).fetchall()
            claimed_ids = [row["job_id"] for row in rows]
            if claimed_ids:
                placeholders = ",".join("?" for _ in claimed_ids)
                connection.execute(
                    f"""
                    UPDATE delivery_jobs
                    SET status = ?, attempt_count = attempt_count + 1, updated_at = ?
                    WHERE job_id IN ({placeholders})
                    """,
                    (DeliveryStatus.DELIVERING.value, now, *claimed_ids),
                )
            connection.commit()
        return [job for job_id in claimed_ids if (job := self.get(job_id)) is not None]

    def mark_succeeded(self, job_id: str) -> None:
        now = utc_now().isoformat()
        self._update(
            job_id,
            status=DeliveryStatus.SUCCEEDED.value,
            delivered_at=now,
            updated_at=now,
            last_error_code=None,
            last_error_message=None,
        )

    def mark_failed(
        self,
        job_id: str,
        *,
        next_attempt_at: datetime | None,
        error_code: str,
        error_message: str,
    ) -> DeliveryJob:
        job = self.get(job_id)
        if job is None:
            raise KeyError(job_id)
        exhausted = job.attempt_count >= job.max_attempts
        self._update(
            job_id,
            status=(
                DeliveryStatus.DEAD_LETTER.value
                if exhausted
                else DeliveryStatus.RETRY_WAIT.value
            ),
            next_attempt_at=(next_attempt_at or utc_now()).isoformat(),
            updated_at=utc_now().isoformat(),
            last_error_code=error_code,
            last_error_message=error_message,
        )
        updated = self.get(job_id)
        if updated is None:
            raise KeyError(job_id)
        return updated

    def retry_dead_letter(self, job_id: str) -> DeliveryJob | None:
        now = utc_now().isoformat()
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE delivery_jobs
                SET status = ?, attempt_count = 0, next_attempt_at = ?,
                    updated_at = ?, delivered_at = NULL,
                    last_error_code = NULL, last_error_message = NULL
                WHERE job_id = ? AND status = ?
                """,
                (
                    DeliveryStatus.PENDING.value,
                    now,
                    now,
                    job_id,
                    DeliveryStatus.DEAD_LETTER.value,
                ),
            )
        return self.get(job_id) if cursor.rowcount else None

    def get(self, job_id: str) -> DeliveryJob | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM delivery_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list(
        self,
        *,
        platform: str | None = None,
        status: DeliveryStatus | None = None,
        limit: int = 50,
    ) -> list[DeliveryJob]:
        clauses: list[str] = []
        values: list[Any] = []
        if platform:
            clauses.append("platform = ?")
            values.append(platform)
        if status:
            clauses.append("status = ?")
            values.append(status.value)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        values.append(limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM delivery_jobs{where} ORDER BY created_at DESC LIMIT ?",
                values,
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def status_counts(self) -> dict[str, int]:
        counts = {status.value: 0 for status in DeliveryStatus}
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM delivery_jobs GROUP BY status"
            ).fetchall()
        for row in rows:
            counts[row["status"]] = row["count"]
        return counts

    def _update(self, job_id: str, **fields: Any) -> None:
        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = [*fields.values(), job_id]
        with self._lock, self._connect() as connection:
            connection.execute(
                f"UPDATE delivery_jobs SET {assignments} WHERE job_id = ?",
                values,
            )

    @staticmethod
    def build_idempotency_key(platform: str, event_id: str) -> str:
        value = f"{platform}:alert_callback:{event_id}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _from_row(row: sqlite3.Row) -> DeliveryJob:
        return DeliveryJob(
            job_id=row["job_id"],
            idempotency_key=row["idempotency_key"],
            task_id=row["task_id"],
            platform=row["platform"],
            change_type=row["change_type"],
            fingerprint=row["fingerprint"],
            payload=json.loads(row["payload_json"]),
            status=DeliveryStatus(row["status"]),
            attempt_count=row["attempt_count"],
            max_attempts=row["max_attempts"],
            next_attempt_at=datetime.fromisoformat(row["next_attempt_at"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            delivered_at=(
                datetime.fromisoformat(row["delivered_at"]) if row["delivered_at"] else None
            ),
            last_error_code=row["last_error_code"],
            last_error_message=row["last_error_message"],
        )
