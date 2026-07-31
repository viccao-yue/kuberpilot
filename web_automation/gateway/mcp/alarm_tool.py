"""Read-only alarm collection through a platform adapter."""

import json

import adapters.mock_platform  # noqa: F401 - registers the adapter plugin
import adapters.legacy_ops_platform  # noqa: F401 - registers the adapter plugin
from adapters.registry import get_adapter
from credentials.environment import (
    CredentialUnavailableError,
    EnvironmentCredentialProvider,
)
from network.checker import ConnectivityChecker
from platforms.loader import PlatformNotFoundError, PlatformRegistry


TOOL_NAME = "web_platform.list_alarms"
TOOL_DEFINITION = {
    "name": TOOL_NAME,
    "description": (
        "Log in to an administrator-registered operations platform with an internal "
        "read-only credential and return standardized active alarms. Credentials, "
        "cookies and target URLs are never accepted from the model."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "platform": {
                "type": "string",
                "pattern": "^[a-z][a-z0-9_-]{1,63}$",
                "description": (
                    "Registered platform id, for example mock_platform or "
                    "legacy_ops_platform"
                ),
            },
            "severity": {
                "type": "string",
                "enum": ["all", "critical", "warning", "info"],
                "default": "all",
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
        },
        "required": ["platform"],
        "additionalProperties": False,
    },
}


def _error(message: str, code: str) -> dict:
    payload = {"ok": False, "error_code": code, "message": message}
    return {
        "isError": True,
        "structuredContent": payload,
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
    }


async def call_alarm_tool(
    arguments: dict,
    registry: PlatformRegistry,
    checker: ConnectivityChecker,
    credential_provider: EnvironmentCredentialProvider,
) -> dict:
    allowed = {"platform", "severity", "limit"}
    if not isinstance(arguments, dict) or set(arguments) - allowed:
        return _error("Only platform, severity and limit are allowed.", "INVALID_ARGUMENTS")
    platform = arguments.get("platform")
    severity = arguments.get("severity", "all")
    limit = arguments.get("limit", 20)
    if not isinstance(platform, str) or severity not in {"all", "critical", "warning", "info"}:
        return _error("Platform or severity is invalid.", "INVALID_ARGUMENTS")
    if not isinstance(limit, int) or not 1 <= limit <= 50:
        return _error("Limit must be an integer from 1 to 50.", "INVALID_ARGUMENTS")

    try:
        definition = registry.get(platform)
    except PlatformNotFoundError:
        return _error("The requested platform is not registered.", "PLATFORM_NOT_FOUND")
    if not definition.credential_id:
        return _error("The platform has no credential reference.", "CREDENTIAL_NOT_CONFIGURED")

    connectivity = await checker.check_platform(platform)
    if not connectivity.overall_ok:
        return _error(
            f"Platform connectivity failed at {connectivity.failed_stage}: {connectivity.message}",
            connectivity.error_code or "CONNECTIVITY_FAILED",
        )

    try:
        credential = credential_provider.resolve(definition.credential_id)
        adapter_class = get_adapter(definition.adapter)
        alarms = await adapter_class(definition).list_alarms(
            credential,
            severity=severity,
            limit=limit,
        )
    except CredentialUnavailableError:
        return _error("The read-only platform credential is unavailable.", "CREDENTIAL_UNAVAILABLE")
    except Exception as exc:
        return _error(
            f"Alarm collection failed: {type(exc).__name__}",
            "ALARM_COLLECTION_FAILED",
        )

    alarm_payload = [item.model_dump(mode="json") for item in alarms]
    severity_counts = {
        name: len([item for item in alarms if item.severity == name])
        for name in ("critical", "warning", "info")
    }
    payload = {
        "ok": True,
        "platform": platform,
        "count": len(alarms),
        "severity_counts": severity_counts,
        "alarms": alarm_payload,
        "collection_method": "playwright_authenticated_session",
        "read_only": True,
    }
    lines = [
        f"{item.severity.upper()}｜{item.resource_name}｜{item.title}｜{item.description}"
        for item in alarms
    ]
    text = f"{platform} 当前返回 {len(alarms)} 条活动告警。"
    if lines:
        text += "\n" + "\n".join(lines)
    return {
        "isError": False,
        "structuredContent": payload,
        "content": [{"type": "text", "text": text}],
    }
