import pytest

from network.errors import ErrorCode
from network.url_policy import (
    TargetPolicyError,
    validate_registered_url,
    validate_resolved_addresses,
)


def test_accepts_registered_http_url():
    validate_registered_url("https://platform.example/login")


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "ftp://platform.example/file",
        "https://user:password@platform.example/login",
        "http://169.254.169.254/latest/meta-data",
    ],
)
def test_rejects_unsafe_url(url):
    with pytest.raises(TargetPolicyError):
        validate_registered_url(url)


def test_rejects_address_outside_allowlist():
    with pytest.raises(TargetPolicyError) as captured:
        validate_resolved_addresses(["203.0.113.8"], ["10.0.0.0/8"])
    assert captured.value.code == ErrorCode.TARGET_NOT_ALLOWED


def test_accepts_address_inside_allowlist():
    validate_resolved_addresses(["10.10.2.8"], ["10.0.0.0/8"])
