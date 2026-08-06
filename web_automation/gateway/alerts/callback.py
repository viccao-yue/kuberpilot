"""Deliver normalized alarm changes to KuberPilot's existing alert webhook."""

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx

from gateway.alerts.differ import AlarmChange, AlarmChangeType


class CallbackDeliveryError(RuntimeError):
    def __init__(self, attempts: int, message: str):
        super().__init__(message)
        self.attempts = attempts


class KuberPilotCallbackClient:
    def __init__(
        self,
        url: str,
        token: str,
        *,
        timeout_seconds: float,
        retry_delays_seconds: tuple[float, ...],
        transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.url = url
        self.token = token
        self.timeout_seconds = timeout_seconds
        self.retry_delays_seconds = retry_delays_seconds
        self.transport = transport

    async def deliver(
        self,
        task_id: str,
        platform: str,
        change: AlarmChange,
    ) -> int:
        payload = self._payload(task_id, platform, change)
        attempts = 1 + len(self.retry_delays_seconds)
        last_error = "callback failed"
        async with httpx.AsyncClient(
            timeout=self.timeout_seconds,
            transport=self.transport,
            trust_env=False,
        ) as client:
            for attempt in range(1, attempts + 1):
                try:
                    response = await client.post(
                        self.url,
                        json=payload,
                        headers={"X-KuberPilot-Token": self.token},
                    )
                    response.raise_for_status()
                    return attempt
                except (httpx.HTTPError, ValueError) as exc:
                    last_error = f"{type(exc).__name__}"
                    if attempt < attempts:
                        await asyncio.sleep(self.retry_delays_seconds[attempt - 1])
        raise CallbackDeliveryError(attempts, last_error)

    @staticmethod
    def _payload(
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
