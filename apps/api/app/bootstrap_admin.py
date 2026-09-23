"""Create the first administrator from an interactive operator terminal."""

import getpass

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import func, select

from app.auth import hasher
from app.commerce_models import Customer
from app.db import SessionLocal
from app.models import AuditEvent, now


def bootstrap() -> None:
    with SessionLocal() as db:
        count = db.scalar(
            select(func.count())
            .select_from(Customer)
            .where(Customer.role == "admin", Customer.active.is_(True))
        )
        if count:
            raise SystemExit(
                "An administrator already exists. Use the audited role API for staff changes."
            )
        try:
            email = str(
                TypeAdapter(EmailStr).validate_python(
                    input("Verified administrator email: ").strip()
                )
            ).lower()
        except ValueError as exc:
            raise SystemExit("Enter a valid email address") from exc
        password = getpass.getpass("New password (at least 12 characters): ")
        if len(password) < 12:
            raise SystemExit("Password must have at least 12 characters")
        customer = db.scalar(select(Customer).where(Customer.email == email))
        if customer:
            if not customer.email_verified_at:
                raise SystemExit("The existing account must verify its email before promotion")
            customer.role = "admin"
            customer.password_hash = hasher.hash(password)
        else:
            customer = Customer(
                email=email,
                password_hash=hasher.hash(password),
                role="admin",
                email_verified_at=now(),
            )
            db.add(customer)
        db.flush()
        db.add(
            AuditEvent(
                actor="bootstrap_admin",
                reason="Initial administrator provisioning",
                action="role_change",
                entity_type="customer",
                entity_id=customer.id,
                before_snapshot=None,
                after_snapshot={"role": "admin"},
            )
        )
        db.commit()
        print(f"Administrator ready: {email}")


if __name__ == "__main__":
    bootstrap()
