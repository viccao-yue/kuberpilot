from gateway.alerts.differ import (
    AlarmChangeType,
    diff_alarm_snapshots,
    index_alarms,
)


def alarm(alarm_id: str, title: str = "CPU high") -> dict:
    return {
        "alarm_id": alarm_id,
        "resource_id": "host-1",
        "resource_type": "host",
        "title": title,
        "occurred_at": "2026-08-05T10:00:00+08:00",
    }


def test_diff_identifies_new_ongoing_and_recovered_alarms():
    previous = index_alarms("mock_platform", [alarm("a-1"), alarm("a-2")])
    current = index_alarms("mock_platform", [alarm("a-2", "updated"), alarm("a-3")])

    changes, ongoing_count = diff_alarm_snapshots(previous, current)

    assert ongoing_count == 1
    assert [(item.change_type, item.alarm["alarm_id"]) for item in changes] == [
        (AlarmChangeType.NEW, "a-3"),
        (AlarmChangeType.RECOVERED, "a-1"),
    ]


def test_fingerprint_ignores_mutable_alarm_text():
    first = index_alarms("mock_platform", [alarm("a-1", "old title")])
    second = index_alarms("mock_platform", [alarm("a-1", "new title")])

    changes, ongoing_count = diff_alarm_snapshots(first, second)

    assert changes == []
    assert ongoing_count == 1
