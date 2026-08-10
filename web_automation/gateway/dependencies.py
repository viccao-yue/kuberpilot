"""Construct and cache application services."""

from functools import lru_cache

from gateway.alerts.callback import KuberPilotCallbackClient
from gateway.alerts.processor import AlarmChangeProcessor
from gateway.config import PROJECT_DIR, Settings
from gateway.delivery.store import DeliveryJobStore
from gateway.delivery.worker import DeliveryWorker
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
def get_delivery_store() -> DeliveryJobStore:
    return DeliveryJobStore(get_settings().task_database_file)


@lru_cache(maxsize=1)
def get_callback_client() -> KuberPilotCallbackClient:
    settings = get_settings()
    return KuberPilotCallbackClient(
        settings.callback_url,
        settings.callback_token,
        timeout_seconds=settings.callback_timeout_seconds,
    )


@lru_cache(maxsize=1)
def get_delivery_worker() -> DeliveryWorker:
    settings = get_settings()
    return DeliveryWorker(
        get_delivery_store(),
        get_callback_client(),
        retry_delays_seconds=settings.callback_retry_delays,
        poll_interval_seconds=settings.delivery_poll_interval_seconds,
        batch_size=settings.delivery_batch_size,
    )


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
                get_delivery_store(),
                get_callback_client(),
                get_delivery_worker(),
                settings.delivery_max_attempts,
            )
            if settings.callback_enabled and settings.callback_token
            else None
        ),
    )


@lru_cache(maxsize=1)
def get_collection_scheduler() -> CollectionScheduler:
    return CollectionScheduler(get_task_manager(), get_registry())
