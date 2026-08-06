from fastapi.testclient import TestClient

from legacy_ops_platform.app import BASE_EVENTS, EVENTS, app as legacy_app
from mock_platform.app import ALARMS, BASE_ALARMS, app as mock_app


def test_mock_alarm_controls_are_disabled_by_default(monkeypatch):
    monkeypatch.delenv("WEB_AUTOMATION_ENABLE_DEMO_CONTROLS", raising=False)
    response = TestClient(mock_app).post("/test/alarms/add", follow_redirects=False)
    assert response.status_code == 404


def test_mock_alarm_controls_add_and_resolve_when_authenticated(monkeypatch):
    monkeypatch.setenv("WEB_AUTOMATION_ENABLE_DEMO_CONTROLS", "1")
    ALARMS[:] = [item.copy() for item in BASE_ALARMS]
    client = TestClient(mock_app)
    login = client.post(
        "/login",
        data={"username": "aiops_robot", "password": "MockOnly@123456"},
    )
    assert login.status_code == 200

    added = client.post("/test/alarms/add")
    assert added.status_code == 200
    assert any(item["id"] == "alarm-004" for item in ALARMS)

    resolved = client.post("/test/alarms/alarm-004/resolve")
    assert resolved.status_code == 200
    assert not any(item["id"] == "alarm-004" for item in ALARMS)


def test_legacy_event_controls_add_and_resolve_when_authenticated(monkeypatch):
    monkeypatch.setenv("WEB_AUTOMATION_ENABLE_DEMO_CONTROLS", "1")
    EVENTS[:] = [item.copy() for item in BASE_EVENTS]
    client = TestClient(legacy_app)
    login = client.post(
        "/auth/signin",
        data={"operator": "legacy_reader", "access_key": "LegacyOnly@123456"},
    )
    assert login.status_code == 200

    added = client.post("/test/events/add")
    assert added.status_code == 200
    assert any(item["event_no"] == "EVT-9004" for item in EVENTS)

    resolved = client.post("/test/events/EVT-9004/resolve")
    assert resolved.status_code == 200
    assert not any(item["event_no"] == "EVT-9004" for item in EVENTS)
