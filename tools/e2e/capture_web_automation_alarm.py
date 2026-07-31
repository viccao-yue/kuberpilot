# -*- coding: utf-8 -*-
"""Capture browser evidence for the Web Automation alarm integration.

Run with web_automation/.venv/Scripts/python.exe while all four local services
are running. Browser profiles and temporary files are redirected by the caller.
"""

from pathlib import Path

from playwright.sync_api import sync_playwright


REPO_ROOT = Path(__file__).resolve().parents[2]
SCREENSHOT_DIR = (
    REPO_ROOT / "docs" / "screenshots" / "web-automation-alarm-integration"
)
FRONTEND_URL = "http://127.0.0.1:3000"
QUESTION = "查看mock_platform当前告警"


def main() -> None:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1000})

        page.goto(f"{FRONTEND_URL}/login", wait_until="networkidle")
        page.get_by_role("heading", name="登录平台").wait_for()
        page.screenshot(
            path=SCREENSHOT_DIR / "01-login-page.png",
            full_page=True,
        )

        page.get_by_role("button", name="进入工作台").click()
        page.wait_for_url("**/dashboard", timeout=30_000)
        page.goto(f"{FRONTEND_URL}/aiops/chat", wait_until="networkidle")
        composer = page.get_by_placeholder(
            "输入你的问题，Enter 发送，Shift + Enter 换行，Esc 收起"
        )
        composer.wait_for(timeout=30_000)
        composer.fill(QUESTION)
        page.screenshot(
            path=SCREENSHOT_DIR / "02-question-ready.png",
            full_page=True,
        )

        page.get_by_role("button", name="发送", exact=True).click()
        page.get_by_text("mock_platform 当前活动告警", exact=False).wait_for(
            timeout=60_000
        )
        page.get_by_text("test-vm-01", exact=False).wait_for(timeout=10_000)
        page.get_by_text("CPU使用率过高", exact=False).wait_for(timeout=10_000)
        page.screenshot(
            path=SCREENSHOT_DIR / "03-alarm-answer.png",
            full_page=True,
        )

        page.goto(f"{FRONTEND_URL}/aiops/audit", wait_until="networkidle")
        page.get_by_text("Web Automation Gateway", exact=False).first.wait_for(
            timeout=30_000
        )
        page.screenshot(
            path=SCREENSHOT_DIR / "04-mcp-audit.png",
            full_page=True,
        )
        browser.close()

    expected = [
        "01-login-page.png",
        "02-question-ready.png",
        "03-alarm-answer.png",
        "04-mcp-audit.png",
    ]
    missing = [name for name in expected if not (SCREENSHOT_DIR / name).is_file()]
    if missing:
        raise RuntimeError(f"Missing screenshots: {missing}")
    print(f"Captured {len(expected)} screenshots in {SCREENSHOT_DIR}")


if __name__ == "__main__":
    main()
