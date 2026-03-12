from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
import enum

from app.core.database import Base


class ToneEnum(str, enum.Enum):
    executive = "executive"
    professional = "professional"
    casual = "casual"


class OutreachStatusEnum(str, enum.Enum):
    draft = "draft"
    approved = "approved"
    sent = "sent"


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    tone = Column(Enum(ToneEnum), default=ToneEnum.professional)
    status = Column(Enum(OutreachStatusEnum), default=OutreachStatusEnum.draft)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(Integer, primary_key=True, index=True)
    outreach_id = Column(Integer, ForeignKey("outreach_messages.id"), nullable=False, index=True)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    sequence_number = Column(Integer, default=1)
    status = Column(Enum(OutreachStatusEnum), default=OutreachStatusEnum.draft)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
