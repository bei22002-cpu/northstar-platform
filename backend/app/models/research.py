import enum
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func

from app.core.database import Base


class ResearchCategoryEnum(str, enum.Enum):
    grants = "grants"
    sponsorships = "sponsorships"
    partnerships = "partnerships"
    crowdfunding = "crowdfunding"
    innovative_models = "innovative_models"
    venture_capital = "venture_capital"
    angel_investment = "angel_investment"


class ViabilityEnum(str, enum.Enum):
    high = "high"
    medium = "medium"
    low = "low"
    unknown = "unknown"


class ResearchInsight(Base):
    __tablename__ = "research_insights"

    id = Column(Integer, primary_key=True, index=True)
    engine_id = Column(Integer, ForeignKey("ai_engines.id"), nullable=False, index=True)
    category = Column(Enum(ResearchCategoryEnum), nullable=False)
    title = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    source_url = Column(String, nullable=True)
    viability = Column(Enum(ViabilityEnum), default=ViabilityEnum.unknown)
    estimated_amount = Column(Float, nullable=True)
    actionable_steps = Column(Text, nullable=True)  # JSON array of steps
    relevance_score = Column(Float, default=0.0)  # 0-100
    created_at = Column(DateTime(timezone=True), server_default=func.now())
