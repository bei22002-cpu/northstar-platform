from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BusinessIdeaCreate(BaseModel):
    title: str
    description: str
    industry: str
    target_market: Optional[str] = None
    budget_range: Optional[str] = None


class BusinessIdeaUpdate(BaseModel):
    status: Optional[str] = None
    feedback: Optional[str] = None


class BusinessIdeaOut(BaseModel):
    id: int
    user_id: int
    title: str
    description: str
    industry: str
    target_market: Optional[str] = None
    budget_range: Optional[str] = None
    status: str
    ai_analysis: Optional[str] = None
    funding_strategy: Optional[str] = None
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
