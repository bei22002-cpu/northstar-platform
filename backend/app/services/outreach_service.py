from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List

from app.models.outreach import OutreachMessage, FollowUp, OutreachStatusEnum
from app.models.lead import Lead
from app.schemas.outreach import OutreachMessageCreate, OutreachMessageUpdate, FollowUpCreate
from app.services.message_personalizer import personalize_message
from app.services.followup_generator import generate_followup


def create_outreach_message(db: Session, data: OutreachMessageCreate) -> OutreachMessage:
    lead = db.query(Lead).filter(Lead.id == data.lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

    personalized = personalize_message(
        company_name=lead.company_name,
        contact_name=lead.contact_name,
        tone=data.tone.value,
    )

    msg = OutreachMessage(
        lead_id=data.lead_id,
        subject=personalized["subject"],
        body=personalized["body"],
        tone=data.tone,
        status=OutreachStatusEnum.draft,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def list_outreach_messages(db: Session, skip: int = 0, limit: int = 100) -> List[OutreachMessage]:
    return db.query(OutreachMessage).offset(skip).limit(limit).all()


def get_outreach_message(db: Session, message_id: int) -> OutreachMessage:
    msg = db.query(OutreachMessage).filter(OutreachMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outreach message not found")
    return msg


def update_outreach_message(db: Session, message_id: int, data: OutreachMessageUpdate) -> OutreachMessage:
    msg = get_outreach_message(db, message_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(msg, field, value)
    db.commit()
    db.refresh(msg)
    return msg


def approve_outreach_message(db: Session, message_id: int) -> OutreachMessage:
    """
    Human-approval step: marks a draft message as approved for manual sending.
    The platform never sends messages automatically — all sends are manual.
    """
    msg = get_outreach_message(db, message_id)
    if msg.status != OutreachStatusEnum.draft:
        status_display = getattr(msg.status, "value", msg.status)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Message is already in '{status_display}' state",
        )
    msg.status = OutreachStatusEnum.approved
    db.commit()
    db.refresh(msg)
    return msg


def mark_outreach_sent(db: Session, message_id: int) -> OutreachMessage:
    """
    Mark a message as sent after the user has manually sent it.
    """
    msg = get_outreach_message(db, message_id)
    if msg.status != OutreachStatusEnum.approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message must be approved before marking as sent",
        )
    msg.status = OutreachStatusEnum.sent
    db.commit()
    db.refresh(msg)
    return msg


def create_followup(db: Session, data: FollowUpCreate) -> FollowUp:
    msg = get_outreach_message(db, data.outreach_id)
    lead = db.query(Lead).filter(Lead.id == msg.lead_id).first()

    generated = generate_followup(
        company_name=lead.company_name if lead else "your company",
        contact_name=lead.contact_name if lead else None,
        sequence_number=data.sequence_number,
    )

    followup = FollowUp(
        outreach_id=data.outreach_id,
        subject=generated["subject"],
        body=generated["body"],
        sequence_number=data.sequence_number,
        status=OutreachStatusEnum.draft,
    )
    db.add(followup)
    db.commit()
    db.refresh(followup)
    return followup


def list_followups(db: Session, outreach_id: int) -> List[FollowUp]:
    return db.query(FollowUp).filter(FollowUp.outreach_id == outreach_id).all()
