from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LeadCreate(BaseModel):
    company_name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    score: Optional[float] = None
    status: str = "new"


class LeadRead(BaseModel):
    id: int
    company_name: str
    website: Optional[str] = None
    industry: Optional[str] = None
    description: Optional[str] = None
    score: Optional[float] = None
    status: str
    date_discovered: Optional[datetime] = None

    model_config = {"from_attributes": True}
