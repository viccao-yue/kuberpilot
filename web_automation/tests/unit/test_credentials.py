import pytest

from credentials.environment import (
    CredentialUnavailableError,
    EnvironmentCredentialProvider,
)


def test_environment_provider_resolves_secret_without_exposing_it(monkeypatch):
    monkeypatch.setenv("CREDENTIAL_DEMO_READONLY_USERNAME", "robot")
    monkeypatch.setenv("CREDENTIAL_DEMO_READONLY_PASSWORD", "local-secret")
    credential = EnvironmentCredentialProvider().resolve("demo-readonly")
    assert credential.username == "robot"
    assert credential.password.get_secret_value() == "local-secret"
    assert "local-secret" not in repr(credential)


def test_missing_credential_is_rejected(monkeypatch):
    monkeypatch.delenv("CREDENTIAL_MISSING_USERNAME", raising=False)
    monkeypatch.delenv("CREDENTIAL_MISSING_PASSWORD", raising=False)
    with pytest.raises(CredentialUnavailableError):
        EnvironmentCredentialProvider().resolve("missing")
