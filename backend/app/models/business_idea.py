import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func

from app.core.database import Base


class IdeaStatusEnum(str, enum.Enum):
    submitted = "submitted"
    analyzing = "analyzing"
    strategies_generated = "strategies_generated"
    in_progress = "in_progress"
    completed = "completed"


class BusinessIdea(Base):
    __tablename__ = "business_ideas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    industry = Column(String, nullable=False)  # e.g. technology, retail, services
    target_market = Column(String, nullable=True)
    budget_range = Column(String, nullable=True)
    status = Column(Enum(IdeaStatusEnum), default=IdeaStatusEnum.submitted)
    ai_analysis = Column(Text, nullable=True)  # JSON with AI-generated analysis
    funding_strategy = Column(Text, nullable=True)  # JSON with recommended funding approaches
    feedback = Column(Text, nullable=True)  # User feedback on AI suggestions
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
