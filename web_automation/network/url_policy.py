"""SSRF-resistant validation for administrator-registered target URLs."""

from ipaddress import ip_address, ip_network
from urllib.parse import urlsplit

from network.errors import ErrorCode


METADATA_HOSTS = {"169.254.169.254", "metadata.google.internal"}


class TargetPolicyError(ValueError):
    def __init__(self, code: ErrorCode, message: str):
        super().__init__(message)
        self.code = code


def validate_registered_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise TargetPolicyError(ErrorCode.INVALID_TARGET, "Target must be an HTTP(S) URL")
    if parsed.username or parsed.password:
        raise TargetPolicyError(
            ErrorCode.INVALID_TARGET,
            "Credentials must not be embedded in the target URL",
        )
    if parsed.hostname.lower() in METADATA_HOSTS:
        raise TargetPolicyError(ErrorCode.TARGET_NOT_ALLOWED, "Metadata endpoints are forbidden")


def validate_resolved_addresses(addresses: list[str], allowed_cidrs: list[str]) -> None:
    if not addresses:
        raise TargetPolicyError(ErrorCode.DNS_RESOLUTION_FAILED, "No address was resolved")

    networks = [ip_network(item, strict=False) for item in allowed_cidrs]
    for raw in addresses:
        address = ip_address(raw)
        if address.is_unspecified or address.is_multicast or address.is_link_local:
            raise TargetPolicyError(
                ErrorCode.TARGET_NOT_ALLOWED,
                f"Resolved address is not allowed: {address}",
            )
        if str(address) == "169.254.169.254":
            raise TargetPolicyError(
                ErrorCode.TARGET_NOT_ALLOWED,
                "Cloud metadata endpoint is forbidden",
            )
        if networks and not any(address in network for network in networks):
            raise TargetPolicyError(
                ErrorCode.TARGET_NOT_ALLOWED,
                f"Resolved address is outside the configured network allowlist: {address}",
            )
