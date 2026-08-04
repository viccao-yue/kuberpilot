import asyncio

from network.tcp_checker import check_tcp


async def test_tcp_reaches_local_server():
    server = await asyncio.start_server(lambda reader, writer: writer.close(), "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        result = await check_tcp("127.0.0.1", port, 1)
        assert result.success
    finally:
        server.close()
        await server.wait_closed()


async def test_tcp_reports_refused_port():
    server = await asyncio.start_server(lambda reader, writer: writer.close(), "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    server.close()
    await server.wait_closed()
    result = await check_tcp("127.0.0.1", port, 1)
    assert not result.success
    # Windows can silently drop a just-closed ephemeral port, producing a timeout
    # instead of an immediate connection-refused response.
    assert result.error_code in {
        "TCP_CONNECTION_REFUSED",
        "TCP_CONNECTION_FAILED",
        "TCP_TIMEOUT",
    }
