"""Build and deliver normalized alarm callbacks to KuberPilot."""

from datetime import datetime, timezone
from typing import Any

import httpx

from gateway.alerts.differ import AlarmChange, AlarmChangeType


class CallbackDeliveryError(RuntimeError):
    def __init__(self, error_code: str, public_message: str):
        super().__init__(public_message)
        self.error_code = error_code
        self.public_message = public_message


class KuberPilotCallbackClient:
    def __init__(
        self,
        url: str,
        token: str,
        *,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.url = url
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def deliver(
        self,
        task_id: str,
        platform: str,
        change: AlarmChange,
    ) -> None:
        await self.deliver_payload(self.build_payload(task_id, platform, change))

    async def deliver_payload(self, payload: dict[str, Any]) -> None:
        """Make exactly one HTTP attempt; durable retry belongs to DeliveryWorker."""
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
            trust_env=False,
        ) as client:
            try:
                response = await client.post(
                    self.url,
                    json=payload,
                    headers={"X-KuberPilot-Token": self.token},
                )
                response.raise_for_status()
            except (httpx.HTTPError, ValueError) as exc:
                raise CallbackDeliveryError(
                    type(exc).__name__.upper(),
                    "KuberPilot callback request failed",
                ) from exc

    @staticmethod
    def build_payload(
        task_id: str,
        platform: str,
        change: AlarmChange,
    ) -> dict[str, Any]:
        alarm = change.alarm
        recovered = change.change_type == AlarmChangeType.RECOVERED
        return {
            "id": change.event_id,
            "external_id": str(alarm.get("alarm_id") or change.fingerprint),
            "fingerprint": change.fingerprint,
            "title": str(alarm.get("title") or "Web Automation 告警"),
            "level": str(alarm.get("severity") or "info"),
            "status": "resolved" if recovered else "firing",
            "source": f"Web Automation / {platform}",
            "message": str(alarm.get("description") or alarm.get("title") or ""),
            "service": str(alarm.get("resource_name") or ""),
            "resource_type": str(alarm.get("resource_type") or ""),
            "resource": str(alarm.get("resource_id") or alarm.get("resource_name") or ""),
            "starts_at": alarm.get("occurred_at"),
            "ends_at": datetime.now(timezone.utc).isoformat() if recovered else None,
            "labels": {
                "platform": platform,
                "change_type": change.change_type.value,
                "collection_task_id": task_id,
            },
            "annotations": {
                "description": str(alarm.get("description") or ""),
                "web_automation_event_id": change.event_id,
            },
        }
