from network.tls_checker import check_tls, skipped_tls


def test_http_tls_stage_is_explicitly_skipped():
    result = skipped_tls()
    assert result.success
    assert not result.enabled
    assert not result.attempted


async def test_missing_ca_file_returns_safe_failure(tmp_path):
    result = await check_tls(
        "127.0.0.1",
        443,
        0.1,
        str(tmp_path / "missing-ca.crt"),
    )
    assert not result.success
    assert result.error_code == "TLS_HANDSHAKE_FAILED"
    assert "missing-ca.crt" not in result.message
