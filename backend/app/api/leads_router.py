from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.lead import Lead
from app.models.user import User
from app.schemas.lead import LeadCreate, LeadRead

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=List[LeadRead])
def list_leads(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all leads. Requires authentication."""
    return db.query(Lead).all()


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a single lead by ID. Requires authentication."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return lead


@router.post("", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead(
    lead_in: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new lead. Requires authentication."""
    lead = Lead(**lead_in.model_dump())
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a lead by ID. Requires authentication."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    db.delete(lead)
    db.commit()
