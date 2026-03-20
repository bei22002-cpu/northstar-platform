import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func

from app.core.database import Base


class MessageTypeEnum(str, enum.Enum):
    funding_request = "funding_request"
    strategy_share = "strategy_share"
    insight_broadcast = "insight_broadcast"
    collaboration_proposal = "collaboration_proposal"
    status_update = "status_update"
    task_assignment = "task_assignment"


class EngineMessage(Base):
    __tablename__ = "engine_messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_engine_id = Column(Integer, ForeignKey("ai_engines.id"), nullable=False, index=True)
    receiver_engine_id = Column(Integer, ForeignKey("ai_engines.id"), nullable=True, index=True)  # null = broadcast
    message_type = Column(Enum(MessageTypeEnum), nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON string for structured data
    is_read = Column(Integer, default=0)  # 0=unread, 1=read
    created_at = Column(DateTime(timezone=True), server_default=func.now())
