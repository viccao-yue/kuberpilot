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
