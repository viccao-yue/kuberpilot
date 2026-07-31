from pathlib import Path

import network.checker as checker_module
from network.checker import ConnectivityChecker
from network.models import DNSResult, HTTPResult, TCPResult, TLSResult
from platforms.loader import PlatformRegistry


def make_registry(tmp_path: Path) -> PlatformRegistry:
    definitions = tmp_path / "definitions"
    definitions.mkdir()
    (definitions / "demo.yaml").write_text(
        """
platform: demo_platform
display_name: Demo
base_url: https://demo.example/login
enabled: true
expected_login_path: /login
allowed_resolved_cidrs: []
""".strip(),
        encoding="utf-8",
    )
    registry = PlatformRegistry(definitions, tmp_path)
    registry.load()
    return registry


async def test_full_connectivity_success(monkeypatch, tmp_path):
    async def dns(*args):
        return DNSResult(
            success=True, hostname="demo.example", addresses=["10.0.0.8"], message="ok"
        )

    async def tcp(*args):
        return TCPResult(success=True, host="demo.example", port=443, message="ok")

    async def tls(*args):
        return TLSResult(success=True, enabled=True, message="ok")

    async def http(*args):
        return HTTPResult(success=True, status_code=200, message="ok")

    monkeypatch.setattr(checker_module, "check_dns", dns)
    monkeypatch.setattr(checker_module, "check_tcp", tcp)
    monkeypatch.setattr(checker_module, "check_tls", tls)
    monkeypatch.setattr(checker_module, "check_http", http)

    report = await ConnectivityChecker(make_registry(tmp_path)).check_platform("demo_platform")
    assert report.overall_ok
    assert report.failed_stage is None
    assert report.target_origin == "https://demo.example"


async def test_dns_failure_stops_later_checks(monkeypatch, tmp_path):
    called = {"tcp": False}

    async def dns(*args):
        return DNSResult(
            success=False,
            hostname="demo.example",
            error_code="DNS_RESOLUTION_FAILED",
            message="dns failed",
        )

    async def tcp(*args):
        called["tcp"] = True

    monkeypatch.setattr(checker_module, "check_dns", dns)
    monkeypatch.setattr(checker_module, "check_tcp", tcp)

    report = await ConnectivityChecker(make_registry(tmp_path)).check_platform("demo_platform")
    assert not report.overall_ok
    assert report.failed_stage == "dns"
    assert not called["tcp"]


async def test_unknown_platform_does_not_disclose_url(tmp_path):
    report = await ConnectivityChecker(make_registry(tmp_path)).check_platform("unknown")
    assert report.error_code == "PLATFORM_NOT_FOUND"
    assert report.target_origin == "not-disclosed"
