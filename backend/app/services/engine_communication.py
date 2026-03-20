"""Service for AI engine inter-communication protocol.

Provides messaging between AI engines for sharing funding strategies,
insights, and collaboration proposals.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ai_engine import AIEngine, EngineStatusEnum
from app.models.engine_message import EngineMessage, MessageTypeEnum


def send_message(
    db: Session,
    sender_id: int,
    message_type: str,
    subject: str,
    body: str,
    receiver_id: Optional[int] = None,
    metadata: Optional[dict] = None,
) -> EngineMessage:
    """Send a message from one engine to another (or broadcast if receiver_id is None)."""
    sender = db.query(AIEngine).filter(AIEngine.id == sender_id).first()
    if not sender:
        raise ValueError(f"Sender engine {sender_id} not found")

    if receiver_id is not None:
        receiver = db.query(AIEngine).filter(AIEngine.id == receiver_id).first()
        if not receiver:
            raise ValueError(f"Receiver engine {receiver_id} not found")

    msg = EngineMessage(
        sender_engine_id=sender_id,
        receiver_engine_id=receiver_id,
        message_type=message_type,
        subject=subject,
        body=body,
        metadata_json=json.dumps(metadata) if metadata else None,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


def get_messages_for_engine(
    db: Session,
    engine_id: int,
    include_broadcasts: bool = True,
    unread_only: bool = False,
) -> list[EngineMessage]:
    """Retrieve messages for a specific engine, optionally including broadcasts."""
    query = db.query(EngineMessage)

    if include_broadcasts:
        query = query.filter(
            (EngineMessage.receiver_engine_id == engine_id)
            | (EngineMessage.receiver_engine_id.is_(None))
        )
    else:
        query = query.filter(EngineMessage.receiver_engine_id == engine_id)

    if unread_only:
        query = query.filter(EngineMessage.is_read == 0)

    return query.order_by(EngineMessage.created_at.desc()).all()


def mark_message_read(db: Session, message_id: int) -> EngineMessage:
    """Mark a message as read."""
    msg = db.query(EngineMessage).filter(EngineMessage.id == message_id).first()
    if not msg:
        raise ValueError(f"Message {message_id} not found")
    msg.is_read = 1
    db.commit()
    db.refresh(msg)
    return msg


def get_communication_history(
    db: Session,
    engine_id: Optional[int] = None,
    message_type: Optional[str] = None,
    limit: int = 50,
) -> list[EngineMessage]:
    """Get communication history, optionally filtered by engine or type."""
    query = db.query(EngineMessage)

    if engine_id is not None:
        query = query.filter(
            (EngineMessage.sender_engine_id == engine_id)
            | (EngineMessage.receiver_engine_id == engine_id)
        )

    if message_type is not None:
        query = query.filter(EngineMessage.message_type == message_type)

    return query.order_by(EngineMessage.created_at.desc()).limit(limit).all()


def broadcast_funding_insight(
    db: Session,
    sender_id: int,
    insight_title: str,
    insight_summary: str,
    strategy_data: Optional[dict] = None,
) -> EngineMessage:
    """Broadcast a funding insight to all engines."""
    return send_message(
        db=db,
        sender_id=sender_id,
        message_type=MessageTypeEnum.insight_broadcast.value,
        subject=f"Funding Insight: {insight_title}",
        body=insight_summary,
        receiver_id=None,
        metadata=strategy_data,
    )


def propose_collaboration(
    db: Session,
    sender_id: int,
    receiver_id: int,
    proposal_title: str,
    proposal_details: str,
    funding_goal: Optional[float] = None,
) -> EngineMessage:
    """Send a collaboration proposal from one engine to another."""
    metadata = {}
    if funding_goal is not None:
        metadata["funding_goal"] = funding_goal

    return send_message(
        db=db,
        sender_id=sender_id,
        message_type=MessageTypeEnum.collaboration_proposal.value,
        subject=proposal_title,
        body=proposal_details,
        receiver_id=receiver_id,
        metadata=metadata,
    )


def update_engine_heartbeat(db: Session, engine_id: int) -> AIEngine:
    """Update the last heartbeat timestamp for an engine."""
    engine = db.query(AIEngine).filter(AIEngine.id == engine_id).first()
    if not engine:
        raise ValueError(f"Engine {engine_id} not found")
    engine.last_heartbeat = datetime.now(timezone.utc)
    db.commit()
    db.refresh(engine)
    return engine
