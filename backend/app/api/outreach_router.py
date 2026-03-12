from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.lead import Lead
from app.models.user import User
from app.schemas.outreach import (
    OutreachFollowupsRequest,
    OutreachFollowupsResponse,
    OutreachGenerateRequest,
    OutreachGenerateResponse,
)
from app.services.outreach_writer import generate_followups, generate_outreach_message

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.post("/generate", response_model=OutreachGenerateResponse)
def outreach_generate(
    req: OutreachGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a personalised outreach subject and body for the given lead.

    Requires authentication. Returns generated content only — does NOT send email.
    """
    lead = db.query(Lead).filter(Lead.id == req.lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    result = generate_outreach_message(lead, req.tone, req.service_focus, req.extra_context)
    return result


@router.post("/followups", response_model=OutreachFollowupsResponse)
def outreach_followups(
    req: OutreachFollowupsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a 3-step follow-up email sequence for the given lead.

    Requires authentication. Returns generated content only — does NOT send email.
    """
    lead = db.query(Lead).filter(Lead.id == req.lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    result = generate_followups(lead, req.tone, req.service_focus)
    return result
