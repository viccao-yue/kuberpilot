"""Shared Playwright browser settings used by platform adapters."""

import os
from pathlib import Path
from urllib.parse import urlsplit

from platforms.models import PlatformDefinition


def browser_launch_options() -> dict[str, object]:
    """Return the administrator-controlled browser launch options."""
    channel = os.environ.get("PLAYWRIGHT_BROWSER_CHANNEL", "msedge")
    options: dict[str, object] = {"headless": True}
    if channel and channel != "chromium":
        options["channel"] = channel
    return options


def platform_origin(definition: PlatformDefinition) -> str:
    """Return the configured scheme and authority without a page path."""
    parsed = urlsplit(str(definition.base_url))
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}"


def browser_state_path(definition: PlatformDefinition) -> Path:
    """Return a project-local, platform-isolated storage-state path."""
    root = Path(__file__).resolve().parents[1]
    path = root / ".runtime" / "browser-state" / f"{definition.platform}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
