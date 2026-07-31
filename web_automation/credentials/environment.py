"""Resolve a credential id from process environment without logging secret values."""

import os
import re

from credentials.models import Credential


class CredentialUnavailableError(RuntimeError):
    pass


def _prefix(credential_id: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", credential_id).strip("_").upper()
    return f"CREDENTIAL_{normalized}"


class EnvironmentCredentialProvider:
    def resolve(self, credential_id: str) -> Credential:
        prefix = _prefix(credential_id)
        username = os.environ.get(f"{prefix}_USERNAME", "")
        password = os.environ.get(f"{prefix}_PASSWORD", "")
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
