"""Run as a scheduled job to enforce POC data retention."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete

from app import models
from app.config import settings
from app.db import SessionLocal


def purge_expired() -> tuple[int, int]:
    current = datetime.now(UTC)
    with SessionLocal() as db:
        signups = db.execute(
            delete(models.IntentSignup).where(
                models.IntentSignup.created_at
                < current - timedelta(days=settings.intent_retention_days)
            )
        ).rowcount
        events = db.execute(
            delete(models.AnalyticsEvent).where(
                models.AnalyticsEvent.occurred_at
                < current - timedelta(days=settings.analytics_retention_days)
            )
        ).rowcount
        db.commit()
    return signups, events


if __name__ == "__main__":
    signups, events = purge_expired()
    print(f"Purged {signups} intent signups and {events} analytics events")
