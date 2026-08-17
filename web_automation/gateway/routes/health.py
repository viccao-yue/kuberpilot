"""Human/operator-facing health and connectivity endpoints."""

from fastapi import APIRouter, Depends

from gateway.config import Settings
from gateway.delivery.worker import DeliveryWorker
from gateway.dependencies import get_checker, get_delivery_worker, get_settings
from network.checker import ConnectivityChecker
from network.models import ConnectivityReport


router = APIRouter()


@router.get("/healthz")
async def healthz(
    delivery_worker: DeliveryWorker = Depends(get_delivery_worker),
    settings: Settings = Depends(get_settings),
) -> dict:
    delivery_enabled = settings.callback_enabled and bool(settings.callback_token)
    delivery_health = delivery_worker.health()
    delivery_ready = not delivery_enabled or (
        delivery_health["is_running"]
        and delivery_health["queue_error_type"] is None
    )
    return {
        "status": "ok" if delivery_ready else "degraded",
        "service": "web-automation-gateway",
        "version": "0.4.0",
        "delivery_worker": {
            "enabled": delivery_enabled,
            **delivery_health,
        },
    }


@router.post(
    "/api/v1/platforms/{platform}/connectivity-check",
    response_model=ConnectivityReport,
)
async def connectivity_check(
    platform: str,
    checker: ConnectivityChecker = Depends(get_checker),
) -> ConnectivityReport:
    return await checker.check_platform(platform)
