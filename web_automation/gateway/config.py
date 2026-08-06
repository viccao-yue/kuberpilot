"""Gateway settings resolved relative to the project, not the user profile."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8010
    log_level: str = "INFO"
    platform_dir: str = "platforms/definitions"
    task_database_path: str = ".runtime/collection-tasks.sqlite3"
    scheduler_enabled: bool = True
    callback_enabled: bool = False
    callback_url: str = "http://127.0.0.1:8000/api/alerts/webhooks/web-automation/"
    callback_token: str = ""
    callback_timeout_seconds: float = 5.0
    callback_retry_delays_seconds: str = "10,30,90"

    model_config = SettingsConfigDict(
        env_prefix="WEB_AUTOMATION_",
        env_file=PROJECT_DIR / ".env",
        extra="ignore",
    )

    @property
    def platform_definition_dir(self) -> Path:
        path = Path(self.platform_dir)
        return path.resolve() if path.is_absolute() else (PROJECT_DIR / path).resolve()

    @property
    def task_database_file(self) -> Path:
        path = Path(self.task_database_path)
        resolved = path.resolve() if path.is_absolute() else (PROJECT_DIR / path).resolve()
        if not resolved.is_relative_to(PROJECT_DIR):
            raise ValueError("Task database path must stay inside the web_automation directory")
        return resolved

    @property
    def callback_retry_delays(self) -> tuple[float, ...]:
        values = []
        for raw_value in self.callback_retry_delays_seconds.split(","):
            value = raw_value.strip()
            if not value:
                continue
            delay = float(value)
            if delay < 0 or delay > 300:
                raise ValueError("Callback retry delays must be between 0 and 300 seconds")
            values.append(delay)
        if len(values) > 5:
            raise ValueError("Callback retry delays support at most five retries")
        return tuple(values)
