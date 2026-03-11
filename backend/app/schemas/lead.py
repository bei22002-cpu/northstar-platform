from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LeadCreate(BaseModel):
    company_name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    company_name: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None


class LeadResponse(BaseModel):
    id: int
    company_name: str
    contact_name: Optional[str]
    email: Optional[str]
    website: Optional[str]
    industry: Optional[str]
    score: float
    classification: Optional[str]
    source: Optional[str]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
