"""Run a sanitized, read-only smoke check through the KuberCon MCP tool path."""

import argparse
import asyncio
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from credentials.environment import EnvironmentCredentialProvider
from gateway.config import PROJECT_DIR, Settings
from gateway.mcp.alarm_tool import call_alarm_tool
from network.checker import ConnectivityChecker
from platforms.loader import PlatformRegistry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--severity",
        choices=("all", "critical", "warning", "info"),
        default="all",
    )
    parser.add_argument("--limit", type=int, choices=range(1, 51), default=20)
    return parser.parse_args()


async def verify(severity: str, limit: int) -> int:
    settings = Settings()
    registry = PlatformRegistry(settings.platform_definition_dir, PROJECT_DIR)
    registry.load()
    result = await call_alarm_tool(
        {"platform": "kubercon", "severity": severity, "limit": limit},
        registry,
        ConnectivityChecker(registry),
        EnvironmentCredentialProvider(),
    )
    payload = result.get("structuredContent", {})
    summary = {
        "is_error": result.get("isError", True),
        "ok": payload.get("ok", False),
        "platform": payload.get("platform", "kubercon"),
        "count": payload.get("count", 0),
        "severity_counts": payload.get("severity_counts", {}),
        "collection_method": payload.get("collection_method"),
        "read_only": payload.get("read_only"),
        "error_code": payload.get("error_code"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok") and not result.get("isError") else 1


def main() -> int:
    args = parse_args()
    return asyncio.run(verify(args.severity, args.limit))


if __name__ == "__main__":
    raise SystemExit(main())
