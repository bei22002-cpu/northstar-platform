"""User subscriptions and usage tracking for tiered pricing."""

import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.sql import func

from app.core.database import Base


class PlanTier(str, enum.Enum):
    free = "free"
    pro = "pro"
    enterprise = "enterprise"


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    tier = Column(Enum(PlanTier), default=PlanTier.free, nullable=False)
    messages_used = Column(Integer, default=0)
    messages_limit = Column(Integer, default=50)  # free=50, pro=unlimited(-1), enterprise=custom
    billing_cycle_start = Column(DateTime(timezone=True), server_default=func.now())
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action_type = Column(String, nullable=False)  # agent_chat, tool_execution
    model_used = Column(String, nullable=True)
    tokens_consumed = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
