"""Resolve a credential id from process environment without logging secret values."""

import os
import re
from pathlib import Path

from dotenv import dotenv_values

from credentials.models import Credential


class CredentialUnavailableError(RuntimeError):
    pass


def _prefix(credential_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", credential_id).strip("_").upper()
    return f"CREDENTIAL_{normalized}"


class EnvironmentCredentialProvider:
    def __init__(self, env_file: Path | None = None):
        project_env = Path(__file__).resolve().parents[1] / ".env"
        self.file_values = dotenv_values(env_file or project_env)

    def resolve(self, credential_id: str) -> Credential:
        prefix = _prefix(credential_id)
        username_key = f"{prefix}_USERNAME"
        password_key = f"{prefix}_PASSWORD"
        username = (
            os.environ.get(username_key) or self.file_values.get(username_key) or ""
        )
        password = (
            os.environ.get(password_key) or self.file_values.get(password_key) or ""
        )
        local_defaults = {
            "mock-platform-readonly": ("aiops_robot", "MockOnly@123456"),
            "legacy-ops-readonly": ("legacy_reader", "LegacyOnly@123456"),
        }
        if (
            not username
            and not password
            and credential_id in local_defaults
            and os.environ.get("WEB_AUTOMATION_ALLOW_MOCK_DEFAULT_CREDENTIALS") == "1"
        ):
            username, password = local_defaults[credential_id]
        if not username or not password:
            raise CredentialUnavailableError(
                f"Credential '{credential_id}' is not available in the configured provider"
            )
        return Credential(username=username, password=password)
