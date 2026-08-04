from urllib.parse import urlencode

import httpx

from mock_platform.app import app


async def test_login_protects_alarm_api(monkeypatch):
    monkeypatch.setenv("MOCK_PLATFORM_USERNAME", "aiops_robot")
    monkeypatch.setenv("MOCK_PLATFORM_PASSWORD", "test-password")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://mock",
        follow_redirects=True,
    ) as client:
        login_page = await client.get("/login")
        assert "仅限本地演示" not in login_page.text
        monkeypatch.setenv("WEB_AUTOMATION_SHOW_DEMO_CREDENTIALS", "1")
        demo_login_page = await client.get("/login")
        assert "仅限本地演示" in demo_login_page.text
        assert "aiops_robot" in demo_login_page.text
        assert "test-password" in demo_login_page.text

        anonymous = await client.get("/api/internal/alarms")
        assert anonymous.status_code == 401

        login = await client.post(
            "/login",
            content=urlencode(
                {"username": "aiops_robot", "password": "test-password"}
            ),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert login.status_code == 200
        assert "登录成功" in login.text

        alarms = await client.get("/api/internal/alarms?severity=critical&limit=20")
        assert alarms.status_code == 200
        payload = alarms.json()
        assert payload["count"] == 1
        assert payload["alarms"][0]["resource_name"] == "test-vm-01"


async def test_wrong_password_does_not_create_session(monkeypatch):
    monkeypatch.setenv("MOCK_PLATFORM_USERNAME", "aiops_robot")
    monkeypatch.setenv("MOCK_PLATFORM_PASSWORD", "correct-password")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://mock") as client:
        response = await client.post(
            "/login",
            content=urlencode({"username": "aiops_robot", "password": "wrong"}),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 200
        assert "账号或密码错误" in response.text
        assert "mock_ops_session" not in response.cookies
