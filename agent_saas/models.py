"""SQLAlchemy models for the SaaS platform."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from agent_saas.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


class User(Base):
    __tablename__ = "users"

    id = Column(String(32), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), default="")
    plan = Column(String(20), default="free", nullable=False)
    stripe_customer_id = Column(String(255), default="")
    stripe_subscription_id = Column(String(255), default="")
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    tokens_used_this_month = Column(Integer, default=0)
    month_reset = Column(String(7), default="")  # "2026-03" format
    created_at = Column(DateTime, default=_utcnow)
    last_login = Column(DateTime, default=_utcnow)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    usage_records = relationship("UsageRecord", back_populates="user", cascade="all, delete-orphan")

    def current_month(self) -> str:
        return _utcnow().strftime("%Y-%m")

    def reset_if_new_month(self) -> None:
        cm = self.current_month()
        if self.month_reset != cm:
            self.tokens_used_this_month = 0
            self.month_reset = cm

    def tokens_remaining(self, plan_limits: dict) -> int:
        self.reset_if_new_month()
        limit = plan_limits.get(self.plan, {}).get("monthly_tokens", 0)
        return max(0, limit - self.tokens_used_this_month)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(32), primary_key=True, default=_uuid)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    title = Column(String(500), default="New conversation")
    model = Column(String(100), default="claude-haiku-4-5-20250514")
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(32), primary_key=True, default=_uuid)
    conversation_id = Column(String(32), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, default="")
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=_utcnow)

    conversation = relationship("Conversation", back_populates="messages")


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(String(32), primary_key=True, default=_uuid)
    user_id = Column(String(32), ForeignKey("users.id"), nullable=False)
    model = Column(String(100), default="")
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=_utcnow)

    user = relationship("User", back_populates="usage_records")
