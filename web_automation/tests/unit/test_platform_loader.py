from pathlib import Path

import pytest

from platforms.loader import PlatformNotFoundError, PlatformRegistry


def test_loads_platform_yaml(tmp_path: Path):
    definitions = tmp_path / "definitions"
    definitions.mkdir()
    (definitions / "demo.yaml").write_text(
        """
platform: demo_platform
display_name: Demo
base_url: https://demo.example/login
enabled: true
allowed_resolved_cidrs: []
""".strip(),
        encoding="utf-8",
    )
    registry = PlatformRegistry(definitions, tmp_path)
    registry.load()
    assert registry.get("demo_platform").display_name == "Demo"


def test_loads_administrator_controlled_adapter_options(tmp_path: Path):
    definitions = tmp_path / "definitions"
    definitions.mkdir()
    (definitions / "kubercon.yaml").write_text(
        """
platform: kubercon_test
display_name: KuberCon test
base_url: http://127.0.0.1:30880/login
adapter: kubercon
adapter_options:
  cluster: test-cluster
  include_builtin: true
""".strip(),
        encoding="utf-8",
    )
    registry = PlatformRegistry(definitions, tmp_path)

    registry.load()

    item = registry.get("kubercon_test")
    assert item.adapter_options == {
        "cluster": "test-cluster",
        "include_builtin": True,
    }


def test_unknown_platform_is_rejected(tmp_path: Path):
    definitions = tmp_path / "definitions"
    definitions.mkdir()
    registry = PlatformRegistry(definitions, tmp_path)
    registry.load()
    with pytest.raises(PlatformNotFoundError):
        registry.get("unknown")


def test_ca_path_cannot_escape_project(tmp_path: Path):
    definitions = tmp_path / "definitions"
    definitions.mkdir()
    (definitions / "bad.yaml").write_text(
        """
platform: bad_platform
display_name: Bad
base_url: https://bad.example/login
ca_cert_path: ../outside.crt
""".strip(),
        encoding="utf-8",
    )
    registry = PlatformRegistry(definitions, tmp_path)
    with pytest.raises(ValueError, match="escapes project"):
        registry.load()
