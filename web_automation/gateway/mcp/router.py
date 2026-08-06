"""Minimal MCP Streamable HTTP JSON-RPC endpoint used by KuberPilot."""

from typing import Any

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from credentials.environment import EnvironmentCredentialProvider
from gateway.dependencies import (
    get_checker,
    get_credential_provider,
    get_registry,
)
from gateway.mcp.alarm_tool import (
    TOOL_DEFINITION as ALARM_TOOL_DEFINITION,
    TOOL_NAME as ALARM_TOOL_NAME,
    call_alarm_tool,
)
from gateway.mcp.health_tool import TOOL_DEFINITION, TOOL_NAME, call_health_tool
from network.checker import ConnectivityChecker
from platforms.loader import PlatformRegistry


router = APIRouter()
PROTOCOL_VERSION = "2025-03-26"


class JSONRPCRequest(BaseModel):
    jsonrpc: str
    id: str | int | None = None
    method: str
    params: dict[str, Any] = Field(default_factory=dict)


def _result(request_id, result: dict) -> JSONResponse:
    return JSONResponse({"jsonrpc": "2.0", "id": request_id, "result": result})


def _error(request_id, code: int, message: str) -> JSONResponse:
    return JSONResponse(
        {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
    )


@router.post("/mcp")
async def mcp_endpoint(
    request: JSONRPCRequest,
    checker: ConnectivityChecker = Depends(get_checker),
    registry: PlatformRegistry = Depends(get_registry),
    credential_provider: EnvironmentCredentialProvider = Depends(get_credential_provider),
):
    if request.method == "notifications/initialized":
        return Response(status_code=202)
    if request.id is None:
        return Response(status_code=202)
    if request.method == "initialize":
        return _result(
            request.id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "kuberpilot-web-automation", "version": "0.3.0"},
            },
        )
    if request.method == "tools/list":
        return _result(request.id, {"tools": [TOOL_DEFINITION, ALARM_TOOL_DEFINITION]})
    if request.method == "tools/call":
        name = request.params.get("name")
        arguments = request.params.get("arguments") or {}
        if name == TOOL_NAME:
            result = await call_health_tool(arguments, checker)
        elif name == ALARM_TOOL_NAME:
            result = await call_alarm_tool(
                arguments,
                registry,
                checker,
                credential_provider,
            )
        else:
            return _error(request.id, -32602, f"Unknown tool: {name}")
        return _result(request.id, result)
    return _error(request.id, -32601, f"Method not found: {request.method}")


@router.delete("/mcp")
async def close_mcp_session():
    return Response(status_code=204)
