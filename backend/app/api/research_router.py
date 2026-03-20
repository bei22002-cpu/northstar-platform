"""API router for funding research and insight management."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.research import ResearchInsightCreate, ResearchInsightOut
from app.services import research_service

router = APIRouter(prefix="/research", tags=["Research"])


@router.get("/insights", response_model=list[ResearchInsightOut])
def list_insights(
    engine_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    viability: Optional[str] = Query(None),
    min_relevance: float = Query(0.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List research insights with optional filters."""
    return research_service.get_insights(
        db, engine_id=engine_id, category=category, viability=viability, min_relevance=min_relevance
    )


@router.post("/insights", response_model=ResearchInsightOut, status_code=status.HTTP_201_CREATED)
def create_insight(payload: ResearchInsightCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Record a new research insight from an AI engine."""
    try:
        return research_service.create_insight(
            db=db,
            engine_id=payload.engine_id,
            category=payload.category,
            title=payload.title,
            summary=payload.summary,
            source_url=payload.source_url,
            viability=payload.viability or "unknown",
            estimated_amount=payload.estimated_amount,
            relevance_score=payload.relevance_score,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/top-opportunities", response_model=list[ResearchInsightOut])
def top_opportunities(
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the most promising funding opportunities."""
    return research_service.get_top_opportunities(db, limit=limit)


@router.get("/report")
def funding_report(
    engine_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a comprehensive funding research report."""
    return research_service.generate_funding_research_report(db, engine_id=engine_id)


@router.get("/templates")
def get_templates():
    """Get pre-built funding research templates and categories."""
    return research_service.get_research_templates()
