from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class ToneEnum(str, Enum):
    executive = "executive"
    professional = "professional"
    casual = "casual"


class OutreachStatusEnum(str, Enum):
    draft = "draft"
    approved = "approved"
    sent = "sent"


class OutreachMessageCreate(BaseModel):
    lead_id: int
    tone: ToneEnum = ToneEnum.professional


class OutreachMessageUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    tone: Optional[ToneEnum] = None
    status: Optional[OutreachStatusEnum] = None


class OutreachMessageResponse(BaseModel):
    id: int
    lead_id: int
    subject: str
    body: str
    tone: ToneEnum
    status: OutreachStatusEnum
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class FollowUpCreate(BaseModel):
    outreach_id: int
    sequence_number: int = 1


class FollowUpResponse(BaseModel):
    id: int
    outreach_id: int
    subject: str
    body: str
    sequence_number: int
    status: OutreachStatusEnum
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}


class ApproveRequest(BaseModel):
    message_id: int


class OutreachWithFollowUps(BaseModel):
    message: OutreachMessageResponse
    follow_ups: List[FollowUpResponse] = []
