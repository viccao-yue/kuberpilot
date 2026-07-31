"""HTTP reachability check without downloading or logging the response body."""

from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit

import httpx

from network.errors import ErrorCode
from network.models import HTTPResult


def _origin(url: str) -> str:
    parsed = urlsplit(url)
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}"


async def check_http(
    url: str,
    timeout_seconds: float,
    proxy_url: str | None,
    ca_cert_path: str | None,
    expected_login_path: str | None,
) -> HTTPResult:
    started = perf_counter()
    verify: bool | str = str(Path(ca_cert_path)) if ca_cert_path else True
    try:
        async with httpx.AsyncClient(
            verify=verify,
            proxy=proxy_url,
            timeout=timeout_seconds,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": "KuberPilot-WebAutomation-Preflight/0.1"},
        ) as client:
            response = await client.get(url)
        location = response.headers.get("location")
        status_ok = response.status_code < 500
        login_reached = (
            expected_login_path in urlsplit(str(response.url)).path
            if expected_login_path
            else None
        )
        message = f"HTTP endpoint responded with status {response.status_code}"
        if location:
            message += " and a redirect (redirect target not followed during preflight)"
        return HTTPResult(
            success=status_ok,
            duration_ms=(perf_counter() - started) * 1000,
            status_code=response.status_code,
            final_origin=_origin(str(response.url)),
            content_type=response.headers.get("content-type"),
            login_page_reached=login_reached,
            error_code=None if status_ok else ErrorCode.HTTP_REQUEST_FAILED.value,
            message=message,
        )
    except httpx.ProxyError:
        code = ErrorCode.PROXY_CONNECTION_FAILED
        message = "The configured proxy could not connect to the target"
    except httpx.TimeoutException:
        code = ErrorCode.HTTP_REQUEST_FAILED
        message = f"HTTP request timed out after {timeout_seconds:g} seconds"
    except httpx.HTTPError as exc:
        code = ErrorCode.HTTP_REQUEST_FAILED
        message = f"HTTP request failed: {type(exc).__name__}"

    return HTTPResult(
        success=False,
        duration_ms=(perf_counter() - started) * 1000,
        error_code=code.value,
        message=message,
    )
