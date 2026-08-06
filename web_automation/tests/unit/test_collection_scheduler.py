from unittest.mock import Mock

from gateway.tasks.scheduler import CollectionScheduler


async def test_scheduler_registers_only_configured_enabled_platforms():
    configured = Mock(
        platform="mock_platform",
        alarm_collection_interval_seconds=60,
    )
    disabled_schedule = Mock(
        platform="network_only",
        alarm_collection_interval_seconds=None,
    )
    registry = Mock()
    registry.list_enabled.return_value = [configured, disabled_schedule]
    scheduler = CollectionScheduler(Mock(), registry)

    scheduler.start()
    try:
        jobs = scheduler.scheduler.get_jobs()
    finally:
        scheduler.shutdown()

    assert [job.id for job in jobs] == ["mock_platform.list_alarms"]
    assert jobs[0].trigger.interval.total_seconds() == 60
