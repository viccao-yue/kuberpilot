import httpx

from gateway.app import app


async def request(method: str, path: str, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


async def test_gateway_health():
    response = await request("GET", "/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.headers["content-type"] == "application/json; charset=utf-8"


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
