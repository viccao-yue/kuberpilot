import pytest

from gateway.config import Settings


def test_task_database_path_must_stay_inside_project():
    settings = Settings(task_database_path="../outside.sqlite3")

    with pytest.raises(ValueError, match="must stay inside"):
        settings.task_database_file


def test_callback_retry_delays_are_validated():
    settings = Settings(callback_retry_delays_seconds="0,1.5,90")
    assert settings.callback_retry_delays == (0.0, 1.5, 90.0)

    with pytest.raises(ValueError, match="between 0 and 300"):
        Settings(callback_retry_delays_seconds="301").callback_retry_delays

    with pytest.raises(ValueError, match="at most five"):
        Settings(callback_retry_delays_seconds="1,2,3,4,5,6").callback_retry_delays
