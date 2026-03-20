from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class FundingRequestCreate(BaseModel):
    engine_id: int
    funding_type: str
    title: str
    description: str
    amount_requested: float
    justification: Optional[str] = None
    projected_roi: Optional[float] = None
    operational_cost: Optional[float] = None
    strategy_details: Optional[str] = None


class FundingRequestUpdate(BaseModel):
    status: Optional[str] = None
    amount_secured: Optional[float] = None
    strategy_details: Optional[str] = None


class FundingRequestOut(BaseModel):
    id: int
    engine_id: int
    funding_type: str
    title: str
    description: str
    amount_requested: float
    amount_secured: float
    justification: Optional[str] = None
    projected_roi: Optional[float] = None
    operational_cost: Optional[float] = None
    status: str
    strategy_details: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenTransactionOut(BaseModel):
    id: int
    engine_id: int
    amount: float
    balance_after: float
    description: str
    funding_request_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
