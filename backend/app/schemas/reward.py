from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RewardTransactionCreate(BaseModel):
    user_id: int
    reward_type: str
    tokens_earned: float
    description: str
    metadata_json: Optional[str] = None


class RewardTransactionOut(BaseModel):
    id: int
    user_id: int
    reward_type: str
    tokens_earned: float
    description: str
    metadata_json: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserRewardBalanceOut(BaseModel):
    id: int
    user_id: int
    total_tokens: float
    lifetime_earned: float
    lifetime_spent: float
    tier: str
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
