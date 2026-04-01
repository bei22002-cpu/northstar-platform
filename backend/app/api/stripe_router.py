"""Stripe payment integration: checkout sessions, webhooks, and customer portal."""

import logging
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import (
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
    STRIPE_PRO_PRICE_ID,
    FRONTEND_URL,
)
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.subscription import UserSubscription, PlanTier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_subscription(db: Session, user_id: int) -> UserSubscription:
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
    if not sub:
        sub = UserSubscription(user_id=user_id, tier=PlanTier.free, messages_used=0, messages_limit=50)
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


def _get_or_create_stripe_customer(user: User, db: Session) -> str:
    """Ensure user has a Stripe customer ID."""
    sub = _get_or_create_subscription(db, user.id)
    if sub.stripe_customer_id:
        return sub.stripe_customer_id

    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe is not configured. Set STRIPE_SECRET_KEY.")

    stripe.api_key = STRIPE_SECRET_KEY
    customer = stripe.Customer.create(
        email=user.email,
        metadata={"user_id": str(user.id)},
    )
    sub.stripe_customer_id = customer.id
    db.commit()
    return customer.id


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class CheckoutResponse(BaseModel):
    checkout_url: str

class PortalResponse(BaseModel):
    portal_url: str

class StripeConfigResponse(BaseModel):
    publishable_key: str
    pro_price_id: str
    is_configured: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/config", response_model=StripeConfigResponse)
def get_stripe_config():
    """Return public Stripe config for the frontend."""
    from app.core.config import STRIPE_PUBLISHABLE_KEY
    return StripeConfigResponse(
        publishable_key=STRIPE_PUBLISHABLE_KEY or "",
        pro_price_id=STRIPE_PRO_PRICE_ID or "",
        is_configured=bool(STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY),
    )


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for Pro upgrade."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")
    if not STRIPE_PRO_PRICE_ID:
        raise HTTPException(status_code=503, detail="Stripe Pro price ID is not configured.")

    stripe.api_key = STRIPE_SECRET_KEY
    customer_id = _get_or_create_stripe_customer(current_user, db)

    session = stripe.checkout.Session.create(
        customer=customer_id,
        mode="subscription",
        line_items=[{"price": STRIPE_PRO_PRICE_ID, "quantity": 1}],
        success_url=f"{FRONTEND_URL}/settings?payment=success",
        cancel_url=f"{FRONTEND_URL}/pricing?payment=cancelled",
        metadata={"user_id": str(current_user.id)},
    )
    return CheckoutResponse(checkout_url=session.url)


@router.post("/portal", response_model=PortalResponse)
def create_portal_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Customer Portal session to manage subscription."""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")

    stripe.api_key = STRIPE_SECRET_KEY
    customer_id = _get_or_create_stripe_customer(current_user, db)

    portal = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{FRONTEND_URL}/settings",
    )
    return PortalResponse(portal_url=portal.url)


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events for subscription lifecycle."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe is not configured.")

    stripe.api_key = STRIPE_SECRET_KEY

    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
        else:
            import json
            event = stripe.Event.construct_from(json.loads(payload), stripe.api_key)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.error("Webhook signature verification failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data, db)
    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(data, db)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data, db)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(data, db)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Webhook handlers
# ---------------------------------------------------------------------------

def _find_sub_by_customer(db: Session, customer_id: str) -> Optional[UserSubscription]:
    return db.query(UserSubscription).filter(
        UserSubscription.stripe_customer_id == customer_id
    ).first()


def _handle_checkout_completed(data: dict, db: Session):
    customer_id = data.get("customer")
    subscription_id = data.get("subscription")
    if not customer_id:
        return
    sub = _find_sub_by_customer(db, customer_id)
    if sub:
        sub.tier = PlanTier.pro
        sub.messages_limit = -1  # unlimited
        sub.stripe_subscription_id = subscription_id
        sub.is_active = True
        db.commit()
        logger.info("Upgraded user subscription to Pro via checkout: customer=%s", customer_id)


def _handle_subscription_updated(data: dict, db: Session):
    customer_id = data.get("customer")
    status = data.get("status")
    if not customer_id:
        return
    sub = _find_sub_by_customer(db, customer_id)
    if sub:
        if status in ("active", "trialing"):
            sub.tier = PlanTier.pro
            sub.messages_limit = -1
            sub.is_active = True
        elif status in ("past_due", "unpaid"):
            sub.is_active = False
        db.commit()


def _handle_subscription_deleted(data: dict, db: Session):
    customer_id = data.get("customer")
    if not customer_id:
        return
    sub = _find_sub_by_customer(db, customer_id)
    if sub:
        sub.tier = PlanTier.free
        sub.messages_limit = 50
        sub.messages_used = 0
        sub.stripe_subscription_id = None
        sub.is_active = True
        db.commit()
        logger.info("Downgraded user to Free: customer=%s", customer_id)


def _handle_payment_failed(data: dict, db: Session):
    customer_id = data.get("customer")
    if not customer_id:
        return
    sub = _find_sub_by_customer(db, customer_id)
    if sub:
        sub.is_active = False
        db.commit()
        logger.warning("Payment failed for customer=%s", customer_id)
