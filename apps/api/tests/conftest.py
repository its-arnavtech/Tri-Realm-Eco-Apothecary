import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import seed
from app.config import settings
from app.db import Base, get_db
from app.main import app


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    local = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(seed, "SessionLocal", local)
    seed.seed()

    def database():
        with local() as db:
            yield db

    app.dependency_overrides[get_db] = database
    monkeypatch.setattr(settings, "admin_api_key", "test-admin-secret")
    monkeypatch.setattr(settings, "environment", "local")
    monkeypatch.setattr(settings, "local_test_commerce", True)
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fixture")
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_fixture")
    monkeypatch.setattr(settings, "stripe_shipping_rate_id", "shr_fixture")
    with TestClient(app) as test_client:
        yield test_client, local
    app.dependency_overrides.clear()
    engine.dispose()
