import enum
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func

from app.core.database import Base


class RewardTypeEnum(str, enum.Enum):
    signup_bonus = "signup_bonus"
    idea_submission = "idea_submission"
    feedback_provided = "feedback_provided"
    referral = "referral"
    subscription = "subscription"
    engagement = "engagement"
    milestone = "milestone"


class RewardTransaction(Base):
    __tablename__ = "reward_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reward_type = Column(Enum(RewardTypeEnum), nullable=False)
    tokens_earned = Column(Float, nullable=False)
    description = Column(String, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON with extra context
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserRewardBalance(Base):
    __tablename__ = "user_reward_balances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    total_tokens = Column(Float, default=0.0)
    lifetime_earned = Column(Float, default=0.0)
    lifetime_spent = Column(Float, default=0.0)
    tier = Column(String, default="bronze")  # bronze, silver, gold, platinum
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
