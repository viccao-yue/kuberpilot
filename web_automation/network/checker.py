"""Orchestrate URL policy, DNS, TCP, TLS and HTTP into one safe report."""

from time import perf_counter
from urllib.parse import urlsplit

from network.dns_checker import check_dns
from network.errors import ErrorCode
from network.http_checker import check_http
from network.models import ConnectivityReport
from network.tcp_checker import check_tcp
from network.tls_checker import check_tls, skipped_tls
from network.url_policy import TargetPolicyError, validate_registered_url
from platforms.loader import PlatformNotFoundError, PlatformRegistry


def _origin(url: str) -> str:
    parsed = urlsplit(url)
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}"


class ConnectivityChecker:
    def __init__(self, registry: PlatformRegistry):
        self.registry = registry

    async def check_platform(self, platform: str) -> ConnectivityReport:
        started = perf_counter()
        try:
            definition = self.registry.get(platform)
        except PlatformNotFoundError:
            return ConnectivityReport(
                platform=platform,
                display_name=platform,
                target_origin="not-disclosed",
                overall_ok=False,
                failed_stage="configuration",
                error_code=ErrorCode.PLATFORM_NOT_FOUND.value,
                message="The requested platform is not registered",
            )

        target_url = str(definition.base_url)
        target_origin = _origin(target_url)
        if not definition.enabled:
            return ConnectivityReport(
                platform=platform,
                display_name=definition.display_name,
                target_origin=target_origin,
                overall_ok=False,
                failed_stage="configuration",
                error_code=ErrorCode.PLATFORM_DISABLED.value,
                message="The requested platform is disabled by an administrator",
            )

        try:
            validate_registered_url(target_url)
        except TargetPolicyError as exc:
            return ConnectivityReport(
                platform=platform,
                display_name=definition.display_name,
                target_origin=target_origin,
                overall_ok=False,
                failed_stage="url_policy",
                error_code=exc.code.value,
                message=str(exc),
            )

        parsed = urlsplit(target_url)
        host = parsed.hostname or ""
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        dns = await check_dns(host, definition.allowed_resolved_cidrs)
        if not dns.success:
            return self._failed(definition, target_origin, started, "dns", dns.error_code, dns=dns)

        tcp = await check_tcp(host, port, definition.timeout_seconds)
        if not tcp.success:
            return self._failed(
                definition,
                target_origin,
                started,
                "tcp",
                tcp.error_code,
                dns=dns,
                tcp=tcp,
            )

        tls = (
            await check_tls(
                host,
                port,
                definition.timeout_seconds,
                definition.ca_cert_path,
            )
            if parsed.scheme == "https"
            else skipped_tls()
        )
        if not tls.success:
            return self._failed(
                definition,
                target_origin,
                started,
                "tls",
                tls.error_code,
                dns=dns,
                tcp=tcp,
                tls=tls,
            )

        http = await check_http(
            target_url,
            definition.timeout_seconds,
            definition.proxy_url,
            definition.ca_cert_path,
            definition.expected_login_path,
        )
        if not http.success:
            return self._failed(
                definition,
                target_origin,
                started,
                "http",
                http.error_code,
                dns=dns,
                tcp=tcp,
                tls=tls,
                http=http,
            )

        return ConnectivityReport(
            platform=platform,
            display_name=definition.display_name,
            target_origin=target_origin,
            overall_ok=True,
            total_duration_ms=(perf_counter() - started) * 1000,
            message="All configured connectivity checks passed",
            dns=dns,
            tcp=tcp,
            tls=tls,
            http=http,
        )

    @staticmethod
    def _failed(
        definition,
        target_origin: str,
        started: float,
        stage: str,
        error_code: str | None,
        **results,
    ) -> ConnectivityReport:
        result = results.get(stage)
        return ConnectivityReport(
            platform=definition.platform,
            display_name=definition.display_name,
            target_origin=target_origin,
            overall_ok=False,
            total_duration_ms=(perf_counter() - started) * 1000,
            failed_stage=stage,
            error_code=error_code,
            message=result.message if result else f"Connectivity check failed at {stage}",
            **results,
        )
