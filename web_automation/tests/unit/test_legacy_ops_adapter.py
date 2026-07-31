from pathlib import Path

from adapters.legacy_ops_platform import LegacyOpsPlatformAdapter
from platforms.models import PlatformDefinition


def _adapter() -> LegacyOpsPlatformAdapter:
    definition = PlatformDefinition(
        platform="legacy_ops_platform",
        display_name="Legacy NOC",
        base_url="http://127.0.0.1:8012/auth/signin",
        adapter="legacy_ops_platform",
        source_file=Path("legacy.yaml"),
    )
    return LegacyOpsPlatformAdapter(definition)


def test_legacy_priority_time_and_missing_fields_are_normalized():
    alarm = _adapter()._to_standard(
        {
            "event_no": "EVT-1",
            "priority": "P2",
            "asset": "payment-api",
            "asset_kind": "",
            "summary": "接口变慢",
            "detail": "",
            "raised_time": "2026/07/31 09:23:07",
            "state": "ACK",
        }
    )
    assert alarm.severity == "warning"
    assert alarm.status == "acknowledged"
    assert alarm.resource_type == "unknown"
    assert alarm.description == "旧平台未提供补充说明。"
    assert alarm.occurred_at.isoformat() == "2026-07-31T09:23:07+08:00"
