"""Customer accounts, secure sessions, and recovery controls."""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Annotated

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app import commerce_models as cm
from app.config import settings
from app.db import get_db
from app.rate_limit import limited

router = APIRouter(prefix="/api/v1/auth", tags=["accounts"])
hasher = PasswordHasher()
DUMMY_HASH = hasher.hash("not-a-real-account-password")
SESSION_DAYS = 7


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenIn(BaseModel):
    token: str = Field(min_length=32, max_length=128)


class ResetIn(TokenIn):
    password: str = Field(min_length=12, max_length=128)


class EmailIn(BaseModel):
    email: EmailStr


class PreferencesIn(BaseModel):
    preferred_biome: str | None = Field(
        default=None, pattern=r"^(forest|ocean|mountain|tri-realm)$"
    )


class CustomerOut(BaseModel):
    id: str
    email: str
    role: str
    email_verified: bool
    preferences: dict


def customer_out(customer: cm.Customer) -> CustomerOut:
    return CustomerOut(
        id=customer.id,
        email=customer.email,
        role=customer.role,
        email_verified=customer.email_verified_at is not None,
        preferences=customer.preferences,
    )


def enforce_origin(request: Request) -> None:
    if settings.environment != "local" and request.headers.get("origin") != settings.web_origin:
        raise HTTPException(403, "Origin not allowed")


def issue_session(db: Session, response: Response, customer: cm.Customer) -> None:
    token = secrets.token_urlsafe(48)
    csrf = secrets.token_urlsafe(32)
    db.add(
        cm.AuthSession(
            customer_id=customer.id,
            token_hash=digest(token),
            csrf_hash=digest(csrf),
            expires_at=datetime.now(UTC) + timedelta(days=SESSION_DAYS),
        )
    )
    db.commit()
    max_age = SESSION_DAYS * 86400
    response.set_cookie(
        "brew67_session",
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.session_cookie_secure or settings.environment != "local",
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        "brew67_csrf",
        csrf,
        max_age=max_age,
        httponly=False,
        secure=settings.session_cookie_secure or settings.environment != "local",
        samesite="lax",
        path="/",
    )


def resolve_session(db: Session, token: str | None) -> cm.AuthSession | None:
    if not token:
        return None
    session = db.scalar(
        select(cm.AuthSession)
        .options(joinedload(cm.AuthSession.customer))
        .where(cm.AuthSession.token_hash == digest(token))
    )
    if not session or session.revoked_at or utc(session.expires_at) <= datetime.now(UTC):
        return None
    if not session.customer.active:
        return None
    return session


def current_session(
    db: Annotated[Session, Depends(get_db)],
    brew67_session: Annotated[str | None, Cookie()] = None,
) -> cm.AuthSession:
    session = resolve_session(db, brew67_session)
    if not session:
        raise HTTPException(401, "Sign in required")
    return session


SessionDep = Annotated[cm.AuthSession, Depends(current_session)]


def current_customer(session: SessionDep) -> cm.Customer:
    return session.customer


CustomerDep = Annotated[cm.Customer, Depends(current_customer)]


def csrf_customer(
    request: Request,
    session: SessionDep,
) -> cm.Customer:
    enforce_csrf(request, session)
    return session.customer


def enforce_csrf(request: Request, session: cm.AuthSession) -> None:
    enforce_origin(request)
    x_csrf_token = request.headers.get("x-csrf-token")
    brew67_csrf = request.cookies.get("brew67_csrf")
    if (
        not x_csrf_token
        or not brew67_csrf
        or not secrets.compare_digest(x_csrf_token, brew67_csrf)
        or not secrets.compare_digest(digest(x_csrf_token), session.csrf_hash)
    ):
        raise HTTPException(403, "CSRF token required")


CsrfCustomer = Annotated[cm.Customer, Depends(csrf_customer)]


def require_role(*roles: str):
    def check(customer: CustomerDep) -> cm.Customer:
        if customer.role not in roles:
            raise HTTPException(403, "Insufficient role")
        return customer

    return check


