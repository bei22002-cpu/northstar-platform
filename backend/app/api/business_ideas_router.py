"""API router for business idea submission and management."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.business_idea import BusinessIdea, IdeaStatusEnum
from app.models.user import User
from app.schemas.business_idea import BusinessIdeaCreate, BusinessIdeaOut, BusinessIdeaUpdate
from app.services.ai_analysis import generate_analysis, suggest_funding

router = APIRouter(prefix="/business-ideas", tags=["Business Ideas"])


@router.get("/", response_model=list[BusinessIdeaOut])
def list_ideas(
    industry: Optional[str] = Query(None),
    idea_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List business ideas with optional filters."""
    query = db.query(BusinessIdea)
    query = query.filter(BusinessIdea.user_id == current_user.id)
    if industry is not None:
        query = query.filter(BusinessIdea.industry == industry)
    if idea_status is not None:
        query = query.filter(BusinessIdea.status == idea_status)
    return query.order_by(BusinessIdea.created_at.desc()).all()


@router.post("/", response_model=BusinessIdeaOut, status_code=status.HTTP_201_CREATED)
def submit_idea(
    payload: BusinessIdeaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a new business idea for AI analysis."""
    idea = BusinessIdea(
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        industry=payload.industry,
        target_market=payload.target_market,
        budget_range=payload.budget_range,
    )

    # Generate AI analysis (uses OpenAI if configured, else rule-based fallback)
    idea.ai_analysis = json.dumps(generate_analysis(
        title=payload.title,
        description=payload.description,
        industry=payload.industry,
        target_market=payload.target_market,
        budget_range=payload.budget_range,
    ))
    idea.funding_strategy = json.dumps(suggest_funding(
        title=payload.title,
        description=payload.description,
        industry=payload.industry,
        target_market=payload.target_market,
        budget_range=payload.budget_range,
    ))
    idea.status = IdeaStatusEnum.strategies_generated.value

    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea


@router.get("/{idea_id}", response_model=BusinessIdeaOut)
def get_idea(idea_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a specific business idea by ID."""
    idea = db.query(BusinessIdea).filter(BusinessIdea.id == idea_id, BusinessIdea.user_id == current_user.id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Business idea not found")
    return idea


@router.patch("/{idea_id}", response_model=BusinessIdeaOut)
def update_idea(idea_id: int, payload: BusinessIdeaUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update a business idea (status or feedback)."""
    idea = db.query(BusinessIdea).filter(BusinessIdea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Business idea not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(idea, field, value)

    db.commit()
    db.refresh(idea)
    return idea


@router.delete("/{idea_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_idea(idea_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete a business idea."""
    idea = db.query(BusinessIdea).filter(BusinessIdea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Business idea not found")
    db.delete(idea)
    db.commit()


@router.get("/industries/list")
def list_industries():
    """Get available industry categories."""
    return {
        "industries": [
            {"value": "technology", "label": "Technology & Software"},
            {"value": "retail", "label": "Retail & E-Commerce"},
            {"value": "services", "label": "Professional Services"},
            {"value": "healthcare", "label": "Healthcare & Biotech"},
            {"value": "finance", "label": "Finance & Fintech"},
            {"value": "education", "label": "Education & EdTech"},
            {"value": "food", "label": "Food & Beverage"},
            {"value": "manufacturing", "label": "Manufacturing"},
            {"value": "real_estate", "label": "Real Estate & PropTech"},
            {"value": "media", "label": "Media & Entertainment"},
            {"value": "sustainability", "label": "Sustainability & CleanTech"},
            {"value": "other", "label": "Other"},
        ]
    }
