"""DNS resolution with duration measurement and address allowlist enforcement."""

import asyncio
import socket
from time import perf_counter

from network.errors import ErrorCode
from network.models import DNSResult
from network.url_policy import TargetPolicyError, validate_resolved_addresses


async def check_dns(hostname: str, allowed_cidrs: list[str]) -> DNSResult:
    started = perf_counter()
    try:
        loop = asyncio.get_running_loop()
        records = await loop.getaddrinfo(
            hostname,
            None,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
        addresses = sorted({record[4][0] for record in records})
        validate_resolved_addresses(addresses, allowed_cidrs)
        return DNSResult(
            success=True,
            duration_ms=(perf_counter() - started) * 1000,
            hostname=hostname,
            addresses=addresses,
            message=f"Resolved {hostname} to {len(addresses)} allowed address(es)",
        )
    except TargetPolicyError as exc:
        return DNSResult(
            success=False,
            duration_ms=(perf_counter() - started) * 1000,
            hostname=hostname,
            addresses=locals().get("addresses", []),
            error_code=exc.code.value,
            message=str(exc),
        )
    except (socket.gaierror, OSError) as exc:
        return DNSResult(
            success=False,
            duration_ms=(perf_counter() - started) * 1000,
            hostname=hostname,
            error_code=ErrorCode.DNS_RESOLUTION_FAILED.value,
            message=f"DNS resolution failed: {type(exc).__name__}",
        )
