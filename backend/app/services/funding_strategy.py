"""Service for autonomous funding identification and token acquisition.

Provides algorithms for AI engines to identify funding opportunities,
propose budgets, and manage token balances.
"""

import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ai_engine import AIEngine
from app.models.funding import FundingRequest, FundingStatusEnum, FundingTypeEnum, TokenTransaction


# ── Funding Request Management ────────────────────────────────────────────────

def create_funding_request(
    db: Session,
    engine_id: int,
    funding_type: str,
    title: str,
    description: str,
    amount_requested: float,
    justification: Optional[str] = None,
    projected_roi: Optional[float] = None,
    operational_cost: Optional[float] = None,
    strategy_details: Optional[str] = None,
) -> FundingRequest:
    """Create a new funding request from an AI engine."""
    engine = db.query(AIEngine).filter(AIEngine.id == engine_id).first()
    if not engine:
        raise ValueError(f"Engine {engine_id} not found")

    request = FundingRequest(
        engine_id=engine_id,
        funding_type=funding_type,
        title=title,
        description=description,
        amount_requested=amount_requested,
        justification=justification,
        projected_roi=projected_roi,
        operational_cost=operational_cost,
        strategy_details=strategy_details,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def update_funding_status(
    db: Session,
    request_id: int,
    status: str,
    amount_secured: Optional[float] = None,
) -> FundingRequest:
    """Update the status of a funding request."""
    request = db.query(FundingRequest).filter(FundingRequest.id == request_id).first()
    if not request:
        raise ValueError(f"Funding request {request_id} not found")

    request.status = status
    if amount_secured is not None:
        request.amount_secured = amount_secured

    # If completed, credit the engine's token balance
    if status == FundingStatusEnum.completed.value and amount_secured:
        _credit_tokens(db, request.engine_id, amount_secured, f"Funding completed: {request.title}", request_id)

    db.commit()
    db.refresh(request)
    return request


def get_funding_requests(
    db: Session,
    engine_id: Optional[int] = None,
    status: Optional[str] = None,
) -> list[FundingRequest]:
    """List funding requests, optionally filtered."""
    query = db.query(FundingRequest)
    if engine_id is not None:
        query = query.filter(FundingRequest.engine_id == engine_id)
    if status is not None:
        query = query.filter(FundingRequest.status == status)
    return query.order_by(FundingRequest.created_at.desc()).all()


# ── Token Management ─────────────────────────────────────────────────────────

def _credit_tokens(
    db: Session,
    engine_id: int,
    amount: float,
    description: str,
    funding_request_id: Optional[int] = None,
) -> TokenTransaction:
    """Credit tokens to an engine's balance."""
    engine = db.query(AIEngine).filter(AIEngine.id == engine_id).first()
    if not engine:
        raise ValueError(f"Engine {engine_id} not found")

    engine.token_balance += amount
    new_balance = engine.token_balance

    txn = TokenTransaction(
        engine_id=engine_id,
        amount=amount,
        balance_after=new_balance,
        description=description,
        funding_request_id=funding_request_id,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def debit_tokens(
    db: Session,
    engine_id: int,
    amount: float,
    description: str,
) -> TokenTransaction:
    """Debit tokens from an engine's balance."""
    engine = db.query(AIEngine).filter(AIEngine.id == engine_id).first()
    if not engine:
        raise ValueError(f"Engine {engine_id} not found")

    if engine.token_balance < amount:
        raise ValueError(f"Insufficient balance: {engine.token_balance} < {amount}")

    engine.token_balance -= amount
    engine.tokens_consumed += amount
    new_balance = engine.token_balance

    txn = TokenTransaction(
        engine_id=engine_id,
        amount=-amount,
        balance_after=new_balance,
        description=description,
    )
    db.add(txn)
    db.commit()
    db.refresh(txn)
    return txn


def get_token_history(
    db: Session,
    engine_id: int,
    limit: int = 50,
) -> list[TokenTransaction]:
    """Get token transaction history for an engine."""
    return (
        db.query(TokenTransaction)
        .filter(TokenTransaction.engine_id == engine_id)
        .order_by(TokenTransaction.created_at.desc())
        .limit(limit)
        .all()
    )


# ── Autonomous Funding Identification ────────────────────────────────────────

def analyze_funding_needs(db: Session, engine_id: int) -> dict:
    """Analyze an engine's funding needs based on consumption patterns and balance."""
    engine = db.query(AIEngine).filter(AIEngine.id == engine_id).first()
    if not engine:
        raise ValueError(f"Engine {engine_id} not found")

    # Calculate burn rate from recent transactions
    recent_debits = (
        db.query(TokenTransaction)
        .filter(TokenTransaction.engine_id == engine_id, TokenTransaction.amount < 0)
        .order_by(TokenTransaction.created_at.desc())
        .limit(30)
        .all()
    )

    total_consumed = sum(abs(t.amount) for t in recent_debits)
    avg_daily_burn = total_consumed / max(len(recent_debits), 1)
    days_remaining = engine.token_balance / avg_daily_burn if avg_daily_burn > 0 else float("inf")

    # Determine urgency
    if days_remaining < 7:
        urgency = "critical"
    elif days_remaining < 30:
        urgency = "high"
    elif days_remaining < 90:
        urgency = "medium"
    else:
        urgency = "low"

    # Suggest funding types based on needs
    suggested_strategies = _suggest_funding_types(engine, days_remaining, total_consumed)

    return {
        "engine_id": engine_id,
        "engine_name": engine.name,
        "current_balance": engine.token_balance,
        "total_consumed": engine.tokens_consumed,
        "avg_daily_burn": round(avg_daily_burn, 2),
        "estimated_days_remaining": round(days_remaining, 1) if days_remaining != float("inf") else None,
        "urgency": urgency,
        "suggested_strategies": suggested_strategies,
        "recommended_funding_amount": round(avg_daily_burn * 90, 2),  # 90-day runway
    }


def _suggest_funding_types(engine: AIEngine, days_remaining: float, total_consumed: float) -> list[dict]:
    """Generate funding strategy suggestions based on engine needs."""
    strategies = []

    if days_remaining < 30:
        strategies.append({
            "type": FundingTypeEnum.token_purchase.value,
            "priority": "high",
            "rationale": "Immediate token purchase needed to maintain operations",
        })

    strategies.append({
        "type": FundingTypeEnum.subscription_revenue.value,
        "priority": "medium",
        "rationale": "Recurring revenue from premium subscriptions provides stable funding",
    })

    strategies.append({
        "type": FundingTypeEnum.grant.value,
        "priority": "medium",
        "rationale": "AI/tech grants can provide substantial non-dilutive funding",
    })

    strategies.append({
        "type": FundingTypeEnum.partnership.value,
        "priority": "medium",
        "rationale": "Strategic partnerships can provide resources and shared costs",
    })

    strategies.append({
        "type": FundingTypeEnum.crowdfunding.value,
        "priority": "low",
        "rationale": "Community-driven funding with marketing benefits",
    })

    strategies.append({
        "type": FundingTypeEnum.sponsorship.value,
        "priority": "low",
        "rationale": "Sponsor relationships provide funding with brand visibility benefits",
    })

    return strategies
