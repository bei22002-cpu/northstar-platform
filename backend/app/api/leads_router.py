from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadOut, LeadSearchQuery
from app.services.lead_score import score_lead
from app.services.lead_classifier import classify_lead
from app.services.lead_scraper import scrape_leads

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("/", response_model=List[LeadOut])
def list_leads(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Lead).offset(skip).limit(limit).all()


@router.post("/", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_lead(lead_data: LeadCreate, db: Session = Depends(get_db)):
    data_dict = lead_data.model_dump()
    score = score_lead(data_dict)
    classification = classify_lead(score)

    lead = Lead(
        **data_dict,
        score=score,
        classification=classification,
        source="manual",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@router.post("/search", response_model=List[LeadOut], status_code=status.HTTP_201_CREATED)
def search_and_import_leads(query: LeadSearchQuery, db: Session = Depends(get_db)):
    """Search public web sources via SerpAPI, score, classify, and persist leads."""
    raw_leads = scrape_leads(
        query=query.query,
        location=query.location,
        industry=query.industry,
        num_results=query.num_results,
    )

    saved = []
    for raw in raw_leads:
        score = score_lead(raw)
        classification = classify_lead(score)
        lead = Lead(
            company_name=raw["company_name"],
            website=raw.get("website"),
            notes=raw.get("notes"),
            source=raw.get("source", "serpapi"),
            industry=raw.get("industry"),
            contact_name=raw.get("contact_name"),
            email=raw.get("email"),
            score=score,
            classification=classification,
        )
        db.add(lead)
        saved.append(lead)

    db.commit()
    for lead in saved:
        db.refresh(lead)

    return saved
