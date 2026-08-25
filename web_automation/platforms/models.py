"""Validated configuration controlled by an administrator, never by the model."""

from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl, field_validator


class PlatformDefinition(BaseModel):
    platform: str = Field(pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    display_name: str = Field(min_length=1, max_length=120)
    base_url: HttpUrl
    enabled: bool = True
    timeout_seconds: float = Field(default=10.0, ge=1.0, le=60.0)
    expected_login_path: str | None = None
    proxy_url: str | None = None
    ca_cert_path: str | None = None
    allowed_resolved_cidrs: list[str] = Field(default_factory=list)
    adapter: str = Field(default="network_only", pattern=r"^[a-z][a-z0-9_-]{1,63}$")
    adapter_options: dict[str, str | int | bool] = Field(default_factory=dict)
    credential_id: str | None = Field(
        default=None,
        pattern=r"^[a-z][a-z0-9_-]{1,63}$",
    )
    alarm_collection_interval_seconds: int | None = Field(default=None, ge=5, le=86400)
    source_file: Path | None = Field(default=None, exclude=True)

    @field_validator("proxy_url")
    @classmethod
    def validate_proxy_url(cls, value: str | None) -> str | None:
        if value and not value.startswith(("http://", "https://", "socks5://")):
            raise ValueError("proxy_url must use http, https or socks5")
        return value
