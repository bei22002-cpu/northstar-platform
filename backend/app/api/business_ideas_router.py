"""API router for business idea submission and management."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.business_idea import BusinessIdea, IdeaStatusEnum
from app.schemas.business_idea import BusinessIdeaCreate, BusinessIdeaOut, BusinessIdeaUpdate

router = APIRouter(prefix="/business-ideas", tags=["Business Ideas"])


@router.get("/", response_model=list[BusinessIdeaOut])
def list_ideas(
    user_id: Optional[int] = Query(None),
    industry: Optional[str] = Query(None),
    idea_status: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    """List business ideas with optional filters."""
    query = db.query(BusinessIdea)
    if user_id is not None:
        query = query.filter(BusinessIdea.user_id == user_id)
    if industry is not None:
        query = query.filter(BusinessIdea.industry == industry)
    if idea_status is not None:
        query = query.filter(BusinessIdea.status == idea_status)
    return query.order_by(BusinessIdea.created_at.desc()).all()


@router.post("/", response_model=BusinessIdeaOut, status_code=status.HTTP_201_CREATED)
def submit_idea(
    payload: BusinessIdeaCreate,
    user_id: int = Query(..., description="The ID of the user submitting the idea"),
    db: Session = Depends(get_db),
):
    """Submit a new business idea for AI analysis."""
    idea = BusinessIdea(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        industry=payload.industry,
        target_market=payload.target_market,
        budget_range=payload.budget_range,
    )

    # Generate initial AI analysis
    idea.ai_analysis = json.dumps(_generate_analysis(payload))
    idea.funding_strategy = json.dumps(_suggest_funding(payload))
    idea.status = IdeaStatusEnum.strategies_generated.value

    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea


@router.get("/{idea_id}", response_model=BusinessIdeaOut)
def get_idea(idea_id: int, db: Session = Depends(get_db)):
    """Get a specific business idea by ID."""
    idea = db.query(BusinessIdea).filter(BusinessIdea.id == idea_id).first()
    if not idea:
        raise HTTPException(status_code=404, detail="Business idea not found")
    return idea


@router.patch("/{idea_id}", response_model=BusinessIdeaOut)
def update_idea(idea_id: int, payload: BusinessIdeaUpdate, db: Session = Depends(get_db)):
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
def delete_idea(idea_id: int, db: Session = Depends(get_db)):
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


# ── Internal analysis helpers ────────────────────────────────────────────────

def _generate_analysis(payload: BusinessIdeaCreate) -> dict:
    """Generate a structured AI analysis of the business idea."""
    industry_insights = {
        "technology": {
            "market_trend": "Growing rapidly with AI/ML adoption",
            "competition_level": "High",
            "entry_barrier": "Medium-High",
            "key_success_factors": ["Innovation speed", "Technical talent", "Scalable architecture"],
        },
        "retail": {
            "market_trend": "Shifting to omnichannel and D2C models",
            "competition_level": "Very High",
            "entry_barrier": "Low-Medium",
            "key_success_factors": ["Customer experience", "Supply chain", "Brand building"],
        },
        "services": {
            "market_trend": "Increasing demand for specialized consulting",
            "competition_level": "Medium",
            "entry_barrier": "Low",
            "key_success_factors": ["Expertise", "Network", "Client relationships"],
        },
        "healthcare": {
            "market_trend": "Digital health and telehealth expansion",
            "competition_level": "Medium-High",
            "entry_barrier": "High",
            "key_success_factors": ["Regulatory compliance", "Clinical validation", "Trust"],
        },
        "finance": {
            "market_trend": "Fintech disruption and embedded finance",
            "competition_level": "High",
            "entry_barrier": "High",
            "key_success_factors": ["Regulatory navigation", "Security", "User trust"],
        },
    }

    base_insight = industry_insights.get(payload.industry, {
        "market_trend": "Emerging opportunities available",
        "competition_level": "Varies",
        "entry_barrier": "Medium",
        "key_success_factors": ["Market research", "Execution speed", "Customer focus"],
    })

    return {
        "industry_analysis": base_insight,
        "recommended_next_steps": [
            "Validate the idea with potential customers",
            "Build a minimum viable product (MVP)",
            "Identify key competitors and differentiators",
            "Develop a go-to-market strategy",
            "Secure initial funding or bootstrap",
        ],
        "risk_factors": [
            "Market timing and readiness",
            "Funding availability",
            "Team capability gaps",
            "Regulatory requirements",
        ],
        "estimated_timeline": "3-6 months to MVP, 12-18 months to market fit",
    }


def _suggest_funding(payload: BusinessIdeaCreate) -> dict:
    """Generate funding strategy recommendations based on the business idea."""
    strategies = [
        {
            "type": "bootstrapping",
            "description": "Self-fund initial development using personal savings or revenue",
            "suitability": "High for low-cost startups",
            "typical_amount": "$0 - $50,000",
        },
        {
            "type": "angel_investment",
            "description": "Seek funding from angel investors in your industry",
            "suitability": "Medium-High for tech startups",
            "typical_amount": "$25,000 - $500,000",
        },
        {
            "type": "crowdfunding",
            "description": "Launch a crowdfunding campaign to validate demand and raise funds",
            "suitability": "High for consumer products",
            "typical_amount": "$10,000 - $250,000",
        },
        {
            "type": "grants",
            "description": "Apply for government or private grants for innovation",
            "suitability": "Medium for technology companies",
            "typical_amount": "$10,000 - $2,000,000",
        },
        {
            "type": "venture_capital",
            "description": "Pitch to VC firms for larger funding rounds",
            "suitability": "High for scalable tech businesses",
            "typical_amount": "$500,000 - $10,000,000+",
        },
    ]

    return {
        "recommended_strategies": strategies,
        "primary_recommendation": strategies[0]["type"] if payload.budget_range in [None, "", "0-50k"] else strategies[1]["type"],
        "funding_readiness_checklist": [
            "Business plan or pitch deck prepared",
            "Market research completed",
            "MVP or prototype available",
            "Financial projections ready",
            "Team assembled or identified",
        ],
    }
