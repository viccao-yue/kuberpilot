import httpx
import respx

from network.http_checker import check_http


@respx.mock
async def test_http_200_is_reachable():
    respx.get("https://platform.example/login").mock(
        return_value=httpx.Response(200, headers={"content-type": "text/html"})
    )
    result = await check_http(
        "https://platform.example/login",
        timeout_seconds=1,
        proxy_url=None,
        ca_cert_path=None,
        expected_login_path="/login",
    )
    assert result.success
    assert result.status_code == 200
    assert result.login_page_reached


@respx.mock
async def test_http_401_means_network_is_reachable():
    respx.get("https://platform.example/login").mock(return_value=httpx.Response(401))
    result = await check_http(
        "https://platform.example/login", 1, None, None, "/login"
    )
    assert result.success
    assert result.status_code == 401


@respx.mock
async def test_http_503_is_failure():
    respx.get("https://platform.example/login").mock(return_value=httpx.Response(503))
    result = await check_http(
        "https://platform.example/login", 1, None, None, "/login"
    )
    assert not result.success
    assert result.error_code == "HTTP_REQUEST_FAILED"
