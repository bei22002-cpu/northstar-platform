from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadUpdate, LeadResponse
from app.services.lead_score import score_lead
from app.services.lead_classifier import classify_lead
from app.services.lead_scraper import search_leads

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("/", response_model=LeadResponse, status_code=201)
def create_lead(lead_data: LeadCreate, db: Session = Depends(get_db)):
    score = score_lead(
        company_name=lead_data.company_name,
        industry=lead_data.industry,
        website=lead_data.website,
        email=lead_data.email,
    )
    classification = classify_lead(score)

    lead = Lead(
        **lead_data.model_dump(),
        score=score,
        classification=classification,
        source="manual",
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.get("/", response_model=List[LeadResponse])
def list_leads(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return db.query(Lead).offset(skip).limit(limit).all()


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException, status
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: int, lead_data: LeadUpdate, db: Session = Depends(get_db)):
    from fastapi import HTTPException, status
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    update_data = lead_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)

    lead.score = score_lead(
        company_name=lead.company_name,
        industry=lead.industry,
        website=lead.website,
        email=lead.email,
    )
    lead.classification = classify_lead(lead.score)

    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=204)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    from fastapi import HTTPException, status
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    db.delete(lead)
    db.commit()


@router.get("/search/public", response_model=List[dict])
def search_public_leads(
    q: str = Query(..., description="Search query for public lead discovery"),
    num: int = Query(10, ge=1, le=50),
):
    """
    Search for leads using publicly accessible sources via SerpAPI.
    Results require human review before import.
    """
    return search_leads(query=q, num_results=num)
