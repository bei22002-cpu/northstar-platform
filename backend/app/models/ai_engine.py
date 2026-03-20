import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Enum
from sqlalchemy.sql import func

from app.core.database import Base


class EngineStatusEnum(str, enum.Enum):
    active = "active"
    idle = "idle"
    researching = "researching"
    funding = "funding"
    error = "error"


class AIEngine(Base):
    __tablename__ = "ai_engines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    specialization = Column(String, nullable=False)  # e.g. "funding", "market_research", "strategy"
    status = Column(Enum(EngineStatusEnum), default=EngineStatusEnum.idle)
    token_balance = Column(Float, default=0.0)
    tokens_consumed = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
