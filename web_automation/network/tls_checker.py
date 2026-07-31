"""TLS handshake and certificate validation using the system or platform CA."""

import asyncio
import ssl
from datetime import datetime, timezone
from time import perf_counter

from network.errors import ErrorCode
from network.models import TLSResult


def _flatten_name(parts: tuple) -> str:
    return ", ".join(f"{key}={value}" for group in parts for key, value in group)


async def check_tls(
    host: str,
    port: int,
    timeout_seconds: float,
    ca_cert_path: str | None,
) -> TLSResult:
    started = perf_counter()
    writer = None
    try:
        context = ssl.create_default_context(cafile=ca_cert_path)
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(
                host,
                port,
                ssl=context,
                server_hostname=host,
            ),
            timeout=timeout_seconds,
        )
        ssl_object = writer.get_extra_info("ssl_object")
        certificate = ssl_object.getpeercert() if ssl_object else {}
        expires = certificate.get("notAfter")
        expiry = (
            datetime.fromtimestamp(ssl.cert_time_to_seconds(expires), tz=timezone.utc)
            if expires
            else None
        )
        days = (expiry - datetime.now(timezone.utc)).days if expiry else None
        return TLSResult(
            success=True,
            duration_ms=(perf_counter() - started) * 1000,
            enabled=True,
            protocol=ssl_object.version() if ssl_object else None,
            subject=_flatten_name(certificate.get("subject", ())) or None,
            issuer=_flatten_name(certificate.get("issuer", ())) or None,
            valid_until=expiry.isoformat() if expiry else None,
            days_until_expiry=days,
            message="TLS handshake and certificate validation succeeded",
        )
    except asyncio.TimeoutError:
        code = ErrorCode.TLS_HANDSHAKE_FAILED
        message = f"TLS handshake timed out after {timeout_seconds:g} seconds"
    except ssl.SSLCertVerificationError as exc:
        verify_message = (exc.verify_message or str(exc)).lower()
        if "expired" in verify_message:
            code = ErrorCode.TLS_CERTIFICATE_EXPIRED
        elif "hostname" in verify_message or "ip address mismatch" in verify_message:
            code = ErrorCode.TLS_HOSTNAME_MISMATCH
        else:
            code = ErrorCode.TLS_PRIVATE_CA_UNTRUSTED
        message = f"TLS certificate validation failed: {exc.verify_message or type(exc).__name__}"
    except (ssl.SSLError, OSError) as exc:
        code = ErrorCode.TLS_HANDSHAKE_FAILED
        message = f"TLS handshake failed: {type(exc).__name__}"
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()

    return TLSResult(
        success=False,
        duration_ms=(perf_counter() - started) * 1000,
        enabled=True,
        error_code=code.value,
        message=message,
    )


def skipped_tls() -> TLSResult:
    return TLSResult(
        attempted=False,
        success=True,
        enabled=False,
        message="TLS check skipped because the configured URL uses HTTP",
    )
