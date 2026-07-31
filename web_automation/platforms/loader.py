"""Load platform definitions from a fixed project directory."""

from pathlib import Path

import yaml

from platforms.models import PlatformDefinition


class PlatformNotFoundError(KeyError):
    """The requested administrator-owned platform definition does not exist."""


class PlatformRegistry:
    def __init__(self, definition_dir: Path, project_dir: Path):
        self.definition_dir = definition_dir.resolve()
        self.project_dir = project_dir.resolve()
        self._items: dict[str, PlatformDefinition] = {}

    def load(self) -> None:
        items: dict[str, PlatformDefinition] = {}
        if not self.definition_dir.is_dir():
            raise FileNotFoundError(f"Platform definition directory not found: {self.definition_dir}")
        for path in sorted(self.definition_dir.glob("*.yaml")):
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            item = PlatformDefinition.model_validate(raw)
            if item.platform in items:
                raise ValueError(f"Duplicate platform id: {item.platform}")
            item.source_file = path
            if item.ca_cert_path:
                cert_path = (self.project_dir / item.ca_cert_path).resolve()
                if not cert_path.is_relative_to(self.project_dir):
                    raise ValueError(f"CA path escapes project directory: {item.ca_cert_path}")
                item.ca_cert_path = str(cert_path)
            items[item.platform] = item
        self._items = items

    def get(self, platform: str) -> PlatformDefinition:
        item = self._items.get(platform)
        if item is None:
            raise PlatformNotFoundError(platform)
        return item

    def list_enabled(self) -> list[PlatformDefinition]:
        return [item for item in self._items.values() if item.enabled]
