from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EngineMessageCreate(BaseModel):
    sender_engine_id: int
    receiver_engine_id: Optional[int] = None  # null = broadcast
    message_type: str
    subject: str
    body: str
    metadata_json: Optional[str] = None


class EngineMessageOut(BaseModel):
    id: int
    sender_engine_id: int
    receiver_engine_id: Optional[int] = None
    message_type: str
    subject: str
    body: str
    metadata_json: Optional[str] = None
    is_read: int
    created_at: datetime

    class Config:
        from_attributes = True
