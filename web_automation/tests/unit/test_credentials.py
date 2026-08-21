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


def test_environment_provider_reads_project_local_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CREDENTIAL_REAL_PLATFORM_USERNAME=reader\n"
        "CREDENTIAL_REAL_PLATFORM_PASSWORD=file-secret\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("CREDENTIAL_REAL_PLATFORM_USERNAME", raising=False)
    monkeypatch.delenv("CREDENTIAL_REAL_PLATFORM_PASSWORD", raising=False)

    credential = EnvironmentCredentialProvider(env_file).resolve("real-platform")

    assert credential.username == "reader"
    assert credential.password.get_secret_value() == "file-secret"


def test_process_environment_overrides_project_local_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CREDENTIAL_REAL_PLATFORM_USERNAME=file-user\n"
        "CREDENTIAL_REAL_PLATFORM_PASSWORD=file-secret\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("CREDENTIAL_REAL_PLATFORM_USERNAME", "process-user")
    monkeypatch.setenv("CREDENTIAL_REAL_PLATFORM_PASSWORD", "process-secret")

    credential = EnvironmentCredentialProvider(env_file).resolve("real-platform")

    assert credential.username == "process-user"
    assert credential.password.get_secret_value() == "process-secret"


def test_environment_provider_reads_quoted_special_characters(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "CREDENTIAL_REAL_PLATFORM_USERNAME='reader user'\n"
        "CREDENTIAL_REAL_PLATFORM_PASSWORD='secret #1\\'s path\\\\value'\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("CREDENTIAL_REAL_PLATFORM_USERNAME", raising=False)
    monkeypatch.delenv("CREDENTIAL_REAL_PLATFORM_PASSWORD", raising=False)

    credential = EnvironmentCredentialProvider(env_file).resolve("real-platform")

    assert credential.username == "reader user"
    assert credential.password.get_secret_value() == "secret #1's path\\value"
