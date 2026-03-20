"""Service for user reward systems and engagement-driven funding.

Provides reward mechanisms that motivate user engagement while generating
revenue to fund operational tokens.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.reward import RewardTransaction, RewardTypeEnum, UserRewardBalance


# ── Reward Configuration ─────────────────────────────────────────────────────

REWARD_AMOUNTS = {
    RewardTypeEnum.signup_bonus.value: 100.0,
    RewardTypeEnum.idea_submission.value: 25.0,
    RewardTypeEnum.feedback_provided.value: 10.0,
    RewardTypeEnum.referral.value: 50.0,
    RewardTypeEnum.subscription.value: 200.0,
    RewardTypeEnum.engagement.value: 5.0,
    RewardTypeEnum.milestone.value: 100.0,
}

TIER_THRESHOLDS = {
    "bronze": 0,
    "silver": 500,
    "gold": 2000,
    "platinum": 10000,
}


# ── Reward Operations ────────────────────────────────────────────────────────

def award_tokens(
    db: Session,
    user_id: int,
    reward_type: str,
    description: str,
    tokens: Optional[float] = None,
    metadata_json: Optional[str] = None,
) -> RewardTransaction:
    """Award tokens to a user for an engagement action."""
    amount = tokens if tokens is not None else REWARD_AMOUNTS.get(reward_type, 5.0)

    txn = RewardTransaction(
        user_id=user_id,
        reward_type=reward_type,
        tokens_earned=amount,
        description=description,
        metadata_json=metadata_json,
    )
    db.add(txn)

    # Update or create balance record
    balance = db.query(UserRewardBalance).filter(UserRewardBalance.user_id == user_id).first()
    if balance is None:
        balance = UserRewardBalance(
            user_id=user_id,
            total_tokens=amount,
            lifetime_earned=amount,
            lifetime_spent=0.0,
        )
        db.add(balance)
    else:
        balance.total_tokens += amount
        balance.lifetime_earned += amount

    # Update tier
    balance.tier = _calculate_tier(balance.lifetime_earned)

    db.commit()
    db.refresh(txn)
    return txn


def spend_tokens(
    db: Session,
    user_id: int,
    amount: float,
    description: str,
) -> RewardTransaction:
    """Spend user tokens on premium services."""
    balance = db.query(UserRewardBalance).filter(UserRewardBalance.user_id == user_id).first()
    if not balance or balance.total_tokens < amount:
        available = balance.total_tokens if balance else 0
        raise ValueError(f"Insufficient token balance: {available} < {amount}")

    txn = RewardTransaction(
        user_id=user_id,
        reward_type="engagement",
        tokens_earned=-amount,
        description=f"Spent: {description}",
    )
    db.add(txn)

    balance.total_tokens -= amount
    balance.lifetime_spent += amount

    db.commit()
    db.refresh(txn)
    return txn


def get_user_balance(db: Session, user_id: int) -> Optional[UserRewardBalance]:
    """Get the reward balance for a user."""
    return db.query(UserRewardBalance).filter(UserRewardBalance.user_id == user_id).first()


def get_user_transactions(
    db: Session,
    user_id: int,
    limit: int = 50,
) -> list[RewardTransaction]:
    """Get reward transaction history for a user."""
    return (
        db.query(RewardTransaction)
        .filter(RewardTransaction.user_id == user_id)
        .order_by(RewardTransaction.created_at.desc())
        .limit(limit)
        .all()
    )


def get_leaderboard(db: Session, limit: int = 10) -> list[UserRewardBalance]:
    """Get top users by lifetime earnings."""
    return (
        db.query(UserRewardBalance)
        .order_by(UserRewardBalance.lifetime_earned.desc())
        .limit(limit)
        .all()
    )


def _calculate_tier(lifetime_earned: float) -> str:
    """Determine user tier based on lifetime earnings."""
    if lifetime_earned >= TIER_THRESHOLDS["platinum"]:
        return "platinum"
    elif lifetime_earned >= TIER_THRESHOLDS["gold"]:
        return "gold"
    elif lifetime_earned >= TIER_THRESHOLDS["silver"]:
        return "silver"
    return "bronze"


# ── Revenue Model Definitions ────────────────────────────────────────────────

REVENUE_MODELS = {
    "premium_subscriptions": {
        "name": "Premium Subscriptions",
        "description": "Monthly/annual plans with advanced AI features",
        "tiers": [
            {"name": "Starter", "price": 9.99, "features": ["Basic AI analysis", "5 ideas/month"]},
            {"name": "Professional", "price": 29.99, "features": ["Advanced AI", "Unlimited ideas", "Funding research"]},
            {"name": "Enterprise", "price": 99.99, "features": ["All features", "Priority AI", "Custom engines", "API access"]},
        ],
    },
    "token_packs": {
        "name": "Token Packs",
        "description": "One-time token purchases for AI operations",
        "options": [
            {"name": "Starter Pack", "tokens": 500, "price": 4.99},
            {"name": "Growth Pack", "tokens": 2000, "price": 14.99},
            {"name": "Scale Pack", "tokens": 10000, "price": 49.99},
        ],
    },
    "sponsor_placements": {
        "name": "Sponsor Placements",
        "description": "Targeted ad placements reaching engaged users",
        "formats": ["Dashboard banner", "Insight sponsorship", "Report branding"],
    },
}


def get_revenue_models() -> dict:
    """Return available revenue model configurations."""
    return REVENUE_MODELS
