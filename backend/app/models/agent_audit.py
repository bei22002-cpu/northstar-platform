"""Audit logging for Cornerstone AI Agent interactions."""

import enum
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class AgentAuditLog(Base):
    __tablename__ = "agent_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String, nullable=False, index=True)
    message = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    model_used = Column(String, nullable=False)
    provider = Column(String, nullable=False)  # anthropic, openai, google
    tool_actions = Column(JSON, nullable=True)
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)
    status = Column(String, default="completed")  # completed, error, pending_approval
    error_message = Column(Text, nullable=True)
    agent_config_id = Column(Integer, ForeignKey("agent_configs.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
