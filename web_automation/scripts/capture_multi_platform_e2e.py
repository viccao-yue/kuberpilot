"""Capture reproducible browser evidence for the two-platform AIOps workflow."""

import asyncio
import os
from pathlib import Path

from playwright.async_api import async_playwright


ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_DIR = (
    ROOT / "docs" / "screenshots" / "web-automation-multi-platform"
)


async def main() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as playwright:
        launch_options = {"headless": True}
        channel = os.environ.get("PLAYWRIGHT_BROWSER_CHANNEL", "msedge")
        if channel and channel != "chromium":
            launch_options["channel"] = channel
        browser = await playwright.chromium.launch(**launch_options)
        context = await browser.new_context(
            viewport={"width": 1440, "height": 1000},
            locale="zh-CN",
        )
        kuberpilot_page = await context.new_page()
        await kuberpilot_page.goto(
            "http://127.0.0.1:3000/login",
            wait_until="networkidle",
        )
        await kuberpilot_page.get_by_placeholder("请输入用户名").fill("admin")
        await kuberpilot_page.get_by_placeholder("请输入密码").fill("Admin@123456")
        await kuberpilot_page.get_by_role("button", name="进入工作台").click()
        await kuberpilot_page.wait_for_url(
            lambda url: "/login" not in url,
            timeout=20_000,
        )
        await kuberpilot_page.goto(
            "http://127.0.0.1:3000/aiops/chat",
            wait_until="networkidle",
        )

        composer = kuberpilot_page.get_by_placeholder(
            "输入你的问题，Enter 发送，Shift + Enter 换行，Esc 收起"
        )
        await composer.fill("查看mock_platform当前告警")
        await kuberpilot_page.get_by_role("button", name="发送").click()
        mock_result = kuberpilot_page.get_by_text("test-vm-01", exact=False).last
        await mock_result.wait_for(timeout=60_000)
        await mock_result.scroll_into_view_if_needed()
        await kuberpilot_page.screenshot(
            path=SCREENSHOT_DIR / "01-mock-kuberpilot-query.png",
            full_page=False,
        )

        mock_page = await context.new_page()
        await mock_page.goto("http://127.0.0.1:8011/login", wait_until="networkidle")
        await mock_page.screenshot(
            path=SCREENSHOT_DIR / "02-mock-platform-login.png",
            full_page=True,
        )
        mock_username = await mock_page.locator("[data-demo-username]").inner_text()
        mock_password = await mock_page.locator("[data-demo-password]").inner_text()
        await mock_page.get_by_label("只读服务账号").fill(mock_username)
        await mock_page.get_by_label("密码").fill(mock_password)
        await mock_page.get_by_role("button", name="登录").click()
        await mock_page.wait_for_url("**/dashboard")
        await mock_page.screenshot(
            path=SCREENSHOT_DIR / "03-mock-platform-home.png",
            full_page=True,
        )
        await mock_page.get_by_role("link", name="查看告警列表").click()
        await mock_page.wait_for_url("**/alarms")
        await mock_page.get_by_role("heading", name="活动告警").wait_for()
        await mock_page.screenshot(
            path=SCREENSHOT_DIR / "04-mock-platform-alarm-page.png",
            full_page=True,
        )
        await mock_page.close()

        await composer.fill("查看legacy_ops_platform当前告警")
        await kuberpilot_page.get_by_role("button", name="发送").click()
        legacy_result = kuberpilot_page.get_by_text(
            "legacy_ops_platform 当前活动告警",
            exact=False,
        ).last
        await legacy_result.wait_for(timeout=60_000)
        await legacy_result.scroll_into_view_if_needed()
        await kuberpilot_page.screenshot(
            path=SCREENSHOT_DIR / "05-legacy-kuberpilot-query.png",
            full_page=False,
        )

        legacy_page = await context.new_page()
        await legacy_page.goto(
            "http://127.0.0.1:8012/auth/signin",
            wait_until="networkidle",
        )
        await legacy_page.screenshot(
            path=SCREENSHOT_DIR / "06-legacy-platform-login.png",
            full_page=True,
        )
        legacy_username = await legacy_page.locator(
            "[data-demo-username]"
        ).inner_text()
        legacy_password = await legacy_page.locator(
            "[data-demo-password]"
        ).inner_text()
        await legacy_page.get_by_label("操作员工号").fill(legacy_username)
        await legacy_page.get_by_label("访问口令").fill(legacy_password)
        await legacy_page.get_by_role("button", name="进入控制台").click()
        await legacy_page.wait_for_url("**/console")
        await legacy_page.screenshot(
            path=SCREENSHOT_DIR / "07-legacy-platform-home.png",
            full_page=True,
        )
        await legacy_page.get_by_role("link", name="进入活动事件列表").click()
        await legacy_page.wait_for_selector("#event-grid")
        await legacy_page.screenshot(
            path=SCREENSHOT_DIR / "08-legacy-platform-alarm-page.png",
            full_page=True,
        )
        await legacy_page.close()

        await kuberpilot_page.goto(
            "http://127.0.0.1:3000/aiops/audit",
            wait_until="networkidle",
        )
        await kuberpilot_page.get_by_text("调用审计", exact=True).click()
        await kuberpilot_page.get_by_text("MCP 工具", exact=True).click()
        await kuberpilot_page.get_by_text(
            "web_platform.list_alarms",
            exact=False,
        ).first.wait_for(
            timeout=30_000
        )
        expand_icons = kuberpilot_page.locator(".el-table__expand-icon")
        for index in range(min(2, await expand_icons.count())):
            await expand_icons.nth(index).click()
        await kuberpilot_page.screenshot(
            path=SCREENSHOT_DIR / "09-multi-platform-mcp-audit.png",
            full_page=True,
        )
        await browser.close()

    print(f"Saved browser evidence to {SCREENSHOT_DIR}")


if __name__ == "__main__":
    asyncio.run(main())
