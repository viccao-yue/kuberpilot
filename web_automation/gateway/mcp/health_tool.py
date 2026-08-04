"""MCP tool definition and execution for the read-only connectivity check."""

import json

from network.checker import ConnectivityChecker


TOOL_NAME = "web_platform.health"
TOOL_DEFINITION = {
    "name": TOOL_NAME,
    "description": (
        "Run a read-only network preflight for an administrator-registered platform. "
        "Checks URL policy, DNS, TCP, TLS and HTTP without accepting an arbitrary URL."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "platform": {
                "type": "string",
                "description": "Registered platform identifier, for example mock_platform",
                "pattern": "^[a-z][a-z0-9_-]{1,63}$",
            }
        },
        "required": ["platform"],
        "additionalProperties": False,
    },
}


async def call_health_tool(arguments: dict, checker: ConnectivityChecker) -> dict:
    if set(arguments) != {"platform"} or not isinstance(arguments.get("platform"), str):
        return {
            "isError": True,
            "content": [
                {
                    "type": "text",
                    "text": "Only one string argument named 'platform' is allowed.",
                }
            ],
        }
    report = await checker.check_platform(arguments["platform"])
    payload = report.model_dump(mode="json")
    return {
        "isError": not report.overall_ok,
        "structuredContent": payload,
        "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
    }
