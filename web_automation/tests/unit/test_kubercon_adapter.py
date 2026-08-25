from pathlib import Path

import pytest

from adapters.kubercon import KuberConAdapter
from platforms.models import PlatformDefinition


def _adapter(**adapter_options) -> KuberConAdapter:
    definition = PlatformDefinition(
        platform="kubercon_test",
        display_name="KuberCon test platform",
        base_url="http://127.0.0.1:30880/login",
        adapter="kubercon",
        adapter_options={"cluster": "test-cluster", **adapter_options},
        source_file=Path("kubercon-test.yaml"),
    )
    return KuberConAdapter(definition)


def _alarm(**overrides):
    item = {
        "activeAt": "2026-08-20T08:49:47.115216326Z",
        "annotations": {
            "summary": "Pod has been unavailable.",
            "description": "A test workload has been unavailable for 15 minutes.",
        },
        "labels": {
            "alertname": "TestPodUnavailable",
            "namespace": "demo-space",
            "pod": "demo-pod-1",
            "rule_group": "test-workloads",
            "rule_id": "rule-test-1",
            "rule_level": "global",
            "severity": "warning",
        },
        "state": "firing",
        "value": "1e+00",
        "_source": "builtin",
    }
    item.update(overrides)
    return item


def test_kubercon_urls_use_registered_cluster_and_rewritten_api_path():
    adapter = _adapter()

    assert adapter.alarm_page_url == (
        "http://127.0.0.1:30880/clusters/test-cluster/alerts"
    )
    assert adapter.alarm_api_url() == (
        "http://127.0.0.1:30880/kapis/clusters/test-cluster/"
        "alerting.kubercloud.com/v2beta1/clusteralerts"
    )
    assert adapter.alarm_api_url(builtin=True).endswith("/globalalerts")


@pytest.mark.parametrize("cluster", ["../admin", "bad/name", "UPPER_CASE", ""])
def test_kubercon_rejects_invalid_cluster_option(cluster):
    adapter = _adapter(cluster=cluster)

    with pytest.raises(ValueError, match="cluster option is invalid"):
        _ = adapter.cluster


def test_kubercon_alarm_is_normalized_without_copying_sensitive_labels():
    adapter = _adapter()

    alarm = adapter._to_standard(_alarm())

    assert alarm.severity == "warning"
    assert alarm.status == "firing"
    assert alarm.resource_type == "pod"
    assert alarm.resource_name == "demo-pod-1"
    assert alarm.resource_id == (
        "kubercon_test::test-cluster::demo-space::pod::demo-pod-1"
    )
    assert alarm.title == "Pod has been unavailable."
    assert alarm.occurred_at.isoformat().startswith("2026-08-20T08:49:47.115216")
    assert alarm.raw_data["source_rule_id"] == "rule-test-1"
    assert "labels" not in alarm.raw_data


def test_kubercon_alarm_id_distinguishes_a_new_firing_lifecycle():
    adapter = _adapter()

    first = adapter._to_standard(_alarm())
    repeated = adapter._to_standard(_alarm())
    fired_again = adapter._to_standard(_alarm(activeAt="2026-08-21T09:00:00Z"))

    assert repeated.alarm_id == first.alarm_id
    assert fired_again.alarm_id != first.alarm_id


def test_kubercon_alarm_id_distinguishes_rules_with_missing_rule_ids():
    adapter = _adapter()
    base_labels = {
        "pod": "demo-pod-1",
        "severity": "warning",
    }

    first = adapter._to_standard(
        _alarm(labels={**base_labels, "alertname": "PodUnavailable"})
    )
    second = adapter._to_standard(
        _alarm(labels={**base_labels, "alertname": "PodRestarting"})
    )

    assert second.alarm_id != first.alarm_id


def test_kubercon_message_and_cluster_fallbacks_are_supported():
    adapter = _adapter()
    alarm = adapter._to_standard(
        _alarm(
            annotations={"message": "CPU usage is high."},
            labels={
                "alertname": "CpuHigh",
                "rule_id": "rule-test-2",
                "severity": "unexpected",
            },
        )
    )

    assert alarm.severity == "info"
    assert alarm.resource_type == "cluster"
    assert alarm.resource_name == "test-cluster"
    assert alarm.title == "CpuHigh"
    assert alarm.description == "CPU usage is high."


class _FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
        self.ok = 200 <= status < 300

    async def json(self):
        return self.payload


class _FakeRequest:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    async def get(self, url, params):
        self.calls.append((url, params))
        return self.responses.pop(0)


class _FakeContext:
    def __init__(self, responses):
        self.request = _FakeRequest(responses)


async def test_kubercon_fetches_custom_and_builtin_alarm_collections():
    adapter = _adapter()
    context = _FakeContext(
        [
            _FakeResponse({"items": [_alarm(_source="ignored")]}),
            _FakeResponse({"items": [_alarm(_source="ignored")]}),
        ]
    )

    items = await adapter._fetch_alarm_items(context, limit=7, severity="warning")

    assert [item["_source"] for item in items] == ["custom", "builtin"]
    assert len(context.request.calls) == 2
    assert context.request.calls[0][1]["limit"] == 7
    assert context.request.calls[0][1]["label_filters"] == "severity=warning"
    assert context.request.calls[1][1]["builtin"] == "true"


async def test_kubercon_expired_session_requests_reauthentication():
    adapter = _adapter()
    context = _FakeContext([_FakeResponse({}, status=401)])

    with pytest.raises(PermissionError, match="not authenticated"):
        await adapter._fetch_alarm_items(context, limit=10)


async def test_kubercon_api_error_does_not_include_response_content():
    adapter = _adapter()
    context = _FakeContext([_FakeResponse({"secret": "must-not-leak"}, status=500)])

    with pytest.raises(RuntimeError, match="returned status 500") as exc_info:
        await adapter._fetch_alarm_items(context, limit=10)

    assert "must-not-leak" not in str(exc_info.value)


@pytest.mark.parametrize("payload", [[], {"items": "not-a-list"}])
async def test_kubercon_rejects_invalid_alarm_response_schema(payload):
    adapter = _adapter(include_builtin=False)
    context = _FakeContext([_FakeResponse(payload)])

    with pytest.raises(RuntimeError, match="invalid response schema"):
        await adapter._fetch_alarm_items(context, limit=10)
