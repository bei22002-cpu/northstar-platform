"""API router for the Cornerstone AI Agent web interface.

Includes endpoints for chat, streaming, audit logs, marketplace,
approval workflows, usage tracking, analytics, and white-label settings.
"""

from __future__ import annotations

import uuid
import time
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func as sqlfunc

from app.api.deps import get_current_user
from app.core.config import ANTHROPIC_API_KEY
from app.core.database import get_db
from app.models.user import User
from app.models.agent_audit import AgentAuditLog
from app.models.agent_config import AgentConfig
from app.models.subscription import UserSubscription, UsageRecord, PlanTier
from app.models.platform_settings import PlatformSettings
from app.services.agent_service import (
    run_agent_chat,
    stream_agent_chat_anthropic,
    get_available_providers,
    execute_approved_tools,
    WORKSPACE,
    MODEL_CONFIGS,
    TOOL_DEFINITIONS,
)

router = APIRouter(prefix="/agent", tags=["Cornerstone AI Agent"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class AgentChatRequest(BaseModel):
    message: str
    history: Optional[list[dict[str, Any]]] = None
    provider: str = "anthropic"
    model: Optional[str] = None
    require_approval: bool = False
    agent_config_id: Optional[int] = None


class ToolAction(BaseModel):
    tool: str
    input: dict[str, Any]
    output: str
    status: str = "executed"


class AgentChatResponse(BaseModel):
    response: str
    tool_actions: list[ToolAction]
    history: list[dict[str, Any]]
    pending_approvals: list[dict[str, Any]] = []
    tokens_input: int = 0
    tokens_output: int = 0
    provider: str = ""
    model: str = ""
    session_id: str = ""
    latency_ms: int = 0


class AgentInfoResponse(BaseModel):
    name: str
    description: str
    workspace: str
    tools: list[str]
    status: str
    providers: list[dict[str, Any]] = []
    model_configs: dict[str, Any] = {}


class ApprovalRequest(BaseModel):
    approvals: list[dict[str, Any]]
    approved: bool = True


class AgentConfigCreate(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: str
    model_provider: str = "anthropic"
    model_name: Optional[str] = None
    tools_enabled: Optional[list[str]] = None
    max_iterations: int = 10
    is_public: bool = False
    category: Optional[str] = None
    icon: Optional[str] = None


class AgentConfigResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    system_prompt: str
    model_provider: str
    model_name: str
    tools_enabled: Optional[list[str]]
    max_iterations: int
    created_by: int
    is_public: bool
    use_count: int
    category: Optional[str]
    icon: Optional[str]


class SubscriptionResponse(BaseModel):
    tier: str
    messages_used: int
    messages_limit: int
    is_active: bool


class AuditLogResponse(BaseModel):
    id: int
    user_id: int
    session_id: str
    message: str
    response: Optional[str]
    model_used: str
    provider: str
    tool_actions: Optional[Any]
    tokens_input: int
    tokens_output: int
    latency_ms: int
    status: str
    created_at: Optional[str]


class AnalyticsResponse(BaseModel):
    total_messages: int
    total_tool_executions: int
    total_tokens: int
    avg_latency_ms: float
    messages_by_provider: dict[str, int]
    messages_by_day: list[dict[str, Any]]
    top_tools: list[dict[str, Any]]
    active_users: int


class PlatformSettingsResponse(BaseModel):
    platform_name: str
    tagline: str
    logo_url: Optional[str]
    favicon_url: Optional[str]
    primary_color: str
    accent_color: str
    sidebar_bg: str
    sidebar_text: str
    custom_css: Optional[str]
    support_email: Optional[str]
    enable_marketplace: bool
    enable_analytics: bool


class PlatformSettingsUpdate(BaseModel):
    platform_name: Optional[str] = None
    tagline: Optional[str] = None
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    primary_color: Optional[str] = None
    accent_color: Optional[str] = None
    sidebar_bg: Optional[str] = None
    sidebar_text: Optional[str] = None
    custom_css: Optional[str] = None
    support_email: Optional[str] = None
    enable_marketplace: Optional[bool] = None
    enable_analytics: Optional[bool] = None


# ---------------------------------------------------------------------------
# Helper: ensure subscription exists
# ---------------------------------------------------------------------------

def _get_or_create_subscription(db: Session, user_id: int) -> UserSubscription:
    sub = db.query(UserSubscription).filter(UserSubscription.user_id == user_id).first()
    if not sub:
        sub = UserSubscription(user_id=user_id, tier=PlanTier.free, messages_used=0, messages_limit=50)
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=AgentChatResponse)
def agent_chat(
    payload: AgentChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgentChatResponse:
    """Send a message to the Cornerstone AI Agent."""
    # Check usage limits
    sub = _get_or_create_subscription(db, current_user.id)
    if sub.messages_limit != -1 and sub.messages_used >= sub.messages_limit:
        return AgentChatResponse(
            response="You have reached your monthly message limit. "
                     "Please upgrade to Pro for unlimited messages.",
            tool_actions=[], history=payload.history or [],
        )

    # Load agent config if specified
    system_prompt = None
    tools_enabled = None
    provider = payload.provider
    model = payload.model
    if payload.agent_config_id:
        config = db.query(AgentConfig).filter(AgentConfig.id == payload.agent_config_id).first()
        if config:
            system_prompt = config.system_prompt
            tools_enabled = config.tools_enabled
            provider = config.model_provider
            model = model or config.model_name
            config.use_count = (config.use_count or 0) + 1
            db.commit()

    start_time = time.time()
    result = run_agent_chat(
        user_message=payload.message,
        history=payload.history,
        provider=provider,
        model=model,
        system_prompt=system_prompt,
        require_approval=payload.require_approval,
        tools_enabled=tools_enabled,
    )

    # Record audit log
    audit = AgentAuditLog(
        user_id=current_user.id,
        session_id=result.get("session_id", str(uuid.uuid4())),
        message=payload.message,
        response=result["response"][:5000],
        model_used=result.get("model", ""),
        provider=result.get("provider", provider),
        tool_actions=result.get("tool_actions"),
        tokens_input=result.get("tokens_input", 0),
        tokens_output=result.get("tokens_output", 0),
        latency_ms=result.get("latency_ms", 0),
        status="completed" if not result.get("pending_approvals") else "pending_approval",
        agent_config_id=payload.agent_config_id,
    )
    db.add(audit)

    # Update usage
    sub.messages_used = (sub.messages_used or 0) + 1
    usage = UsageRecord(
        user_id=current_user.id,
        action_type="agent_chat",
        model_used=result.get("model", ""),
        tokens_consumed=result.get("tokens_input", 0) + result.get("tokens_output", 0),
    )
    db.add(usage)
    db.commit()

    return AgentChatResponse(
        response=result["response"],
        tool_actions=[ToolAction(**ta) for ta in result["tool_actions"]],
        history=result["history"],
        pending_approvals=result.get("pending_approvals", []),
        tokens_input=result.get("tokens_input", 0),
        tokens_output=result.get("tokens_output", 0),
        provider=result.get("provider", ""),
        model=result.get("model", ""),
        session_id=result.get("session_id", ""),
        latency_ms=result.get("latency_ms", 0),
    )


@router.post("/chat/stream")
def agent_chat_stream(
    payload: AgentChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Stream agent responses using Server-Sent Events (SSE)."""
    return StreamingResponse(
        stream_agent_chat_anthropic(
            user_message=payload.message,
            history=payload.history,
            model=payload.model,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/approve")
def approve_tools(
    payload: ApprovalRequest,
    current_user: User = Depends(get_current_user),
):
    """Approve or reject pending tool executions."""
    if not payload.approved:
        return {"status": "rejected", "response": "Actions cancelled.", "tool_actions": [], "results": []}
    results = execute_approved_tools(payload.approvals)
    # Build a summary response from tool results
    summary_parts = []
    for r in results:
        summary_parts.append(f"Executed {r['tool']}: {r['output'][:200]}")
    response_text = "\n".join(summary_parts) if summary_parts else "Actions approved and executed."
    return {"status": "approved", "response": response_text, "tool_actions": results, "results": results}


@router.get("/info", response_model=AgentInfoResponse)
def agent_info(
    current_user: User = Depends(get_current_user),
) -> AgentInfoResponse:
    """Return metadata about the Cornerstone AI Agent."""
    providers = get_available_providers()
    any_configured = len(providers) > 0
    return AgentInfoResponse(
        name="Cornerstone AI Agent",
        description=(
            "An autonomous AI agent powered by multiple LLMs that can read, write, "
            "edit, and manage files and run terminal commands inside the "
            "project workspace. Supports Claude, GPT-4, and Gemini."
        ),
        workspace=WORKSPACE,
        tools=[td["name"] for td in TOOL_DEFINITIONS],
        status="online" if any_configured else "unconfigured",
        providers=providers,
        model_configs=MODEL_CONFIGS,
    )


# ---------------------------------------------------------------------------
# Audit Logs
# ---------------------------------------------------------------------------

@router.get("/audit")
def get_audit_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
):
    """Get agent audit logs for the current user."""
    logs = (
        db.query(AgentAuditLog)
        .filter(AgentAuditLog.user_id == current_user.id)
        .order_by(AgentAuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": log.id,
            "session_id": log.session_id,
            "message": log.message,
            "response": (log.response or "")[:200],
            "model_used": log.model_used,
            "provider": log.provider,
            "tool_actions": log.tool_actions,
            "tokens_input": log.tokens_input,
            "tokens_output": log.tokens_output,
            "latency_ms": log.latency_ms,
            "status": log.status,
            "created_at": str(log.created_at) if log.created_at else None,
        }
        for log in logs
    ]


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get analytics data for the agent dashboard."""
    total_messages = db.query(sqlfunc.count(AgentAuditLog.id)).filter(
        AgentAuditLog.user_id == current_user.id
    ).scalar() or 0

    total_tokens = db.query(
        sqlfunc.coalesce(sqlfunc.sum(AgentAuditLog.tokens_input + AgentAuditLog.tokens_output), 0)
    ).filter(AgentAuditLog.user_id == current_user.id).scalar() or 0

    avg_latency = db.query(
        sqlfunc.coalesce(sqlfunc.avg(AgentAuditLog.latency_ms), 0)
    ).filter(AgentAuditLog.user_id == current_user.id).scalar() or 0

    # Messages by provider
    provider_counts = (
        db.query(AgentAuditLog.provider, sqlfunc.count(AgentAuditLog.id))
        .filter(AgentAuditLog.user_id == current_user.id)
        .group_by(AgentAuditLog.provider)
        .all()
    )
    messages_by_provider = {p: c for p, c in provider_counts if p}

    # Count tool executions from tool_actions JSON
    total_tool_executions = 0
    tool_counts: dict[str, int] = {}
    logs_with_tools = (
        db.query(AgentAuditLog.tool_actions)
        .filter(AgentAuditLog.user_id == current_user.id, AgentAuditLog.tool_actions.isnot(None))
        .all()
    )
    for (actions,) in logs_with_tools:
        if isinstance(actions, list):
            total_tool_executions += len(actions)
            for action in actions:
                if isinstance(action, dict):
                    name = action.get("tool", "unknown")
                    tool_counts[name] = tool_counts.get(name, 0) + 1

    top_tools = sorted(
        [{"tool": k, "count": v} for k, v in tool_counts.items()],
        key=lambda x: x["count"], reverse=True,
    )[:10]

    # Active users (org-wide)
    active_users = db.query(sqlfunc.count(sqlfunc.distinct(AgentAuditLog.user_id))).scalar() or 0

    # Compute messages_by_day (last 30 days)
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    thirty_days_ago = now - timedelta(days=30)
    daily_rows = (
        db.query(
            sqlfunc.cast(AgentAuditLog.created_at, sqlfunc.text()).label("day"),
            sqlfunc.count(AgentAuditLog.id).label("cnt"),
        )
        .filter(
            AgentAuditLog.user_id == current_user.id,
            AgentAuditLog.created_at >= thirty_days_ago,
        )
        .group_by("day")
        .order_by("day")
        .all()
    )
    messages_by_day = [{"date": str(row.day)[:10], "count": row.cnt} for row in daily_rows]

    return AnalyticsResponse(
        total_messages=total_messages,
        total_tool_executions=total_tool_executions,
        total_tokens=total_tokens,
        avg_latency_ms=round(float(avg_latency), 1),
        messages_by_provider=messages_by_provider,
        messages_by_day=messages_by_day,
        top_tools=top_tools,
        active_users=active_users,
    )


# ---------------------------------------------------------------------------
# Agent Marketplace
# ---------------------------------------------------------------------------

@router.get("/marketplace")
def list_marketplace_configs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    category: Optional[str] = None,
):
    """List public agent configurations and user's own configs."""
    query = db.query(AgentConfig).filter(
        (AgentConfig.is_public == True) | (AgentConfig.created_by == current_user.id)
    )
    if category:
        query = query.filter(AgentConfig.category == category)
    configs = query.order_by(AgentConfig.use_count.desc()).all()
    return [
        {
            "id": c.id, "name": c.name, "description": c.description,
            "model_provider": c.model_provider, "model_name": c.model_name,
            "tools_enabled": c.tools_enabled, "max_iterations": c.max_iterations,
            "created_by": c.created_by, "is_public": c.is_public,
            "use_count": c.use_count, "category": c.category, "icon": c.icon,
        }
        for c in configs
    ]


@router.post("/marketplace")
def create_marketplace_config(
    payload: AgentConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new agent configuration."""
    config = AgentConfig(
        name=payload.name,
        description=payload.description,
        system_prompt=payload.system_prompt,
        model_provider=payload.model_provider,
        model_name=payload.model_name or MODEL_CONFIGS.get(payload.model_provider, {}).get("default_model", ""),
        tools_enabled=payload.tools_enabled,
        max_iterations=payload.max_iterations,
        created_by=current_user.id,
        is_public=payload.is_public,
        category=payload.category,
        icon=payload.icon,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return {"id": config.id, "name": config.name, "status": "created"}


@router.delete("/marketplace/{config_id}")
def delete_marketplace_config(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an agent configuration (only owner can delete)."""
    config = db.query(AgentConfig).filter(
        AgentConfig.id == config_id, AgentConfig.created_by == current_user.id
    ).first()
    if not config:
        return {"error": "Config not found or not authorized"}
    db.delete(config)
    db.commit()
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# Subscription / Usage
# ---------------------------------------------------------------------------

@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's subscription info."""
    sub = _get_or_create_subscription(db, current_user.id)
    return SubscriptionResponse(
        tier=sub.tier.value if hasattr(sub.tier, 'value') else str(sub.tier),
        messages_used=sub.messages_used or 0,
        messages_limit=sub.messages_limit or 50,
        is_active=sub.is_active,
    )


@router.post("/subscription/upgrade")
def upgrade_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upgrade to Pro tier (placeholder - would integrate with Stripe)."""
    sub = _get_or_create_subscription(db, current_user.id)
    sub.tier = PlanTier.pro
    sub.messages_limit = -1  # unlimited
    db.commit()
    return {"status": "upgraded", "tier": "pro", "messages_limit": -1}


# ---------------------------------------------------------------------------
# White-Label / Platform Settings
# ---------------------------------------------------------------------------

@router.get("/settings", response_model=PlatformSettingsResponse)
def get_platform_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get platform branding/settings."""
    settings = db.query(PlatformSettings).first()
    if not settings:
        settings = PlatformSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return PlatformSettingsResponse(
        platform_name=settings.platform_name or "NorthStar",
        tagline=settings.tagline or "AI-Powered Consulting Platform",
        logo_url=settings.logo_url,
        favicon_url=settings.favicon_url,
        primary_color=settings.primary_color or "#3182ce",
        accent_color=settings.accent_color or "#805ad5",
        sidebar_bg=settings.sidebar_bg or "#1a202c",
        sidebar_text=settings.sidebar_text or "#90cdf4",
        custom_css=settings.custom_css,
        support_email=settings.support_email,
        enable_marketplace=settings.enable_marketplace if settings.enable_marketplace is not None else True,
        enable_analytics=settings.enable_analytics if settings.enable_analytics is not None else True,
    )


@router.put("/settings")
def update_platform_settings(
    payload: PlatformSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update platform branding/settings."""
    settings = db.query(PlatformSettings).first()
    if not settings:
        settings = PlatformSettings()
        db.add(settings)
        db.commit()
        db.refresh(settings)

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(settings, key, value)
    db.commit()
    db.refresh(settings)
    return PlatformSettingsResponse(
        platform_name=settings.platform_name or "NorthStar",
        tagline=settings.tagline or "AI-Powered Consulting Platform",
        logo_url=settings.logo_url,
        favicon_url=settings.favicon_url,
        primary_color=settings.primary_color or "#3182ce",
        accent_color=settings.accent_color or "#805ad5",
        sidebar_bg=settings.sidebar_bg or "#1a202c",
        sidebar_text=settings.sidebar_text or "#90cdf4",
        custom_css=settings.custom_css,
        support_email=settings.support_email,
        enable_marketplace=settings.enable_marketplace if settings.enable_marketplace is not None else True,
        enable_analytics=settings.enable_analytics if settings.enable_analytics is not None else True,
    )
