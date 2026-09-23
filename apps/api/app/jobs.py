"""Run once per minute with a scheduler for checkout and email reconciliation."""

import logging
import smtplib
from datetime import UTC, datetime, timedelta
from email.message import EmailMessage

from sqlalchemy import delete, select

from app import commerce_models as cm
from app import commerce_service, payment
from app.config import settings
from app.db import SessionLocal

logger = logging.getLogger(__name__)


def email_content(row: cm.EmailOutbox) -> tuple[str, str]:
    if row.template == "verify_email":
        return (
            "Verify your brew67potions email",
            f"Open this link to verify your email:\n{row.payload['url']}",
        )
    if row.template == "password_reset":
        return (
            "Reset your brew67potions password",
            f"Open this link to reset your password:\n{row.payload['url']}",
        )
    if row.template == "order_confirmed":
        return "Your brew67potions order is confirmed", (
            "We received your payment. View your order at "
            f"{settings.public_web_url}/account/orders/{row.payload['order_id']}"
        )
    if row.template == "order_stock_hold":
        return "Paid refill order needs stock review", (
            f"Order {row.payload['order_id']} was paid but stock could not be allocated. "
            "Replenish and allocate it in operations before fulfillment."
        )
    raise ValueError(f"Unsupported email template: {row.template}")


def send_email(row: cm.EmailOutbox) -> None:
    if not settings.smtp_host or not settings.smtp_from:
        raise RuntimeError("SMTP host and sender must be configured")
    subject, body = email_content(row)
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = row.recipient
    message["Subject"] = subject
    message.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


def reconcile_expired_checkouts() -> int:
    completed = 0
    with SessionLocal() as db:
        orders = db.scalars(
            select(cm.Order)
            .where(
                cm.Order.status.in_(["pending_payment", "checkout_open"]),
                cm.Order.reservation_expires_at < datetime.now(UTC),
            )
            .with_for_update(skip_locked=True)
            .limit(50)
        ).all()
        for order in orders:
            if order.stripe_checkout_id:
                try:
                    state, payment_status = payment.checkout_state(order.stripe_checkout_id)
                    if state == "open":
                        payment.expire_checkout(order.stripe_checkout_id)
                        state = "expired"
                    if state != "expired" or payment_status == "paid":
                        continue
                except Exception:
                    # Provider state must be known before releasing stock.
                    logger.exception("Could not reconcile checkout %s", order.id)
                    continue
            commerce_service.release_reservation(db, order, "checkout_expired")
            completed += 1
        db.commit()
    return completed


def deliver_outbox() -> tuple[int, int]:
    sent = failed = 0
    with SessionLocal() as db:
        rows = db.scalars(
            select(cm.EmailOutbox)
            .where(
                cm.EmailOutbox.status == "pending",
                cm.EmailOutbox.attempts < 5,
            )
            .order_by(cm.EmailOutbox.created_at)
            .with_for_update(skip_locked=True)
            .limit(20)
        ).all()
        for row in rows:
            try:
                send_email(row)
                row.status = "sent"
                row.sent_at = datetime.now(UTC)
                sent += 1
            except Exception:
                logger.exception("Could not send outbox message %s", row.id)
                row.attempts += 1
                if row.attempts >= 5:
                    row.status = "failed"
                failed += 1
        db.commit()
    return sent, failed


def purge_account_tokens() -> int:
    with SessionLocal() as db:
        cutoff = datetime.now(UTC) - timedelta(days=7)
        count = 0
        for table in (cm.AuthSession, cm.EmailVerification, cm.PasswordReset):
            count += db.execute(delete(table).where(table.expires_at < cutoff)).rowcount
        count += db.execute(
            delete(cm.EmailOutbox).where(
                cm.EmailOutbox.created_at < datetime.now(UTC) - timedelta(days=30),
                cm.EmailOutbox.status.in_(["sent", "failed"]),
            )
        ).rowcount
        count += db.execute(
            delete(cm.RateLimitBucket).where(cm.RateLimitBucket.expires_at < datetime.now(UTC))
        ).rowcount
        db.commit()
    return count


if __name__ == "__main__":
    expired = reconcile_expired_checkouts()
    sent, failed = deliver_outbox()
    purged = purge_account_tokens()
    print(
        f"Expired checkouts: {expired}; emails sent: {sent}; send failures: {failed}; token rows purged: {purged}"
    )
