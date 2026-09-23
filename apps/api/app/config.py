from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DATABASE_URL = (
    f"sqlite:///{(Path(__file__).resolve().parent.parent / 'brew67.db').as_posix()}"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[3] / ".env"), extra="ignore"
    )

    database_url: str = LOCAL_DATABASE_URL
    web_origin: str = "http://localhost:3000"
    admin_api_key: str = ""
    environment: str = "local"
    commerce_enabled: bool = False
    consent_policy_version: str = "2026-09-poc"
    intent_retention_days: int = 90
    analytics_retention_days: int = 30


settings = Settings()
