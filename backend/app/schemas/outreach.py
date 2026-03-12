from typing import Literal, Optional

from pydantic import BaseModel


class OutreachGenerateRequest(BaseModel):
    lead_id: int
    tone: Literal["executive", "professional", "casual"]
    service_focus: Literal["operations", "strategy", "scaling"]
    extra_context: Optional[str] = None


class OutreachGenerateResponse(BaseModel):
    subject: str
    message: str


class OutreachFollowupsRequest(BaseModel):
    lead_id: int
    tone: Literal["executive", "professional", "casual"]
    service_focus: Literal["operations", "strategy", "scaling"]


class OutreachFollowupsResponse(BaseModel):
    followup_1: str
    followup_2: str
    followup_3: str
