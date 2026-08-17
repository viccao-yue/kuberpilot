"""Compare the latest alarm collection with the last delivered snapshot."""

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any


class AlarmChangeType(str, Enum):
    NEW = "new"
    RECOVERED = "recovered"


@dataclass(frozen=True)
class AlarmChange:
    change_type: AlarmChangeType
    fingerprint: str
    alarm: dict[str, Any]
    lifecycle_sequence: int = 1

    @property
    def event_id(self) -> str:
        occurred_at = str(self.alarm.get("occurred_at") or "")
        value = f"{self.change_type.value}:{self.fingerprint}:{occurred_at}"
        if self.lifecycle_sequence > 1:
            value = f"{value}:{self.lifecycle_sequence}"
        return hashlib.sha256(value.encode("utf-8")).hexdigest()


def alarm_fingerprint(platform: str, alarm: dict[str, Any]) -> str:
    """Build a stable identity without using mutable title or description text."""
    alarm_id = str(alarm.get("alarm_id") or "").strip()
    if alarm_id:
        identity = {"platform": platform, "alarm_id": alarm_id}
    else:
        identity = {
            "platform": platform,
            "resource_id": alarm.get("resource_id"),
            "resource_type": alarm.get("resource_type"),
            "title": alarm.get("title"),
        }
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def index_alarms(platform: str, alarms: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {alarm_fingerprint(platform, alarm): alarm for alarm in alarms}


def diff_alarm_snapshots(
    previous: dict[str, dict[str, Any]],
    current: dict[str, dict[str, Any]],
) -> tuple[list[AlarmChange], int]:
    new_fingerprints = sorted(set(current) - set(previous))
    recovered_fingerprints = sorted(set(previous) - set(current))
    changes = [
        AlarmChange(AlarmChangeType.NEW, fingerprint, current[fingerprint])
        for fingerprint in new_fingerprints
    ]
    changes.extend(
        AlarmChange(AlarmChangeType.RECOVERED, fingerprint, previous[fingerprint])
        for fingerprint in recovered_fingerprints
    )
    ongoing_count = len(set(previous) & set(current))
    return changes, ongoing_count
