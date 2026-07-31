"""Adapter for a legacy platform that exposes alarms only as an HTML table."""

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright

from adapters.base import BaseAdapter
from adapters.mock_platform import PlatformLoginError
from adapters.registry import register_adapter
from credentials.models import Credential
from models.standard import StandardAlarm


PRIORITY_TO_SEVERITY = {"P1": "critical", "P2": "warning", "P3": "info"}
STATE_TO_STATUS = {"OPEN": "firing", "ACK": "acknowledged"}


@register_adapter
class LegacyOpsPlatformAdapter(BaseAdapter):
    PLATFORM = "legacy_ops_platform"

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
                context = await browser.new_context(**context_options)
                page = await context.new_page()
                await page.goto(f"{self.origin}/active-events", wait_until="domcontentloaded")
                if "/auth/signin" in page.url:
                    await page.get_by_label("操作员工号").fill(credential.username)
                    await page.get_by_label("访问口令").fill(
                        credential.password.get_secret_value()
                    )
                    await page.get_by_role("button", name="进入控制台").click()
                    try:
                        await page.wait_for_url("**/console", timeout=10_000)
                    except Exception as exc:
                        raise PlatformLoginError(
                            "Legacy platform login failed; credentials or page contract changed"
                        ) from exc
                    await context.storage_state(path=str(self.state_path))
                    await page.goto(
                        f"{self.origin}/active-events",
                        wait_until="domcontentloaded",
                    )
                rows = page.locator("#event-grid tbody tr")
                alarms = []
                for index in range(await rows.count()):
                    row = rows.nth(index)
                    raw = {
                        "event_no": await row.get_attribute("data-event-no"),
                        "priority": (await row.locator(".priority").inner_text()).strip(),
                        "asset": (await row.locator(".asset").inner_text()).strip(),
                        "asset_kind": (await row.locator(".asset-kind").inner_text()).strip(),
                        "summary": (await row.locator(".summary").inner_text()).strip(),
                        "detail": (await row.locator(".detail").inner_text()).strip(),
                        "raised_time": (await row.locator(".raised-time").inner_text()).strip(),
                        "state": (await row.locator(".state").inner_text()).strip(),
                    }
                    alarm = self._to_standard(raw)
                    if severity == "all" or alarm.severity == severity:
                        alarms.append(alarm)
                    if len(alarms) >= limit:
                        break
                return alarms
            finally:
                await browser.close()

    def _to_standard(self, item: dict) -> StandardAlarm:
        occurred_at = datetime.strptime(
            item["raised_time"],
            "%Y/%m/%d %H:%M:%S",
        ).replace(tzinfo=timezone(timedelta(hours=8)))
        event_no = item.get("event_no") or "unknown"
        asset = item.get("asset") or "unknown"
        return StandardAlarm(
            alarm_id=f"{self.definition.platform}::{event_no}",
            severity=PRIORITY_TO_SEVERITY.get(item.get("priority"), "info"),
            resource_id=f"{self.definition.platform}::{asset}",
            resource_type=(item.get("asset_kind") or "unknown").lower(),
            resource_name=asset,
            title=item.get("summary") or "未命名事件",
            description=item.get("detail") or "旧平台未提供补充说明。",
            occurred_at=occurred_at,
            platform=self.definition.platform,
            status=STATE_TO_STATUS.get(item.get("state"), "firing"),
            raw_data={
                "source_event_no": event_no,
                "source_priority": item.get("priority"),
            },
        )
