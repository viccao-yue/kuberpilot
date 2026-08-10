"""Human/operator-facing health and connectivity endpoints."""

from fastapi import APIRouter, Depends

from gateway.dependencies import get_checker
from network.checker import ConnectivityChecker
from network.models import ConnectivityReport


router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "service": "web-automation-gateway", "version": "0.4.0"}


@router.post(
    "/api/v1/platforms/{platform}/connectivity-check",
    response_model=ConnectivityReport,
)
async def connectivity_check(
    platform: str,
    checker: ConnectivityChecker = Depends(get_checker),
) -> ConnectivityReport:
    return await checker.check_platform(platform)
