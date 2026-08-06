"""Construct and cache application services."""

from functools import lru_cache

from gateway.alerts.callback import KuberPilotCallbackClient
from gateway.alerts.processor import AlarmChangeProcessor
from gateway.config import PROJECT_DIR, Settings
from gateway.tasks.manager import CollectionTaskManager
from gateway.tasks.scheduler import CollectionScheduler
from gateway.tasks.store import CollectionTaskStore
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


@lru_cache(maxsize=1)
def get_task_store() -> CollectionTaskStore:
    store = CollectionTaskStore(get_settings().task_database_file)
    store.fail_interrupted_tasks()
    return store


@lru_cache(maxsize=1)
def get_task_manager() -> CollectionTaskManager:
    settings = get_settings()
    return CollectionTaskManager(
        get_task_store(),
        get_registry(),
        get_checker(),
        get_credential_provider(),
        change_processor=(
            AlarmChangeProcessor(
                get_task_store(),
                KuberPilotCallbackClient(
                    settings.callback_url,
                    settings.callback_token,
                    timeout_seconds=settings.callback_timeout_seconds,
                    retry_delays_seconds=settings.callback_retry_delays,
                ),
            )
            if settings.callback_enabled and settings.callback_token
            else None
        ),
    )


@lru_cache(maxsize=1)
def get_collection_scheduler() -> CollectionScheduler:
    return CollectionScheduler(get_task_manager(), get_registry())
