"""Serializable results for each network layer and the combined report."""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class StageResult(BaseModel):
    attempted: bool = True
    success: bool
    duration_ms: float = Field(default=0, ge=0)
    error_code: str | None = None
    message: str


class DNSResult(StageResult):
    hostname: str
    addresses: list[str] = Field(default_factory=list)


class TCPResult(StageResult):
    host: str
    port: int


class TLSResult(StageResult):
    enabled: bool
    protocol: str | None = None
    subject: str | None = None
    issuer: str | None = None
    valid_until: str | None = None
    days_until_expiry: int | None = None


class HTTPResult(StageResult):
    status_code: int | None = None
    final_origin: str | None = None
    content_type: str | None = None
    login_page_reached: bool | None = None


class ConnectivityReport(BaseModel):
    platform: str
    display_name: str
    target_origin: str
    overall_ok: bool
    checked_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_duration_ms: float = Field(default=0, ge=0)
    failed_stage: str | None = None
    error_code: str | None = None
    message: str
    dns: DNSResult | None = None
    tcp: TCPResult | None = None
    tls: TLSResult | None = None
    http: HTTPResult | None = None
