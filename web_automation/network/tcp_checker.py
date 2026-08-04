"""Single-port TCP reachability check; this is not a port scanner."""

import asyncio
from time import perf_counter

from network.errors import ErrorCode
from network.models import TCPResult


async def check_tcp(host: str, port: int, timeout_seconds: float) -> TCPResult:
    started = perf_counter()
    writer = None
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout_seconds,
        )
        return TCPResult(
            success=True,
            duration_ms=(perf_counter() - started) * 1000,
            host=host,
            port=port,
            message=f"TCP connection to configured port {port} succeeded",
        )
    except asyncio.TimeoutError:
        return TCPResult(
            success=False,
            duration_ms=(perf_counter() - started) * 1000,
            host=host,
            port=port,
            error_code=ErrorCode.TCP_TIMEOUT.value,
            message=f"TCP connection timed out after {timeout_seconds:g} seconds",
        )
    except ConnectionRefusedError:
        return TCPResult(
            success=False,
            duration_ms=(perf_counter() - started) * 1000,
            host=host,
            port=port,
            error_code=ErrorCode.TCP_CONNECTION_REFUSED.value,
            message="The configured target port refused the connection",
        )
    except OSError as exc:
        return TCPResult(
            success=False,
            duration_ms=(perf_counter() - started) * 1000,
            host=host,
            port=port,
            error_code=ErrorCode.TCP_CONNECTION_FAILED.value,
            message=f"TCP connection failed: {type(exc).__name__}",
        )
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()
