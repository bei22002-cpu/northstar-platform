from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LeadBase(BaseModel):
    company_name: str
    contact_name: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    notes: Optional[str] = None


class LeadCreate(LeadBase):
    pass


class LeadOut(LeadBase):
    id: int
    score: float
    classification: Optional[str] = None
    source: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class LeadSearchQuery(BaseModel):
    query: str
    location: Optional[str] = None
    industry: Optional[str] = None
    num_results: int = 10
