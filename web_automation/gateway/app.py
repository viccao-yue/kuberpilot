"""FastAPI entry point for task 1."""

from fastapi import FastAPI

from gateway.mcp.router import router as mcp_router
from gateway.routes.health import router as health_router


app = FastAPI(
    title="KuberPilot Web Automation Gateway",
    version="0.1.0",
    description="Read-only platform connectivity preflight and MCP tool.",
)
app.include_router(health_router)
app.include_router(mcp_router)
