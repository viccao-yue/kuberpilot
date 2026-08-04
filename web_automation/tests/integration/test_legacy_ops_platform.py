from urllib.parse import urlencode

import httpx

from legacy_ops_platform.app import SESSIONS, app


async def test_legacy_platform_has_no_alarm_api_and_renders_html_table(monkeypatch):
    monkeypatch.setenv("LEGACY_OPS_USERNAME", "legacy_reader")
    monkeypatch.setenv("LEGACY_OPS_PASSWORD", "test-password")
    SESSIONS.clear()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://legacy",
        follow_redirects=True,
    ) as client:
        anonymous = await client.get("/active-events")
        assert anonymous.status_code == 200
        assert "Legacy NOC Console 3.2" in anonymous.text
        assert "仅限本地演示" not in anonymous.text
        monkeypatch.setenv("WEB_AUTOMATION_SHOW_DEMO_CREDENTIALS", "1")
        demo_login_page = await client.get("/auth/signin")
        assert "仅限本地演示" in demo_login_page.text
        assert "legacy_reader" in demo_login_page.text
        assert "test-password" in demo_login_page.text

        login = await client.post(
            "/auth/signin",
            content=urlencode(
                {"operator": "legacy_reader", "access_key": "test-password"}
            ),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert login.status_code == 200
        assert "只读事件查询" in login.text

        events = await client.get("/active-events")
        assert events.status_code == 200
        assert 'id="event-grid"' in events.text
        assert "EVT-9001" in events.text
        assert "2026/07/31 09:18:32" in events.text


async def test_legacy_session_can_expire(monkeypatch):
    monkeypatch.setenv("LEGACY_OPS_USERNAME", "legacy_reader")
    monkeypatch.setenv("LEGACY_OPS_PASSWORD", "test-password")
    SESSIONS.clear()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://legacy",
        follow_redirects=True,
    ) as client:
        await client.post(
            "/auth/signin",
            content=urlencode(
                {"operator": "legacy_reader", "access_key": "test-password"}
            ),
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert "活动事件列表" in (await client.get("/active-events")).text
        await client.post("/test/expire-session")
        assert "Legacy NOC Console 3.2" in (await client.get("/active-events")).text
