"""FastAPI main application — routes for auth, chat, billing, and admin."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Cookie, Depends, FastAPI, Form, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from agent_saas.config import (
    APP_NAME,
    PLANS,
    STRIPE_PUBLISHABLE_KEY,
    MODEL_MAP,
)
from agent_saas.database import get_db, init_db
from agent_saas.models import Conversation, Message, UsageRecord, User
from agent_saas import auth as auth_module
from agent_saas import billing as billing_module
from agent_saas import chat as chat_module


# ── App setup ───────────────────────────────────────────────────────

app = FastAPI(title=APP_NAME, docs_url="/api/docs")

_base = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(_base / "static")), name="static")
templates = Jinja2Templates(directory=str(_base / "templates"))


@app.on_event("startup")
def startup():
    init_db()
    # Create default admin if not exists
    db = next(get_db())
    try:
        from agent_saas.config import ADMIN_EMAIL, ADMIN_PASSWORD
        existing = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        if not existing:
            user, err = auth_module.signup_user(db, ADMIN_EMAIL, ADMIN_PASSWORD, "Admin")
            if user:
                user.is_admin = True
                user.plan = "enterprise"
                db.commit()
    finally:
        db.close()


# ── Auth helpers ────────────────────────────────────────────────────

def _get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Cookie(None, alias="token"),
) -> Optional[User]:
    """Get current user from JWT cookie."""
    if not token:
        return None
    return auth_module.get_user_from_token(db, token)


def _require_user(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Cookie(None, alias="token"),
) -> User:
    """Require authenticated user or redirect to login."""
    user = _get_current_user(request, db, token)
    if not user:
        raise RedirectToLogin()
    return user


class RedirectToLogin(Exception):
    pass


@app.exception_handler(RedirectToLogin)
async def redirect_to_login(request: Request, exc: RedirectToLogin):
    return RedirectResponse(url="/login", status_code=302)


# ── Public pages ────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request, db: Session = Depends(get_db),
                  token: Optional[str] = Cookie(None, alias="token")):
    user = None
    if token:
        user = auth_module.get_user_from_token(db, token)
    return templates.TemplateResponse(request, "landing.html", {
        "app_name": APP_NAME, "user": user, "plans": PLANS,
    })


@app.get("/pricing", response_class=HTMLResponse)
async def pricing(request: Request, db: Session = Depends(get_db),
                  token: Optional[str] = Cookie(None, alias="token")):
    user = None
    if token:
        user = auth_module.get_user_from_token(db, token)
    return templates.TemplateResponse(request, "pricing.html", {
        "app_name": APP_NAME, "user": user, "plans": PLANS,
    })


# ── Auth pages ──────────────────────────────────────────────────────

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    return templates.TemplateResponse(request, "login.html", {
        "app_name": APP_NAME, "error": error,
    })


@app.post("/login")
async def login_submit(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
):
    user, error = auth_module.login_user(db, email, password)
    if error:
        return templates.TemplateResponse(request, "login.html", {
            "app_name": APP_NAME, "error": error,
        }, status_code=400)

    token = auth_module.create_token(user.id, user.email, user.is_admin)
    resp = RedirectResponse(url="/chat", status_code=302)
    resp.set_cookie("token", token, httponly=True, max_age=3600 * 72, samesite="lax")
    return resp


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request, error: str = ""):
    return templates.TemplateResponse(request, "signup.html", {
        "app_name": APP_NAME, "error": error,
    })


@app.post("/signup")
async def signup_submit(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(""),
):
    user, error = auth_module.signup_user(db, email, password, name)
    if error:
        return templates.TemplateResponse(request, "signup.html", {
            "app_name": APP_NAME, "error": error,
        }, status_code=400)

    token = auth_module.create_token(user.id, user.email, user.is_admin)
    resp = RedirectResponse(url="/chat", status_code=302)
    resp.set_cookie("token", token, httponly=True, max_age=3600 * 72, samesite="lax")
    return resp


@app.get("/logout")
async def logout():
    resp = RedirectResponse(url="/", status_code=302)
    resp.delete_cookie("token")
    return resp


# ── Dashboard ───────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_user),
):
    plan_info = PLANS.get(user.plan, PLANS["free"])
    user.reset_if_new_month()

    # Recent usage
    usage_records = (
        db.query(UsageRecord)
        .filter(UsageRecord.user_id == user.id)
        .order_by(UsageRecord.created_at.desc())
        .limit(20)
        .all()
    )

    total_cost = (
        db.query(func.sum(UsageRecord.cost_usd))
        .filter(UsageRecord.user_id == user.id)
        .scalar() or 0
    )

    conversation_count = (
        db.query(func.count(Conversation.id))
        .filter(Conversation.user_id == user.id)
        .scalar() or 0
    )

    return templates.TemplateResponse(request, "dashboard.html", {
        "app_name": APP_NAME,
        "user": user,
        "plan_info": plan_info,
        "usage_records": usage_records,
        "total_cost": round(total_cost, 4),
        "conversation_count": conversation_count,
        "stripe_configured": billing_module.is_stripe_configured(),
    })


# ── Chat ────────────────────────────────────────────────────────────

@app.get("/chat", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_user),
    c: str = "",
):
    plan_info = PLANS.get(user.plan, PLANS["free"])
    user.reset_if_new_month()

    # Get user's conversations
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(50)
        .all()
    )

    # Current conversation messages
    messages = []
    current_conv_id = c
    if current_conv_id:
        conv = db.query(Conversation).filter(
            Conversation.id == current_conv_id,
            Conversation.user_id == user.id,
        ).first()
        if conv:
            messages = (
                db.query(Message)
                .filter(Message.conversation_id == current_conv_id)
                .order_by(Message.created_at)
                .all()
            )

    return templates.TemplateResponse(request, "chat.html", {
        "app_name": APP_NAME,
        "user": user,
        "plan_info": plan_info,
        "conversations": conversations,
        "messages": messages,
        "current_conv_id": current_conv_id,
        "allowed_models": plan_info["models"],
        "model_map": MODEL_MAP,
    })


@app.post("/api/chat")
async def api_chat(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Cookie(None, alias="token"),
):
    """API endpoint for chat messages."""
    user = auth_module.get_user_from_token(db, token) if token else None
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    body = await request.json()
    message = body.get("message", "").strip()
    conversation_id = body.get("conversation_id", "") or uuid.uuid4().hex
    model = body.get("model", "haiku")

    if not message:
        return JSONResponse({"error": "Message is required"}, status_code=400)

    result = chat_module.chat(db, user, conversation_id, message, model)
    if "error" in result:
        status = 429 if result.get("type") == "rate_limit" else 400
        if result.get("type") == "limit":
            status = 403
        return JSONResponse(result, status_code=status)

    result["conversation_id"] = conversation_id
    return JSONResponse(result)


@app.post("/api/conversations/new")
async def new_conversation(
    db: Session = Depends(get_db),
    token: Optional[str] = Cookie(None, alias="token"),
):
    """Create a new conversation."""
    user = auth_module.get_user_from_token(db, token) if token else None
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    conv = Conversation(user_id=user.id, title="New conversation")
    db.add(conv)
    db.commit()
    return JSONResponse({"conversation_id": conv.id})


@app.delete("/api/conversations/{conv_id}")
async def delete_conversation(
    conv_id: str,
    db: Session = Depends(get_db),
    token: Optional[str] = Cookie(None, alias="token"),
):
    """Delete a conversation."""
    user = auth_module.get_user_from_token(db, token) if token else None
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    conv = db.query(Conversation).filter(
        Conversation.id == conv_id, Conversation.user_id == user.id
    ).first()
    if conv:
        db.delete(conv)
        db.commit()
    return JSONResponse({"status": "ok"})


# ── Billing ─────────────────────────────────────────────────────────

@app.post("/api/billing/checkout")
async def billing_checkout(
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Cookie(None, alias="token"),
):
    user = auth_module.get_user_from_token(db, token) if token else None
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)

    body = await request.json()
    plan = body.get("plan", "pro")
    result = billing_module.create_checkout_session(user, plan)

    if "error" in result:
        return JSONResponse(result, status_code=400)

    # Save customer ID if newly created
    if not user.stripe_customer_id:
        db.commit()

    return JSONResponse(result)


@app.get("/billing/success")
async def billing_success(request: Request, session_id: str = ""):
    return templates.TemplateResponse(request, "billing_success.html", {
        "app_name": APP_NAME,
    })


@app.post("/api/billing/webhook")
async def billing_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    result = billing_module.handle_webhook(payload, sig, db)
    if "error" in result:
        return JSONResponse(result, status_code=400)
    return JSONResponse(result)


@app.get("/api/billing/portal")
async def billing_portal(
    db: Session = Depends(get_db),
    token: Optional[str] = Cookie(None, alias="token"),
):
    user = auth_module.get_user_from_token(db, token) if token else None
    if not user:
        return JSONResponse({"error": "Not authenticated"}, status_code=401)
    result = billing_module.get_billing_portal_url(user)
    if "error" in result:
        return JSONResponse(result, status_code=400)
    return RedirectResponse(url=result["url"])


# ── Admin ───────────────────────────────────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(_require_user),
):
    if not user.is_admin:
        return RedirectResponse(url="/dashboard", status_code=302)

    # Stats
    total_users = db.query(func.count(User.id)).scalar() or 0
    pro_users = db.query(func.count(User.id)).filter(User.plan == "pro").scalar() or 0
    enterprise_users = db.query(func.count(User.id)).filter(User.plan == "enterprise").scalar() or 0
    total_revenue_monthly = (pro_users * 29) + (enterprise_users * 99)

    total_tokens = db.query(func.sum(UsageRecord.input_tokens + UsageRecord.output_tokens)).scalar() or 0
    total_cost = db.query(func.sum(UsageRecord.cost_usd)).scalar() or 0
    total_conversations = db.query(func.count(Conversation.id)).scalar() or 0

    # Recent users
    users = db.query(User).order_by(User.created_at.desc()).limit(50).all()

    # Recent usage
    recent_usage = (
        db.query(UsageRecord)
        .order_by(UsageRecord.created_at.desc())
        .limit(30)
        .all()
    )

    return templates.TemplateResponse(request, "admin.html", {
        "app_name": APP_NAME,
        "user": user,
        "total_users": total_users,
        "pro_users": pro_users,
        "enterprise_users": enterprise_users,
        "total_revenue_monthly": total_revenue_monthly,
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 4),
        "total_conversations": total_conversations,
        "users": users,
        "recent_usage": recent_usage,
    })


@app.post("/api/admin/users/{user_id}/plan")
async def admin_update_plan(
    user_id: str,
    request: Request,
    db: Session = Depends(get_db),
    token: Optional[str] = Cookie(None, alias="token"),
):
    admin = auth_module.get_user_from_token(db, token) if token else None
    if not admin or not admin.is_admin:
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    body = await request.json()
    plan = body.get("plan", "free")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        return JSONResponse({"error": "User not found"}, status_code=404)

    target.plan = plan
    db.commit()
    return JSONResponse({"status": "ok", "plan": plan})


@app.post("/api/admin/users/{user_id}/toggle")
async def admin_toggle_user(
    user_id: str,
    db: Session = Depends(get_db),
    token: Optional[str] = Cookie(None, alias="token"),
):
    admin = auth_module.get_user_from_token(db, token) if token else None
    if not admin or not admin.is_admin:
        return JSONResponse({"error": "Forbidden"}, status_code=403)

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        return JSONResponse({"error": "User not found"}, status_code=404)

    target.is_active = not target.is_active
    db.commit()
    return JSONResponse({"status": "ok", "is_active": target.is_active})
