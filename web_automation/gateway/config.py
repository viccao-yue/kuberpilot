"""Gateway settings resolved relative to the project, not the user profile."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    host: str = "127.0.0.1"
    port: int = 8010
    log_level: str = "INFO"
    platform_dir: str = "platforms/definitions"

    model_config = SettingsConfigDict(
        env_prefix="WEB_AUTOMATION_",
        env_file=PROJECT_DIR / ".env",
        extra="ignore",
    )

    @property
    def platform_definition_dir(self) -> Path:
        path = Path(self.platform_dir)
        return path.resolve() if path.is_absolute() else (PROJECT_DIR / path).resolve()
