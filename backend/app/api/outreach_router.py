from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.outreach import (
    OutreachMessageCreate,
    OutreachMessageUpdate,
    OutreachMessageResponse,
    FollowUpCreate,
    FollowUpResponse,
    ApproveRequest,
    OutreachWithFollowUps,
)
from app.services import outreach_service

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.post("/messages", response_model=OutreachMessageResponse, status_code=201)
def create_message(data: OutreachMessageCreate, db: Session = Depends(get_db)):
    """
    Generate a personalized outreach message for a lead.
    The message is created as a draft pending human review and approval.
    """
    return outreach_service.create_outreach_message(db, data)


@router.get("/messages", response_model=List[OutreachMessageResponse])
def list_messages(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return outreach_service.list_outreach_messages(db, skip=skip, limit=limit)


@router.get("/messages/{message_id}", response_model=OutreachWithFollowUps)
def get_message(message_id: int, db: Session = Depends(get_db)):
    msg = outreach_service.get_outreach_message(db, message_id)
    follow_ups = outreach_service.list_followups(db, message_id)
    return OutreachWithFollowUps(message=msg, follow_ups=follow_ups)


@router.put("/messages/{message_id}", response_model=OutreachMessageResponse)
def update_message(message_id: int, data: OutreachMessageUpdate, db: Session = Depends(get_db)):
    return outreach_service.update_outreach_message(db, message_id, data)


@router.post("/messages/{message_id}/approve", response_model=OutreachMessageResponse)
def approve_message(message_id: int, db: Session = Depends(get_db)):
    """
    Human-approval step: approve a draft message for manual sending.
    NorthStar never sends messages automatically.
    """
    return outreach_service.approve_outreach_message(db, message_id)


@router.post("/messages/{message_id}/sent", response_model=OutreachMessageResponse)
def mark_sent(message_id: int, db: Session = Depends(get_db)):
    """
    Mark a message as sent after you have manually dispatched it.
    """
    return outreach_service.mark_outreach_sent(db, message_id)


@router.post("/followups", response_model=FollowUpResponse, status_code=201)
def create_followup(data: FollowUpCreate, db: Session = Depends(get_db)):
    """
    Generate a follow-up message for an existing outreach thread.
    """
    return outreach_service.create_followup(db, data)


@router.get("/messages/{message_id}/followups", response_model=List[FollowUpResponse])
def list_followups(message_id: int, db: Session = Depends(get_db)):
    return outreach_service.list_followups(db, message_id)
