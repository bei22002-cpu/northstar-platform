from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AIEngineBase(BaseModel):
    name: str
    description: Optional[str] = None
    specialization: str


class AIEngineCreate(AIEngineBase):
    token_balance: float = 0.0


class AIEngineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    specialization: Optional[str] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class AIEngineOut(AIEngineBase):
    id: int
    status: str
    token_balance: float
    tokens_consumed: float
    is_active: bool
    last_heartbeat: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
