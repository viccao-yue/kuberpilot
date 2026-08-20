import httpx
import pytest

from gateway.alerts.callback import CallbackDeliveryError, KuberPilotCallbackClient
from gateway.alerts.differ import AlarmChange, AlarmChangeType


def change(change_type: AlarmChangeType = AlarmChangeType.NEW) -> AlarmChange:
    return AlarmChange(
        change_type,
        "stable-fingerprint",
        {
            "alarm_id": "mock_platform::alarm-001",
            "severity": "critical",
            "resource_id": "mock_platform::vm-001",
            "resource_type": "vm",
            "resource_name": "test-vm-01",
            "title": "CPU使用率过高",
            "description": "CPU达到95%",
            "occurred_at": "2026-08-05T10:00:00+08:00",
        },
    )


async def test_callback_sends_token_and_normalized_active_payload():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["token"] = request.headers.get("X-KuberPilot-Token")
        captured["payload"] = __import__("json").loads(request.content)
        return httpx.Response(202, json={"success": True})

    client = KuberPilotCallbackClient(
        "http://kuberpilot.local/api/alerts/webhooks/generic/",
        "secret-token",
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )

    await client.deliver("task-1", "mock_platform", change())

    assert captured["token"] == "secret-token"
    assert captured["payload"]["status"] == "firing"
    assert captured["payload"]["labels"]["collection_task_id"] == "task-1"


async def test_callback_makes_one_attempt_and_reports_sanitized_failure():
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503)

    client = KuberPilotCallbackClient(
        "http://kuberpilot.local/callback",
        "secret-token",
        timeout_seconds=1,
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(CallbackDeliveryError) as raised:
        await client.deliver("task-1", "mock_platform", change())

    assert calls == 1
    assert raised.value.error_code == "HTTPSTATUSERROR"
    assert "secret-token" not in str(raised.value)


def test_recovered_callback_uses_same_fingerprint_and_resolved_status():
    payload = KuberPilotCallbackClient.build_payload(
        "task-2",
        "mock_platform",
        change(AlarmChangeType.RECOVERED),
    )

    assert payload["fingerprint"] == "stable-fingerprint"
    assert payload["status"] == "resolved"
    assert payload["ends_at"] is not None
