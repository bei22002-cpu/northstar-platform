"""API router for AI Engine management and inter-engine communication."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.ai_engine import AIEngine, EngineStatusEnum
from app.models.user import User
from app.schemas.ai_engine import AIEngineCreate, AIEngineOut, AIEngineUpdate
from app.schemas.engine_message import EngineMessageCreate, EngineMessageOut
from app.services import engine_communication

router = APIRouter(prefix="/ai-engines", tags=["AI Engines"])


# ── Engine CRUD ───────────────────────────────────────────────────────────────

@router.get("/", response_model=list[AIEngineOut])
def list_engines(
    active_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all registered AI engines."""
    query = db.query(AIEngine)
    if active_only:
        query = query.filter(AIEngine.is_active.is_(True))
    return query.order_by(AIEngine.created_at.desc()).all()


@router.post("/", response_model=AIEngineOut, status_code=status.HTTP_201_CREATED)
def create_engine(payload: AIEngineCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Register a new AI engine."""
    existing = db.query(AIEngine).filter(AIEngine.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Engine with this name already exists")

    engine = AIEngine(
        name=payload.name,
        description=payload.description,
        specialization=payload.specialization,
        token_balance=payload.token_balance,
    )
    db.add(engine)
    db.commit()
    db.refresh(engine)
    return engine


@router.get("/{engine_id}", response_model=AIEngineOut)
def get_engine(engine_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a specific AI engine by ID."""
    engine = db.query(AIEngine).filter(AIEngine.id == engine_id).first()
    if not engine:
        raise HTTPException(status_code=404, detail="Engine not found")
    return engine


@router.patch("/{engine_id}", response_model=AIEngineOut)
def update_engine(engine_id: int, payload: AIEngineUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update an AI engine's properties."""
    engine = db.query(AIEngine).filter(AIEngine.id == engine_id).first()
    if not engine:
        raise HTTPException(status_code=404, detail="Engine not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(engine, field, value)

    db.commit()
    db.refresh(engine)
    return engine


@router.post("/{engine_id}/heartbeat", response_model=AIEngineOut)
def engine_heartbeat(engine_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update heartbeat timestamp for an engine."""
    try:
        return engine_communication.update_engine_heartbeat(db, engine_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Inter-Engine Messaging ───────────────────────────────────────────────────

@router.post("/messages", response_model=EngineMessageOut, status_code=status.HTTP_201_CREATED)
def send_message(payload: EngineMessageCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Send a message between AI engines."""
    try:
        return engine_communication.send_message(
            db=db,
            sender_id=payload.sender_engine_id,
            message_type=payload.message_type,
            subject=payload.subject,
            body=payload.body,
            receiver_id=payload.receiver_engine_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/messages/history", response_model=list[EngineMessageOut])
def get_message_history(
    engine_id: Optional[int] = Query(None),
    message_type: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get communication history across engines."""
    return engine_communication.get_communication_history(
        db, engine_id=engine_id, message_type=message_type, limit=limit
    )


@router.get("/{engine_id}/messages", response_model=list[EngineMessageOut])
def get_engine_messages(
    engine_id: int,
    unread_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get messages for a specific engine."""
    return engine_communication.get_messages_for_engine(
        db, engine_id=engine_id, unread_only=unread_only
    )


@router.post("/messages/{message_id}/read", response_model=EngineMessageOut)
def mark_read(message_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Mark a message as read."""
    try:
        return engine_communication.mark_message_read(db, message_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{engine_id}/broadcast-insight", response_model=EngineMessageOut)
def broadcast_insight(
    engine_id: int,
    title: str = Query(...),
    summary: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Broadcast a funding insight to all engines."""
    try:
        return engine_communication.broadcast_funding_insight(
            db, sender_id=engine_id, insight_title=title, insight_summary=summary
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{sender_id}/collaborate/{receiver_id}", response_model=EngineMessageOut)
def propose_collab(
    sender_id: int,
    receiver_id: int,
    title: str = Query(...),
    details: str = Query(...),
    funding_goal: Optional[float] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a collaboration proposal between engines."""
    try:
        return engine_communication.propose_collaboration(
            db,
            sender_id=sender_id,
            receiver_id=receiver_id,
            proposal_title=title,
            proposal_details=details,
            funding_goal=funding_goal,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