@router.post(
    "/register", response_model=CustomerOut, status_code=201, dependencies=[Depends(limited)]
)
def register(
    payload: RegisterIn,
    request: Request,
    response: Response,
    db: Annotated[Session, Depends(get_db)],
):
    enforce_origin(request)
    email = str(payload.email).lower()
    if db.scalar(select(cm.Customer.id).where(cm.Customer.email == email)):
        raise HTTPException(409, "Account already exists")
    customer = cm.Customer(email=email, password_hash=hasher.hash(payload.password))
    db.add(customer)
    db.flush()
    token = secrets.token_urlsafe(48)
    db.add(
        cm.EmailVerification(
            customer_id=customer.id,
            token_hash=digest(token),
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
    )
    db.add(
        cm.EmailOutbox(
            recipient=email,
            template="verify_email",
            payload={"url": f"{settings.public_web_url}/verify?token={token}"},
        )
    )
    db.commit()
    issue_session(db, response, customer)
    return customer_out(customer)


@router.post("/login", response_model=CustomerOut, dependencies=[Depends(limited)])
def login(
    payload: LoginIn, request: Request, response: Response, db: Annotated[Session, Depends(get_db)]
):
    enforce_origin(request)
    customer = db.scalar(select(cm.Customer).where(cm.Customer.email == str(payload.email).lower()))
    if customer and customer.locked_until and utc(customer.locked_until) > datetime.now(UTC):
        raise HTTPException(429, "Too many failed attempts. Try again later")
    try:
        valid = bool(
            hasher.verify(customer.password_hash if customer else DUMMY_HASH, payload.password)
        )
    except VerificationError:
        valid = False
    if not valid or not customer or not customer.active:
        if customer:
            customer.failed_login_attempts += 1
            if customer.failed_login_attempts >= 5:
                customer.locked_until = datetime.now(UTC) + timedelta(minutes=15)
                customer.failed_login_attempts = 0
            db.commit()
        raise HTTPException(401, "Invalid credentials")
    customer.failed_login_attempts = 0
    customer.locked_until = None
    issue_session(db, response, customer)
    return customer_out(customer)


@router.post("/logout")
def logout(
    response: Response,
    session: SessionDep,
    customer: CsrfCustomer,
    db: Annotated[Session, Depends(get_db)],
):
    session.revoked_at = datetime.now(UTC)
    db.commit()
    response.delete_cookie("brew67_session", path="/")
    response.delete_cookie("brew67_csrf", path="/")
    return {"signed_out": True}


@router.get("/me", response_model=CustomerOut)
def me(customer: CustomerDep):
    return customer_out(customer)


@router.patch("/preferences", response_model=CustomerOut)
def save_preferences(
    payload: PreferencesIn, customer: CsrfCustomer, db: Annotated[Session, Depends(get_db)]
):
    customer.preferences = payload.model_dump(exclude_none=True)
    db.commit()
    return customer_out(customer)


@router.post("/verify-email", dependencies=[Depends(limited)])
def verify_email(payload: TokenIn, db: Annotated[Session, Depends(get_db)]):
    verification = db.scalar(
        select(cm.EmailVerification).where(cm.EmailVerification.token_hash == digest(payload.token))
    )
    if (
        not verification
        or verification.used_at
        or utc(verification.expires_at) <= datetime.now(UTC)
    ):
        raise HTTPException(400, "Verification link is invalid or expired")
    customer = db.get(cm.Customer, verification.customer_id)
    verification.used_at = datetime.now(UTC)
    customer.email_verified_at = datetime.now(UTC)
    db.commit()
    return {"verified": True}


@router.post("/verification/resend")
def resend_verification(customer: CsrfCustomer, db: Annotated[Session, Depends(get_db)]):
    if customer.email_verified_at:
        return {"sent": False, "message": "Email is already verified"}
    recent = db.scalar(
        select(cm.EmailVerification).where(
            cm.EmailVerification.customer_id == customer.id,
            cm.EmailVerification.used_at.is_(None),
            cm.EmailVerification.expires_at > datetime.now(UTC) + timedelta(hours=23, minutes=50),
        )
    )
    if recent:
        return {"sent": False, "message": "A verification link was recently sent"}
    token = secrets.token_urlsafe(48)
    db.add(
        cm.EmailVerification(
            customer_id=customer.id,
            token_hash=digest(token),
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
    )
    db.add(
        cm.EmailOutbox(
            recipient=customer.email,
            template="verify_email",
            payload={"url": f"{settings.public_web_url}/verify?token={token}"},
        )
    )
    db.commit()
    return {"sent": True}


@router.post("/password-reset/request", dependencies=[Depends(limited)])
def request_reset(payload: EmailIn, request: Request, db: Annotated[Session, Depends(get_db)]):
    enforce_origin(request)
    customer = db.scalar(select(cm.Customer).where(cm.Customer.email == str(payload.email).lower()))
    if customer and customer.active:
        recent = db.scalar(
            select(cm.PasswordReset).where(
                cm.PasswordReset.customer_id == customer.id,
                cm.PasswordReset.used_at.is_(None),
                cm.PasswordReset.expires_at > datetime.now(UTC) + timedelta(minutes=25),
            )
        )
        if recent:
            return {"message": "If this account exists, recovery instructions will be sent."}
        token = secrets.token_urlsafe(48)
        db.add(
            cm.PasswordReset(
                customer_id=customer.id,
                token_hash=digest(token),
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
        )
        db.add(
            cm.EmailOutbox(
                recipient=customer.email,
                template="password_reset",
                payload={"url": f"{settings.public_web_url}/reset-password?token={token}"},
            )
        )
        db.commit()
    return {"message": "If this account exists, recovery instructions will be sent."}


@router.post("/password-reset/confirm", dependencies=[Depends(limited)])
def confirm_reset(payload: ResetIn, request: Request, db: Annotated[Session, Depends(get_db)]):
    enforce_origin(request)
    reset = db.scalar(
        select(cm.PasswordReset).where(cm.PasswordReset.token_hash == digest(payload.token))
    )
    if not reset or reset.used_at or utc(reset.expires_at) <= datetime.now(UTC):
        raise HTTPException(400, "Recovery link is invalid or expired")
    customer = db.get(cm.Customer, reset.customer_id)
    customer.password_hash = hasher.hash(payload.password)
    reset.used_at = datetime.now(UTC)
    db.execute(
        update(cm.AuthSession)
        .where(cm.AuthSession.customer_id == customer.id)
        .values(revoked_at=datetime.now(UTC))
    )
    db.commit()
    return {"password_reset": True}
