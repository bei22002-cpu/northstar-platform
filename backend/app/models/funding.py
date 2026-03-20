import enum
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func

from app.core.database import Base


class FundingTypeEnum(str, enum.Enum):
    grant = "grant"
    sponsorship = "sponsorship"
    partnership = "partnership"
    crowdfunding = "crowdfunding"
    subscription_revenue = "subscription_revenue"
    ad_revenue = "ad_revenue"
    token_purchase = "token_purchase"


class FundingStatusEnum(str, enum.Enum):
    proposed = "proposed"
    under_review = "under_review"
    approved = "approved"
    in_progress = "in_progress"
    completed = "completed"
    rejected = "rejected"


class FundingRequest(Base):
    __tablename__ = "funding_requests"

    id = Column(Integer, primary_key=True, index=True)
    engine_id = Column(Integer, ForeignKey("ai_engines.id"), nullable=False, index=True)
    funding_type = Column(Enum(FundingTypeEnum), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    amount_requested = Column(Float, nullable=False)
    amount_secured = Column(Float, default=0.0)
    justification = Column(Text, nullable=True)
    projected_roi = Column(Float, nullable=True)  # percentage
    operational_cost = Column(Float, nullable=True)
    status = Column(Enum(FundingStatusEnum), default=FundingStatusEnum.proposed)
    strategy_details = Column(Text, nullable=True)  # JSON string with strategy breakdown
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TokenTransaction(Base):
    __tablename__ = "token_transactions"

    id = Column(Integer, primary_key=True, index=True)
    engine_id = Column(Integer, ForeignKey("ai_engines.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)  # positive = credit, negative = debit
    balance_after = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    funding_request_id = Column(Integer, ForeignKey("funding_requests.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
