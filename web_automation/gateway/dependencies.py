"""Construct and cache application services."""

from functools import lru_cache

from gateway.config import PROJECT_DIR, Settings
from network.checker import ConnectivityChecker
from platforms.loader import PlatformRegistry
from credentials.environment import EnvironmentCredentialProvider


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@lru_cache(maxsize=1)
def get_registry() -> PlatformRegistry:
    settings = get_settings()
    registry = PlatformRegistry(settings.platform_definition_dir, PROJECT_DIR)
    registry.load()
    return registry


def get_checker() -> ConnectivityChecker:
    return ConnectivityChecker(get_registry())


@lru_cache(maxsize=1)
def get_credential_provider() -> EnvironmentCredentialProvider:
    return EnvironmentCredentialProvider()
