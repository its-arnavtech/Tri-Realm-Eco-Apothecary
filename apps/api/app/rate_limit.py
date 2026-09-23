"""Shared fixed-window limiter backed by the transactional database."""

import hashlib
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import commerce_models as cm
from app.db import get_db

WINDOW_SECONDS = 15 * 60
PATH_LIMITS = {
    "/api/v1/events": 120,
    "/api/v1/recommendations": 60,
    "/api/v1/carts": 30,
    "/api/v1/auth/login": 30,
    "/api/v1/checkout/session": 20,
}


def limited(request: Request, db: Annotated[Session, Depends(get_db)]) -> None:
    path = request.url.path
    limit = PATH_LIMITS.get(path, 10)
    window = int(datetime.now(UTC).timestamp()) // WINDOW_SECONDS
    address = request.client.host if request.client else "unknown"
    key_hash = hashlib.sha256(f"{address}:{path}:{window}".encode()).hexdigest()
    expires_at = datetime.fromtimestamp((window + 1) * WINDOW_SECONDS, UTC)
    try:
        with db.begin_nested():
            db.add(cm.RateLimitBucket(key_hash=key_hash, attempts=1, expires_at=expires_at))
            db.flush()
        attempts = 1
    except IntegrityError:
        attempts = db.execute(
            update(cm.RateLimitBucket)
            .where(cm.RateLimitBucket.key_hash == key_hash)
            .values(attempts=cm.RateLimitBucket.attempts + 1)
            .returning(cm.RateLimitBucket.attempts)
        ).scalar_one()
    db.commit()
    if attempts > limit:
        raise HTTPException(429, "Too many requests. Try again later.")
