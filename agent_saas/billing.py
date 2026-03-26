"""Stripe billing integration — subscriptions, checkout, webhooks."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from agent_saas.config import (
    STRIPE_SECRET_KEY,
    STRIPE_PRICE_ENTERPRISE,
    STRIPE_PRICE_PRO,
    STRIPE_WEBHOOK_SECRET,
    APP_URL,
)
from agent_saas.models import User


def _get_stripe():
    """Lazy-import stripe to avoid hard dependency."""
    try:
        import stripe

        stripe.api_key = STRIPE_SECRET_KEY
        return stripe
    except ImportError:
        return None


def is_stripe_configured() -> bool:
    """Check if Stripe keys are set."""
    return bool(STRIPE_SECRET_KEY and STRIPE_PRICE_PRO)


def create_checkout_session(user: User, plan: str) -> dict[str, Any]:
    """Create a Stripe Checkout session for a plan upgrade."""
    stripe = _get_stripe()
    if not stripe:
        return {"error": "Stripe is not installed. Run: pip install stripe"}
    if not STRIPE_SECRET_KEY:
        return {"error": "Stripe is not configured. Set STRIPE_SECRET_KEY in .env"}

    price_id = STRIPE_PRICE_PRO if plan == "pro" else STRIPE_PRICE_ENTERPRISE
    if not price_id:
        return {"error": f"No Stripe price ID configured for plan: {plan}"}

    try:
        # Create or reuse Stripe customer
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": user.id},
            )
            customer_id = customer.id
        else:
            customer_id = user.stripe_customer_id

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=f"{APP_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/pricing",
            metadata={"user_id": user.id, "plan": plan},
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        return {"error": str(e)}


def handle_webhook(payload: bytes, sig_header: str, db: Session) -> dict[str, Any]:
    """Handle Stripe webhook events."""
    stripe = _get_stripe()
    if not stripe:
        return {"error": "Stripe not installed"}

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        return {"error": f"Webhook verification failed: {e}"}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("metadata", {}).get("user_id")
        plan = session.get("metadata", {}).get("plan", "pro")

        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.plan = plan
                user.stripe_customer_id = session.get("customer", "")
                user.stripe_subscription_id = session.get("subscription", "")
                db.commit()

    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        customer_id = sub.get("customer", "")
        if customer_id:
            user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
            if user:
                user.plan = "free"
                user.stripe_subscription_id = ""
                db.commit()

    return {"status": "ok"}


def get_billing_portal_url(user: User) -> dict[str, Any]:
    """Create a Stripe billing portal session for managing subscription."""
    stripe = _get_stripe()
    if not stripe or not user.stripe_customer_id:
        return {"error": "No billing account found."}

    try:
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=f"{APP_URL}/dashboard",
        )
        return {"url": session.url}
    except Exception as e:
        return {"error": str(e)}
