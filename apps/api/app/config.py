from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

LOCAL_DATABASE_URL = (
    f"sqlite:///{(Path(__file__).resolve().parent.parent / 'brew67.db').as_posix()}"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent.parent / ".env"),
        extra="ignore",
    )

    database_url: str = LOCAL_DATABASE_URL
    web_origin: str = "http://localhost:3000"
    admin_api_key: str = ""
    environment: str = "production"
    commerce_enabled: bool = False
    local_test_commerce: bool = False
    consent_policy_version: str = "2026-09-poc"
    intent_retention_days: int = 90
    analytics_retention_days: int = 30
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_shipping_rate_id: str = ""
    subscriptions_enabled: bool = False
    session_cookie_secure: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_starttls: bool = True
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    operations_email: str = ""
    public_web_url: str = "http://localhost:3000"
    launch_approval_reference: str = ""
    support_email: str = ""
    terms_url: str = ""
    refund_policy_url: str = ""

    @field_validator("database_url")
    @classmethod
    def use_psycopg_for_managed_postgres(cls, value: str) -> str:
        # Managed hosts usually provide a plain PostgreSQL URL. This API ships psycopg 3.
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value


settings = Settings()
