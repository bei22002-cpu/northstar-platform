"""Service for AI engine funding research mechanisms.

Provides functionality for AI engines to research funding options including
grants, sponsorships, partnerships, crowdfunding, and innovative models.
"""

import json
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ai_engine import AIEngine
from app.models.research import ResearchInsight, ResearchCategoryEnum, ViabilityEnum


def create_insight(
    db: Session,
    engine_id: int,
    category: str,
    title: str,
    summary: str,
    source_url: Optional[str] = None,
    viability: str = "unknown",
    estimated_amount: Optional[float] = None,
    actionable_steps: Optional[list[str]] = None,
    relevance_score: float = 0.0,
) -> ResearchInsight:
    """Record a new research insight discovered by an AI engine."""
    engine = db.query(AIEngine).filter(AIEngine.id == engine_id).first()
    if not engine:
        raise ValueError(f"Engine {engine_id} not found")

    insight = ResearchInsight(
        engine_id=engine_id,
        category=category,
        title=title,
        summary=summary,
        source_url=source_url,
        viability=viability,
        estimated_amount=estimated_amount,
        actionable_steps=json.dumps(actionable_steps) if actionable_steps else None,
        relevance_score=relevance_score,
    )
    db.add(insight)
    db.commit()
    db.refresh(insight)
    return insight


def get_insights(
    db: Session,
    engine_id: Optional[int] = None,
    category: Optional[str] = None,
    viability: Optional[str] = None,
    min_relevance: float = 0.0,
) -> list[ResearchInsight]:
    """Retrieve research insights with optional filters."""
    query = db.query(ResearchInsight)

    if engine_id is not None:
        query = query.filter(ResearchInsight.engine_id == engine_id)
    if category is not None:
        query = query.filter(ResearchInsight.category == category)
    if viability is not None:
        query = query.filter(ResearchInsight.viability == viability)
    if min_relevance > 0:
        query = query.filter(ResearchInsight.relevance_score >= min_relevance)

    return query.order_by(ResearchInsight.relevance_score.desc()).all()


def get_top_opportunities(db: Session, limit: int = 10) -> list[ResearchInsight]:
    """Get the most promising funding opportunities across all engines."""
    return (
        db.query(ResearchInsight)
        .filter(ResearchInsight.viability.in_([ViabilityEnum.high.value, ViabilityEnum.medium.value]))
        .order_by(ResearchInsight.relevance_score.desc())
        .limit(limit)
        .all()
    )


def generate_funding_research_report(db: Session, engine_id: Optional[int] = None) -> dict:
    """Generate a summary research report of funding options."""
    insights = get_insights(db, engine_id=engine_id)

    by_category: dict[str, list] = {}
    for insight in insights:
        cat = insight.category
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append({
            "title": insight.title,
            "viability": insight.viability,
            "estimated_amount": insight.estimated_amount,
            "relevance_score": insight.relevance_score,
        })

    total_potential = sum(
        i.estimated_amount for i in insights if i.estimated_amount is not None
    )

    high_viability_count = sum(1 for i in insights if i.viability == ViabilityEnum.high.value)
    medium_viability_count = sum(1 for i in insights if i.viability == ViabilityEnum.medium.value)

    return {
        "total_insights": len(insights),
        "total_potential_funding": round(total_potential, 2),
        "high_viability_count": high_viability_count,
        "medium_viability_count": medium_viability_count,
        "by_category": by_category,
        "top_opportunities": [
            {
                "id": i.id,
                "title": i.title,
                "category": i.category,
                "viability": i.viability,
                "estimated_amount": i.estimated_amount,
                "relevance_score": i.relevance_score,
            }
            for i in get_top_opportunities(db, limit=5)
        ],
    }


# ── Pre-built Research Templates ─────────────────────────────────────────────

FUNDING_RESEARCH_TEMPLATES = {
    "grants": {
        "description": "Government and private grants for AI/technology projects",
        "sources": [
            "SBIR/STTR programs",
            "NSF grants",
            "DOE technology grants",
            "Private foundation technology grants",
            "State-level innovation funds",
        ],
        "typical_range": "$10,000 - $2,000,000",
        "timeline": "3-12 months application to award",
    },
    "crowdfunding": {
        "description": "Community-driven funding through platforms",
        "sources": [
            "Kickstarter campaigns",
            "Indiegogo projects",
            "Republic equity crowdfunding",
            "WeFunder campaigns",
            "GoFundMe for business",
        ],
        "typical_range": "$5,000 - $500,000",
        "timeline": "1-3 months campaign duration",
    },
    "partnerships": {
        "description": "Strategic alliances with complementary organizations",
        "sources": [
            "Technology company partnerships",
            "University research collaborations",
            "Industry consortium membership",
            "API/platform partnerships",
            "Joint venture agreements",
        ],
        "typical_range": "$25,000 - $5,000,000",
        "timeline": "1-6 months negotiation",
    },
    "sponsorships": {
        "description": "Corporate sponsorship for visibility and access",
        "sources": [
            "Technology company sponsorships",
            "Event sponsorships with tech focus",
            "Content/media sponsorships",
            "Research sponsorships",
            "Educational sponsorships",
        ],
        "typical_range": "$5,000 - $250,000",
        "timeline": "1-3 months negotiation",
    },
    "innovative_models": {
        "description": "Novel funding approaches suited for AI/tech",
        "sources": [
            "Revenue-based financing",
            "Token-based ecosystem economics",
            "Data licensing agreements",
            "API usage fees",
            "White-label licensing",
        ],
        "typical_range": "Varies widely",
        "timeline": "Ongoing revenue stream",
    },
}


def get_research_templates() -> dict:
    """Return pre-built research templates for funding categories."""
    return FUNDING_RESEARCH_TEMPLATES
