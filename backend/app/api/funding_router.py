"""API router for funding requests, token management, and funding analysis."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.funding import FundingRequestCreate, FundingRequestOut, FundingRequestUpdate, TokenTransactionOut
from app.services import funding_strategy

router = APIRouter(prefix="/funding", tags=["Funding"])


# ── Funding Requests ─────────────────────────────────────────────────────────

@router.get("/requests", response_model=list[FundingRequestOut])
def list_funding_requests(
    engine_id: Optional[int] = Query(None),
    request_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all funding requests with optional filters."""
    return funding_strategy.get_funding_requests(db, engine_id=engine_id, status=request_status)


@router.post("/requests", response_model=FundingRequestOut, status_code=status.HTTP_201_CREATED)
def create_funding_request(payload: FundingRequestCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new funding request from an AI engine."""
    try:
        return funding_strategy.create_funding_request(
            db=db,
            engine_id=payload.engine_id,
            funding_type=payload.funding_type,
            title=payload.title,
            description=payload.description,
            amount_requested=payload.amount_requested,
            justification=payload.justification,
            projected_roi=payload.projected_roi,
            operational_cost=payload.operational_cost,
            strategy_details=payload.strategy_details,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/requests/{request_id}", response_model=FundingRequestOut)
def update_funding_request(
    request_id: int,
    payload: FundingRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a funding request's status or secured amount."""
    try:
        return funding_strategy.update_funding_status(
            db=db,
            request_id=request_id,
            status=payload.status or "proposed",
            amount_secured=payload.amount_secured,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Token Management ─────────────────────────────────────────────────────────

@router.get("/tokens/{engine_id}/history", response_model=list[TokenTransactionOut])
def get_token_history(
    engine_id: int,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get token transaction history for an engine."""
    return funding_strategy.get_token_history(db, engine_id=engine_id, limit=limit)


@router.post("/tokens/{engine_id}/debit", response_model=TokenTransactionOut)
def debit_engine_tokens(
    engine_id: int,
    amount: float = Query(..., gt=0),
    description: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Debit tokens from an engine's balance."""
    try:
        return funding_strategy.debit_tokens(db, engine_id=engine_id, amount=amount, description=description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Funding Analysis ─────────────────────────────────────────────────────────

@router.get("/analysis/{engine_id}")
def analyze_engine_funding(engine_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Analyze funding needs and get strategy recommendations for an engine."""
    try:
        return funding_strategy.analyze_funding_needs(db, engine_id=engine_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
