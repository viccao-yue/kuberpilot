"""FastAPI entry point for the Web Automation Gateway."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.requests import Request

from gateway.dependencies import get_collection_scheduler, get_settings, get_task_manager
from gateway.mcp.router import router as mcp_router
from gateway.routes.health import router as health_router
from gateway.routes.tasks import router as task_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scheduler = get_collection_scheduler()
    if get_settings().scheduler_enabled:
        scheduler.start()
    try:
        yield
    finally:
        scheduler.shutdown()
        await get_task_manager().drain()


app = FastAPI(
    title="KuberPilot Web Automation Gateway",
    version="0.3.0",
    description="Read-only platform collection, scheduling, alert callbacks and MCP tools.",
    lifespan=lifespan,
)
app.include_router(health_router)
app.include_router(mcp_router)
app.include_router(task_router)


@app.middleware("http")
async def declare_json_utf8(request: Request, call_next):
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if content_type == "application/json":
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response
