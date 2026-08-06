"""Small SQLite repository for durable local collection-task history."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from gateway.tasks.models import CollectionTask, TaskStatus, TaskTrigger


ACTIVE_STATUSES = (TaskStatus.QUEUED.value, TaskStatus.RUNNING.value)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CollectionTaskStore:
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
                CREATE TABLE IF NOT EXISTS collection_tasks (
                    task_id TEXT PRIMARY KEY,
                    platform TEXT NOT NULL,
                    action TEXT NOT NULL,
                    trigger TEXT NOT NULL,
                    status TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    result_limit INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    finished_at TEXT,
                    duration_ms INTEGER,
                    result_json TEXT,
                    error_code TEXT,
                    error_message TEXT
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_collection_tasks_created "
                "ON collection_tasks(created_at DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_collection_tasks_platform_status "
                "ON collection_tasks(platform, status)"
            )
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

    def fail_interrupted_tasks(self) -> int:
        """Release single-process locks left behind by a previous Gateway process."""
        finished_at = utc_now().isoformat()
        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE collection_tasks
                SET status = ?, finished_at = ?, error_code = ?, error_message = ?
                WHERE status IN (?, ?)
                """,
                (
                    TaskStatus.FAILED.value,
                    finished_at,
                    "GATEWAY_RESTARTED",
                    "Task was interrupted by a Gateway restart",
                    *ACTIVE_STATUSES,
                ),
            )
        return cursor.rowcount

    def create_if_platform_idle(self, task: CollectionTask) -> tuple[bool, CollectionTask]:
        """Atomically create a task or return the platform's active task."""
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            active = connection.execute(
                "SELECT * FROM collection_tasks WHERE platform = ? AND status IN (?, ?) "
                "ORDER BY created_at DESC LIMIT 1",
                (task.platform, *ACTIVE_STATUSES),
            ).fetchone()
            if active is not None:
                connection.rollback()
                return False, self._from_row(active)
            connection.execute(
                """
                INSERT INTO collection_tasks (
                    task_id, platform, action, trigger, status, severity, result_limit,
                    created_at, started_at, finished_at, duration_ms, result_json,
                    error_code, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._values(task),
            )
            connection.commit()
        return True, task

    def mark_running(self, task_id: str, started_at: datetime) -> None:
        self._update(
            task_id,
            status=TaskStatus.RUNNING.value,
            started_at=started_at.isoformat(),
        )

    def mark_succeeded(
        self,
        task_id: str,
        finished_at: datetime,
        duration_ms: int,
        result: dict[str, Any],
    ) -> None:
        self._update(
            task_id,
            status=TaskStatus.SUCCEEDED.value,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            result_json=json.dumps(result, ensure_ascii=False),
        )

    def mark_failed(
        self,
        task_id: str,
        finished_at: datetime,
        duration_ms: int,
        error_code: str,
        error_message: str,
    ) -> None:
        self._update(
            task_id,
            status=TaskStatus.FAILED.value,
            finished_at=finished_at.isoformat(),
            duration_ms=duration_ms,
            error_code=error_code,
            error_message=error_message,
        )

    def get(self, task_id: str) -> CollectionTask | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM collection_tasks WHERE task_id = ?",
                (task_id,),
            ).fetchone()
        return self._from_row(row) if row else None

    def list(
        self,
        *,
        platform: str | None = None,
        status: TaskStatus | None = None,
        limit: int = 50,
    ) -> list[CollectionTask]:
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
                f"SELECT * FROM collection_tasks{where} ORDER BY created_at DESC LIMIT ?",
                values,
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def get_alarm_snapshot(self, platform: str) -> dict[str, dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT fingerprint, alarm_json FROM alarm_snapshots WHERE platform = ?",
                (platform,),
            ).fetchall()
        return {row["fingerprint"]: json.loads(row["alarm_json"]) for row in rows}

    def replace_alarm_snapshot(
        self,
        platform: str,
        alarms: dict[str, dict[str, Any]],
    ) -> None:
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "DELETE FROM alarm_snapshots WHERE platform = ?",
                (platform,),
            )
            connection.executemany(
                "INSERT INTO alarm_snapshots (platform, fingerprint, alarm_json) "
                "VALUES (?, ?, ?)",
                [
                    (platform, fingerprint, json.dumps(alarm, ensure_ascii=False))
                    for fingerprint, alarm in alarms.items()
                ],
            )
            connection.commit()

    def _update(self, task_id: str, **fields: Any) -> None:
        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = [*fields.values(), task_id]
        with self._lock, self._connect() as connection:
            connection.execute(
                f"UPDATE collection_tasks SET {assignments} WHERE task_id = ?",
                values,
            )

    @staticmethod
    def _values(task: CollectionTask) -> tuple[Any, ...]:
        return (
            task.task_id,
            task.platform,
            task.action,
            task.trigger.value,
            task.status.value,
            task.severity,
            task.limit,
            task.created_at.isoformat(),
            task.started_at.isoformat() if task.started_at else None,
            task.finished_at.isoformat() if task.finished_at else None,
            task.duration_ms,
            json.dumps(task.result, ensure_ascii=False) if task.result else None,
            task.error_code,
            task.error_message,
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> CollectionTask:
        return CollectionTask(
            task_id=row["task_id"],
            platform=row["platform"],
            action=row["action"],
            trigger=TaskTrigger(row["trigger"]),
            status=TaskStatus(row["status"]),
            severity=row["severity"],
            limit=row["result_limit"],
            created_at=datetime.fromisoformat(row["created_at"]),
            started_at=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            finished_at=(
                datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None
            ),
            duration_ms=row["duration_ms"],
            result=json.loads(row["result_json"]) if row["result_json"] else None,
            error_code=row["error_code"],
            error_message=row["error_message"],
        )
