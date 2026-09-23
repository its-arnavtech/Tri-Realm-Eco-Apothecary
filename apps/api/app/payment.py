"""Hosted payment-provider adapter. No raw payment details enter the application."""

import time

import stripe
from fastapi import HTTPException

from app.config import settings


def _configured() -> None:
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret:
        raise HTTPException(503, "Payment provider is not configured")
    stripe.api_key = settings.stripe_secret_key


def create_checkout(
    order_id: str, email: str, lines: list[dict], currency: str, customer_id: str | None = None
) -> tuple[str, str]:
    _configured()
    if not settings.stripe_shipping_rate_id:
        raise HTTPException(503, "Shipping is not configured")
    session = stripe.checkout.Session.create(
        mode="payment",
        client_reference_id=order_id,
        **(
            {"customer": customer_id}
            if customer_id
            else {"customer_email": email, "customer_creation": "always"}
        ),
        line_items=[
            {
                "price_data": {
                    "currency": currency.lower(),
                    "unit_amount": item["unit_price_cents"],
                    "product_data": {"name": item["product_name"]},
                },
                "quantity": item["quantity"],
            }
            for item in lines
        ],
        automatic_tax={"enabled": True},
        shipping_address_collection={"allowed_countries": ["US"]},
        shipping_options=[{"shipping_rate": settings.stripe_shipping_rate_id}],
        success_url=f"{settings.public_web_url}/account/orders?checkout=success",
        cancel_url=f"{settings.public_web_url}/cart?checkout=cancel",
        metadata={"order_id": order_id},
        expires_at=int(time.time()) + 1860,
        idempotency_key=f"checkout-{order_id}",
    )
    if not session.id or not session.url:
        raise HTTPException(502, "Payment provider did not return a checkout URL")
    return session.id, session.url


def verify_event(payload: bytes, signature: str | None) -> dict:
    _configured()
    if not signature:
        raise HTTPException(400, "Missing payment signature")
    try:
        return stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError) as exc:
        raise HTTPException(400, "Invalid payment signature") from exc


def create_refund(payment_intent_id: str, amount_cents: int, refund_id: str):
    _configured()
    return stripe.Refund.create(
        payment_intent=payment_intent_id,
        amount=amount_cents,
        metadata={"internal_refund_id": refund_id},
        idempotency_key=f"refund-{refund_id}",
    )


def create_subscription_checkout(
    customer_id: str | None, email: str, account_id: str, price_id: str, product_id: str
) -> tuple[str, str]:
    _configured()
    if not settings.stripe_shipping_rate_id:
        raise HTTPException(503, "Shipping is not configured")
    session = stripe.checkout.Session.create(
        mode="subscription",
        **({"customer": customer_id} if customer_id else {"customer_email": email}),
        line_items=[{"price": price_id, "quantity": 1}],
        automatic_tax={"enabled": True},
        shipping_address_collection={"allowed_countries": ["US"]},
        shipping_options=[{"shipping_rate": settings.stripe_shipping_rate_id}],
        success_url=f"{settings.public_web_url}/account?subscription=success",
        cancel_url=f"{settings.public_web_url}/account?subscription=cancel",
        metadata={"product_id": product_id, "account_id": account_id},
        subscription_data={"metadata": {"product_id": product_id, "account_id": account_id}},
    )
    return session.id, session.url


def expire_checkout(session_id: str) -> None:
    _configured()
    stripe.checkout.Session.expire(session_id)


def checkout_state(session_id: str) -> tuple[str, str]:
    _configured()
    session = stripe.checkout.Session.retrieve(session_id)
    return session.status, session.payment_status


def subscription_identity(subscription_id: str) -> dict:
    _configured()
    subscription = stripe.Subscription.retrieve(subscription_id)
    return {
        "metadata": dict(subscription.metadata or {}),
        "customer": subscription.customer,
        "status": subscription.status,
    }


def create_billing_portal(customer_id: str) -> str:
    _configured()
    portal = stripe.billing_portal.Session.create(
        customer=customer_id, return_url=f"{settings.public_web_url}/account"
    )
    return portal.url
