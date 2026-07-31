"""Playwright adapter that logs in through the real mock-platform HTML form."""

import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright

from adapters.base import BaseAdapter
from adapters.registry import register_adapter
from credentials.models import Credential
from models.standard import StandardAlarm


class PlatformLoginError(RuntimeError):
    pass


@register_adapter
class MockPlatformAdapter(BaseAdapter):
    PLATFORM = "mock_platform"

    @property
    def origin(self) -> str:
        parsed = urlsplit(str(self.definition.base_url))
        port = f":{parsed.port}" if parsed.port else ""
        return f"{parsed.scheme}://{parsed.hostname}{port}"

    @property
    def state_path(self) -> Path:
        root = Path(__file__).resolve().parents[1]
        path = root / ".runtime" / "browser-state" / f"{self.definition.platform}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    async def list_alarms(
        self,
        credential: Credential,
        severity: str = "all",
        limit: int = 20,
    ) -> list[StandardAlarm]:
        async with async_playwright() as playwright:
            channel = os.environ.get("PLAYWRIGHT_BROWSER_CHANNEL", "msedge")
            launch_options = {"headless": True}
            if channel and channel != "chromium":
                launch_options["channel"] = channel
            browser = await playwright.chromium.launch(**launch_options)
            try:
                context_options = {}
                if self.state_path.is_file():
                    context_options["storage_state"] = str(self.state_path)
                if self.definition.ca_cert_path:
                    context_options["ignore_https_errors"] = False
                context = await browser.new_context(**context_options)
                page = await context.new_page()

                response = await page.goto(
                    f"{self.origin}/api/internal/alarms?severity={severity}&limit={limit}",
                    wait_until="domcontentloaded",
                )
                if response is None or response.status == 401:
                    await page.goto(f"{self.origin}/login", wait_until="domcontentloaded")
                    await page.get_by_label("只读服务账号").fill(credential.username)
                    await page.get_by_label("密码").fill(
                        credential.password.get_secret_value()
                    )
                    await page.get_by_role("button", name="登录").click()
                    try:
                        await page.wait_for_url("**/dashboard", timeout=10_000)
                    except Exception as exc:
                        raise PlatformLoginError(
                            "Mock platform login failed; credentials or page contract changed"
                        ) from exc
                    await context.storage_state(path=str(self.state_path))
                    response = await page.goto(
                        f"{self.origin}/api/internal/alarms?severity={severity}&limit={limit}",
                        wait_until="domcontentloaded",
                    )
                if response is None or response.status != 200:
                    status = response.status if response else "no-response"
                    raise RuntimeError(f"Alarm API returned status {status}")
                payload = json.loads(await page.locator("body").inner_text())
                return [self._to_standard(item) for item in payload.get("alarms", [])]
            finally:
                await browser.close()

    def _to_standard(self, item: dict) -> StandardAlarm:
        return StandardAlarm(
            alarm_id=f"{self.definition.platform}::{item['id']}",
            severity=item.get("level", "info"),
            resource_id=f"{self.definition.platform}::{item.get('resource_id', 'unknown')}",
            resource_type=item.get("resource_type", "unknown"),
            resource_name=item.get("resource_name", "unknown"),
            title=item.get("title", ""),
            description=item.get("message", ""),
            occurred_at=item["occurred_at"],
            platform=self.definition.platform,
            status=item.get("status", "firing"),
            raw_data={"source_alarm_id": item.get("id")},
        )
