from app.config import Settings


def test_managed_postgres_urls_use_installed_psycopg_driver():
    for scheme in ("postgres", "postgresql"):
        settings = Settings(
            _env_file=None,
            database_url=f"{scheme}://user:password@database.example/brew67?sslmode=require",
        )
        assert settings.database_url == (
            "postgresql+psycopg://user:password@database.example/brew67?sslmode=require"
        )


def test_explicit_driver_and_sqlite_urls_are_unchanged():
    for url in ("postgresql+psycopg://user:password@localhost/brew67", "sqlite:///test.db"):
        assert Settings(_env_file=None, database_url=url).database_url == url
