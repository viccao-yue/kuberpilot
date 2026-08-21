from types import SimpleNamespace

from adapters.base import PlatformLoginError
from adapters.kubercon import KuberConAdapter
from adapters.registry import get_adapter
from credentials.models import Credential
from gateway.mcp import alarm_tool


def test_kubercon_adapter_is_registered_for_mcp_dispatch():
    assert get_adapter("kubercon") is KuberConAdapter


async def test_alarm_tool_returns_specific_login_error(monkeypatch):
    class RejectingAdapter:
        def __init__(self, definition):
            self.definition = definition

        async def list_alarms(self, credential, severity="all", limit=20):
            raise PlatformLoginError("sensitive platform detail")

    registry = SimpleNamespace(
        get=lambda platform: SimpleNamespace(
            credential_id="kubercon-readonly",
            adapter="kubercon",
        )
    )
    checker = SimpleNamespace(
        check_platform=lambda platform: None,
    )

    async def successful_check(platform):
        return SimpleNamespace(overall_ok=True)

    checker.check_platform = successful_check
    credential_provider = SimpleNamespace(
        resolve=lambda credential_id: Credential(username="reader", password="secret")
    )
    monkeypatch.setattr(alarm_tool, "get_adapter", lambda adapter: RejectingAdapter)

    result = await alarm_tool.call_alarm_tool(
        {"platform": "kubercon", "limit": 10},
        registry,
        checker,
        credential_provider,
    )

    assert result["isError"] is True
    assert result["structuredContent"]["error_code"] == "PLATFORM_LOGIN_FAILED"
    assert "sensitive platform detail" not in str(result)
