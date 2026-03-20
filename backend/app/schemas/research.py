from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ResearchInsightCreate(BaseModel):
    engine_id: int
    category: str
    title: str
    summary: str
    source_url: Optional[str] = None
    viability: Optional[str] = "unknown"
    estimated_amount: Optional[float] = None
    actionable_steps: Optional[str] = None  # JSON array
    relevance_score: float = 0.0


class ResearchInsightOut(BaseModel):
    id: int
    engine_id: int
    category: str
    title: str
    summary: str
    source_url: Optional[str] = None
    viability: str
    estimated_amount: Optional[float] = None
    actionable_steps: Optional[str] = None
    relevance_score: float
    created_at: datetime

    class Config:
        from_attributes = True
