import socket

from network.dns_checker import check_dns


async def test_dns_resolves_localhost():
    result = await check_dns("localhost", ["127.0.0.0/8", "::1/128"])
    assert result.success
    assert result.addresses


async def test_dns_reports_unknown_name(monkeypatch):
    async def fail(*args, **kwargs):
        raise socket.gaierror("missing")

    loop = __import__("asyncio").get_running_loop()
    monkeypatch.setattr(loop, "getaddrinfo", fail)
    result = await check_dns("missing.invalid", [])
    assert not result.success
    assert result.error_code == "DNS_RESOLUTION_FAILED"
