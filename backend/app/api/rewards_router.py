"""API router for user rewards and engagement-driven funding."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.reward import RewardTransactionCreate, RewardTransactionOut, UserRewardBalanceOut
from app.services import reward_service

router = APIRouter(prefix="/rewards", tags=["Rewards"])


@router.get("/balance/{user_id}", response_model=Optional[UserRewardBalanceOut])
def get_balance(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get reward balance for a user."""
    balance = reward_service.get_user_balance(db, user_id=user_id)
    if not balance:
        return None
    return balance


@router.post("/award", response_model=RewardTransactionOut, status_code=status.HTTP_201_CREATED)
def award_tokens(payload: RewardTransactionCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Award tokens to a user for an engagement action."""
    return reward_service.award_tokens(
        db=db,
        user_id=payload.user_id,
        reward_type=payload.reward_type,
        description=payload.description,
        tokens=payload.tokens_earned,
        metadata_json=payload.metadata_json,
    )


@router.post("/spend")
def spend_tokens(
    user_id: int = Query(...),
    amount: float = Query(..., gt=0),
    description: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Spend user tokens on premium services."""
    try:
        txn = reward_service.spend_tokens(db, user_id=user_id, amount=amount, description=description)
        return {"status": "ok", "transaction_id": txn.id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/transactions/{user_id}", response_model=list[RewardTransactionOut])
def get_transactions(
    user_id: int,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get reward transaction history for a user."""
    return reward_service.get_user_transactions(db, user_id=user_id, limit=limit)


@router.get("/leaderboard", response_model=list[UserRewardBalanceOut])
def leaderboard(
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the top users by lifetime earnings."""
    return reward_service.get_leaderboard(db, limit=limit)


@router.get("/revenue-models")
def revenue_models():
    """Get available revenue model configurations."""
    return reward_service.get_revenue_models()
