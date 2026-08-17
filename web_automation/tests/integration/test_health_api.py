from unittest.mock import Mock

import httpx

from gateway.app import app
from gateway.dependencies import get_delivery_worker, get_settings


async def request(method: str, path: str, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


async def test_gateway_health():
    worker = Mock()
    worker.health.return_value = {
        "is_running": False,
        "backlog": 2,
        "dead_letter": 1,
        "queue_error_type": None,
        "last_error": None,
    }
    settings = Mock(callback_enabled=False, callback_token="")
    app.dependency_overrides[get_delivery_worker] = lambda: worker
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = await request("GET", "/healthz")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["delivery_worker"] == {
        "enabled": False,
        "is_running": False,
        "backlog": 2,
        "dead_letter": 1,
        "queue_error_type": None,
        "last_error": None,
    }
    assert response.headers["content-type"] == "application/json; charset=utf-8"


async def test_gateway_health_reports_stopped_enabled_delivery_worker():
    worker = Mock()
    worker.health.return_value = {
        "is_running": False,
        "backlog": 3,
        "dead_letter": 0,
        "queue_error_type": None,
        "last_error": {
            "stage": "worker_loop",
            "type": "RuntimeError",
            "at": "2026-08-17T10:00:00+00:00",
        },
    }
    settings = Mock(callback_enabled=True, callback_token="configured")
    app.dependency_overrides[get_delivery_worker] = lambda: worker
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = await request("GET", "/healthz")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["delivery_worker"]["enabled"] is True
    assert response.json()["delivery_worker"]["is_running"] is False
    assert response.json()["delivery_worker"]["backlog"] == 3


async def test_mcp_initialize_and_list_tools():
    initialized = await request(
        "POST",
        "/mcp",
        json={"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {}},
    )
    assert initialized.json()["result"]["protocolVersion"] == "2025-03-26"

    listed = await request(
        "POST",
        "/mcp",
        json={"jsonrpc": "2.0", "id": "2", "method": "tools/list", "params": {}},
    )
    tools = listed.json()["result"]["tools"]
    assert [tool["name"] for tool in tools] == [
        "web_platform.health",
        "web_platform.list_alarms",
    ]
    assert all(tool["inputSchema"]["additionalProperties"] is False for tool in tools)


async def test_mcp_rejects_arbitrary_url_argument():
    response = await request(
        "POST",
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": "3",
            "method": "tools/call",
            "params": {
                "name": "web_platform.health",
                "arguments": {
                    "platform": "mock_platform",
                    "url": "http://169.254.169.254/",
                },
            },
        },
    )
    result = response.json()["result"]
    assert result["isError"] is True
    assert "169.254.169.254" not in str(result)
