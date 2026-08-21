"""Read active alarms from an authenticated KuberCon management console."""

import hashlib
import re
from typing import Any

from playwright.async_api import BrowserContext, Page, async_playwright

from adapters.base import BaseAdapter, PlatformLoginError
from adapters.browser import browser_launch_options, browser_state_path, platform_origin
from adapters.registry import register_adapter
from credentials.models import Credential
from models.standard import StandardAlarm


SEVERITY_MAP = {
    "critical": "critical",
    "error": "critical",
    "warning": "warning",
    "warn": "warning",
    "info": "info",
}
STATE_MAP = {
    "firing": "firing",
    "pending": "pending",
    "inactive": "resolved",
    "resolved": "resolved",
}
RESOURCE_LABELS = (
    ("pod", "pod"),
    ("deployment", "deployment"),
    ("statefulset", "statefulset"),
    ("daemonset", "daemonset"),
    ("node", "node"),
    ("service", "service"),
    ("instance", "instance"),
    ("namespace", "namespace"),
)
CLUSTER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]{0,62}$")


@register_adapter
class KuberConAdapter(BaseAdapter):
    """Use browser login and KuberCon's authenticated read-only alarm APIs."""

    PLATFORM = "kubercon"

    @property
    def origin(self) -> str:
        return platform_origin(self.definition)

    @property
    def state_path(self):
        return browser_state_path(self.definition)

    @property
    def cluster(self) -> str:
        value = str(self.definition.adapter_options.get("cluster", "host")).strip()
        if not CLUSTER_PATTERN.fullmatch(value):
            raise ValueError("KuberCon cluster option is invalid")
        return value

    @property
    def include_builtin(self) -> bool:
        return self.definition.adapter_options.get("include_builtin", True) is not False

    @property
    def alarm_page_url(self) -> str:
        return f"{self.origin}/clusters/{self.cluster}/alerts"

    def alarm_api_url(self, builtin: bool = False) -> str:
        resource = "globalalerts" if builtin else "clusteralerts"
        return (
            f"{self.origin}/kapis/clusters/{self.cluster}/"
            f"alerting.kubercloud.com/v2beta1/{resource}"
        )

    async def list_alarms(
        self,
        credential: Credential,
        severity: str = "all",
        limit: int = 20,
    ) -> list[StandardAlarm]:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(**browser_launch_options())
            try:
                context_options: dict[str, Any] = {}
                if self.state_path.is_file():
                    context_options["storage_state"] = str(self.state_path)
                context = await browser.new_context(**context_options)
                page = await context.new_page()
                await self._ensure_logged_in(page, context, credential)

                try:
                    items = await self._fetch_alarm_items(context, limit, severity)
                except PermissionError:
                    await page.goto(f"{self.origin}/login", wait_until="domcontentloaded")
                    await self._login(page, context, credential)
                    items = await self._fetch_alarm_items(context, limit, severity)

                alarms = [self._to_standard(item) for item in items]
                if severity != "all":
                    alarms = [item for item in alarms if item.severity == severity]
                alarms.sort(key=lambda item: item.occurred_at, reverse=True)
                return alarms[:limit]
            finally:
                await browser.close()

    async def _ensure_logged_in(
        self,
        page: Page,
        context: BrowserContext,
        credential: Credential,
    ) -> None:
        await page.goto(self.alarm_page_url, wait_until="domcontentloaded")
        if "/login" in page.url:
            await self._login(page, context, credential)

    async def _login(
        self,
        page: Page,
        context: BrowserContext,
        credential: Credential,
    ) -> None:
        await page.locator('input[name="username"]').fill(credential.username)
        await page.locator('input[name="password"]').fill(
            credential.password.get_secret_value()
        )
        await page.locator('button[type="submit"]').click()
        try:
            await page.wait_for_url(
                lambda url: "/login" not in str(url),
                timeout=15_000,
            )
        except Exception as exc:
            raise PlatformLoginError(
                "KuberCon login failed; credentials or page contract changed"
            ) from exc
        await context.storage_state(path=str(self.state_path))

    async def _fetch_alarm_items(
        self,
        context: BrowserContext,
        limit: int,
        severity: str = "all",
    ) -> list[dict[str, Any]]:
        kinds = [False, True] if self.include_builtin else [False]
        items: list[dict[str, Any]] = []
        for builtin in kinds:
            params = {
                "page": 1,
                "limit": limit,
                "sortBy": "createTime",
                "ascending": "false",
                **({"builtin": "true"} if builtin else {}),
            }
            if severity != "all":
                params["label_filters"] = f"severity={severity}"
            response = await context.request.get(
                self.alarm_api_url(builtin=builtin),
                params=params,
            )
            if response.status in {401, 403}:
                raise PermissionError("KuberCon session is not authenticated")
            if not response.ok:
                raise RuntimeError(f"KuberCon alarm API returned status {response.status}")
            payload = await response.json()
            if not isinstance(payload, dict) or not isinstance(
                payload.get("items", []), list
            ):
                raise RuntimeError("KuberCon alarm API returned an invalid response schema")
            source = "builtin" if builtin else "custom"
            for item in payload.get("items", []):
                if isinstance(item, dict):
                    items.append({**item, "_source": source})
        return items

    def _to_standard(self, item: dict[str, Any]) -> StandardAlarm:
        labels = item.get("labels") if isinstance(item.get("labels"), dict) else {}
        annotations = (
            item.get("annotations")
            if isinstance(item.get("annotations"), dict)
            else {}
        )
        occurred_at = item.get("activeAt")
        if not occurred_at:
            raise ValueError("KuberCon alarm has no activeAt value")
        resource_type, resource_name = self._resource_identity(labels)
        namespace = str(labels.get("namespace") or "").strip()
        rule_id = str(labels.get("rule_id") or "unknown").strip()
        alert_name = str(labels.get("alertname") or "unnamed-alert").strip()
        source_collection = str(item.get("_source") or "custom").strip()
        lifecycle_key = "|".join(
            (
                self.cluster,
                source_collection,
                rule_id,
                alert_name,
                resource_type,
                resource_name,
                str(occurred_at),
            )
        )
        alarm_digest = hashlib.sha256(lifecycle_key.encode("utf-8")).hexdigest()[:24]
        resource_parts = [self.definition.platform, self.cluster]
        if namespace:
            resource_parts.append(namespace)
        resource_parts.extend((resource_type, resource_name))
        title = str(annotations.get("summary") or alert_name).strip()
        description = str(
            annotations.get("description") or annotations.get("message") or title
        ).strip()
        severity = SEVERITY_MAP.get(str(labels.get("severity", "")).lower(), "info")
        status = STATE_MAP.get(str(item.get("state", "")).lower(), "firing")
        return StandardAlarm(
            alarm_id=f"{self.definition.platform}::{alarm_digest}",
            severity=severity,
            resource_id="::".join(resource_parts),
            resource_type=resource_type,
            resource_name=resource_name,
            title=title,
            description=description,
            occurred_at=occurred_at,
            platform=self.definition.platform,
            status=status,
            raw_data={
                "source_rule_id": rule_id,
                "source_rule_group": labels.get("rule_group"),
                "source_rule_level": labels.get("rule_level"),
                "source_collection": source_collection,
                "source_value": item.get("value"),
            },
        )

    def _resource_identity(self, labels: dict[str, Any]) -> tuple[str, str]:
        for label, resource_type in RESOURCE_LABELS:
            value = str(labels.get(label) or "").strip()
            if value:
                return resource_type, value
        return "cluster", self.cluster
