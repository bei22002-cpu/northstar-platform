"""Stripe billing integration for the SaaS platform.

Handles checkout sessions, webhook processing, and customer portal.
Requires: pip install stripe

Environment variables:
    STRIPE_SECRET_KEY       — sk_test_... or sk_live_...
    STRIPE_PUBLISHABLE_KEY  — pk_test_... or pk_live_...
    STRIPE_WEBHOOK_SECRET   — whsec_... (from Stripe dashboard)
    STRIPE_PRO_PRICE_ID     — price_... for Pro plan
    STRIPE_ENTERPRISE_PRICE_ID — price_... for Enterprise plan
    SAAS_BASE_URL           — public URL (default: http://localhost:8000)
"""

from __future__ import annotations

import os
from typing import Any, Optional

STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRO_PRICE_ID: str = os.getenv("STRIPE_PRO_PRICE_ID", "")
STRIPE_ENTERPRISE_PRICE_ID: str = os.getenv("STRIPE_ENTERPRISE_PRICE_ID", "")
SAAS_BASE_URL: str = os.getenv("SAAS_BASE_URL", "http://localhost:8000")

# Map plan keys to Stripe price IDs
PLAN_TO_PRICE: dict[str, str] = {
    "pro": STRIPE_PRO_PRICE_ID,
    "enterprise": STRIPE_ENTERPRISE_PRICE_ID,
}


def is_configured() -> bool:
    """Return True if Stripe keys are set."""
    return bool(STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY)


def _get_stripe() -> Any:
    """Lazy-import and configure the stripe module."""
    import stripe

    stripe.api_key = STRIPE_SECRET_KEY
    return stripe


def create_checkout_session(
    user_id: int,
    user_email: str,
    plan: str,
) -> Optional[str]:
    """Create a Stripe Checkout session and return the URL.

    Returns None if the plan has no associated price or Stripe is not configured.
    """
    if not is_configured():
        return None

    price_id = PLAN_TO_PRICE.get(plan)
    if not price_id:
        return None

    stripe = _get_stripe()

    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        customer_email=user_email,
        client_reference_id=str(user_id),
        metadata={"user_id": str(user_id), "plan": plan},
        success_url=f"{SAAS_BASE_URL}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{SAAS_BASE_URL}/pricing",
    )
    return session.url


def create_portal_session(stripe_customer_id: str) -> Optional[str]:
    """Create a Stripe Customer Portal session and return the URL."""
    if not is_configured() or not stripe_customer_id:
        return None

    stripe = _get_stripe()

    session = stripe.billing_portal.Session.create(
        customer=stripe_customer_id,
        return_url=f"{SAAS_BASE_URL}/dashboard",
    )
    return session.url


def handle_webhook_event(payload: bytes, sig_header: str) -> dict[str, Any]:
    """Verify and parse a Stripe webhook event.

    Returns a dict with keys: event_type, user_id, plan, customer_id, subscription_id.
    Raises ValueError on verification failure.
    """
    stripe = _get_stripe()

    if STRIPE_WEBHOOK_SECRET:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    else:
        import json

        event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)

    result: dict[str, Any] = {"event_type": event["type"]}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        result["user_id"] = int(session.get("client_reference_id", 0))
        result["plan"] = session.get("metadata", {}).get("plan", "")
        result["customer_id"] = session.get("customer", "")
        result["subscription_id"] = session.get("subscription", "")

    elif event["type"] in (
        "customer.subscription.updated",
        "customer.subscription.deleted",
    ):
        sub = event["data"]["object"]
        result["customer_id"] = sub.get("customer", "")
        result["subscription_id"] = sub.get("id", "")
        result["status"] = sub.get("status", "")
        result["cancel_at_period_end"] = sub.get("cancel_at_period_end", False)

    return result
