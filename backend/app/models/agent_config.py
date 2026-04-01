"""Agent marketplace configurations."""

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func

from app.core.database import Base


class AgentConfig(Base):
    __tablename__ = "agent_configs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)
    model_provider = Column(String, default="anthropic")  # anthropic, openai, google
    model_name = Column(String, default="claude-sonnet-4-20250514")
    tools_enabled = Column(JSON, nullable=True)  # list of tool names, null = all
    max_iterations = Column(Integer, default=10)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    is_public = Column(Boolean, default=False)
    use_count = Column(Integer, default=0)
    category = Column(String, nullable=True)  # coding, devops, data, general
    icon = Column(String, nullable=True)  # emoji or icon name
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
