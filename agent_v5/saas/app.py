"""Cornerstone AI SaaS Platform — FastAPI application.

Run with: uvicorn agent_v5.saas.app:app --port 8000
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from agent_v5.config import ANTHROPIC_API_KEYS, DEFAULT_ENGINE, DEFAULT_MODEL
from agent_v5.saas import database as db
from agent_v5.saas.auth import create_token, verify_token

try:
    from fastapi import FastAPI, Form, Request, Response, HTTPException
    from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
except ImportError:
    raise ImportError(
        "FastAPI and Jinja2 are required for the SaaS platform. "
        "Install with: pip install fastapi uvicorn jinja2 python-multipart"
    )

# ── App setup ─────────────────────────────────────────────────────────

SAAS_DIR = Path(__file__).parent
TEMPLATES_DIR = SAAS_DIR / "templates"
STATIC_DIR = SAAS_DIR / "static"

app = FastAPI(title="Cornerstone AI", version="5.0.0")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Initialize database on startup
db.init_db()


# ── Helpers ───────────────────────────────────────────────────────────

def _get_current_user(request: Request) -> Optional[db.User]:
    """Extract user from cookie token."""
    token = request.cookies.get("token", "")
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        return None
    return db.get_user_by_id(payload["user_id"])


def _chat_with_engine(messages: list[dict[str, Any]], model: str = "") -> dict[str, Any]:
    """Send messages to the agent_v5 engine and return the response."""
    from agent_v5.engine.discovery import get_engine
    from agent_v5.types import GenerationConfig

    engine = get_engine(DEFAULT_ENGINE)
    use_model = model or DEFAULT_MODEL or "claude-sonnet-4-20250514"

    system = "You are Cornerstone AI, a helpful and capable assistant built on the Jarvis framework. Be concise, accurate, and helpful."

    filtered = [m for m in messages if m.get("role") != "system"]

    config = GenerationConfig(temperature=0.7, max_tokens=4096)
    result = engine.generate(filtered, use_model, config=config, system=system)

    return {
        "text": result.text,
        "model": result.model,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
    }


# ── Page routes ───────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def landing(request: Request) -> Response:
    user = _get_current_user(request)
    if user:
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})


@app.post("/login", response_class=HTMLResponse)
async def login_submit(request: Request, email: str = Form(...), password: str = Form(...)) -> Response:
    user = db.authenticate(email, password)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid email or password"})
    token = create_token(user.id, user.email)
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.set_cookie("token", token, httponly=True, max_age=86400 * 7)
    return resp


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request) -> Response:
    return templates.TemplateResponse("signup.html", {"request": request, "error": ""})


@app.post("/signup", response_class=HTMLResponse)
async def signup_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(""),
) -> Response:
    user = db.create_user(email, password, name)
    if not user:
        return templates.TemplateResponse("signup.html", {"request": request, "error": "Email already registered"})
    token = create_token(user.id, user.email)
    resp = RedirectResponse("/dashboard", status_code=302)
    resp.set_cookie("token", token, httponly=True, max_age=86400 * 7)
    return resp


@app.get("/logout")
async def logout() -> Response:
    resp = RedirectResponse("/", status_code=302)
    resp.delete_cookie("token")
    return resp


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request) -> Response:
    user = _get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    stats = db.get_usage_stats(user.id)
    conversations = db.get_conversations(user.id)
    plan_info = db.PLANS.get(user.plan, db.PLANS["free"])
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "stats": stats,
        "conversations": conversations,
        "plan": plan_info,
        "plans": db.PLANS,
    })


@app.get("/chat", response_class=HTMLResponse)
async def chat_page(request: Request) -> Response:
    user = _get_current_user(request)
    if not user:
        return RedirectResponse("/login", status_code=302)
    conv_id = request.query_params.get("id", "")
    messages: list[dict[str, Any]] = []
    if conv_id:
        messages = db.get_messages(int(conv_id))
    conversations = db.get_conversations(user.id)
    plan_info = db.PLANS.get(user.plan, db.PLANS["free"])
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "user": user,
        "conversations": conversations,
        "messages": messages,
        "conv_id": conv_id,
        "plan": plan_info,
    })


@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request) -> Response:
    user = _get_current_user(request)
    return templates.TemplateResponse("pricing.html", {
        "request": request,
        "user": user,
        "plans": db.PLANS,
    })


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request) -> Response:
    user = _get_current_user(request)
    if not user or not user.is_admin:
        return RedirectResponse("/dashboard", status_code=302)
    stats = db.get_admin_stats()
    users = db.get_all_users()
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "user": user,
        "stats": stats,
        "users": users,
        "plans": db.PLANS,
    })


# ── API routes ────────────────────────────────────────────────────────

@app.post("/api/chat")
async def api_chat(request: Request) -> JSONResponse:
    user = _get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")

    # Check token limits
    if user.tokens_used >= user.tokens_limit:
        raise HTTPException(429, "Token limit reached. Upgrade your plan.")

    body = await request.json()
    message = body.get("message", "").strip()
    conv_id = body.get("conversation_id")

    if not message:
        raise HTTPException(400, "Message is required")

    # Create conversation if needed
    if not conv_id:
        title = message[:50] + ("..." if len(message) > 50 else "")
        conv_id = db.create_conversation(user.id, title)

    # Get conversation history
    history = db.get_messages(int(conv_id))
    messages = [{"role": m["role"], "content": m["content"]} for m in history[-20:]]
    messages.append({"role": "user", "content": message})

    # Store user message
    db.add_message(int(conv_id), "user", message)

    # Get allowed models for plan
    plan_info = db.PLANS.get(user.plan, db.PLANS["free"])
    model = body.get("model", plan_info["models"][0])
    if model not in plan_info["models"]:
        model = plan_info["models"][0]

    try:
        result = _chat_with_engine(messages, model)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    # Store assistant message
    db.add_message(int(conv_id), "assistant", result["text"], result["tokens_in"], result["tokens_out"], result["model"])

    # Record usage
    db.record_usage(user.id, result["tokens_in"], result["tokens_out"], result["model"])

    return JSONResponse({
        "response": result["text"],
        "model": result["model"],
        "tokens_in": result["tokens_in"],
        "tokens_out": result["tokens_out"],
        "conversation_id": conv_id,
    })


@app.post("/api/conversations")
async def create_conv(request: Request) -> JSONResponse:
    user = _get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    body = await request.json()
    title = body.get("title", "New Chat")
    conv_id = db.create_conversation(user.id, title)
    return JSONResponse({"id": conv_id, "title": title})


@app.get("/api/conversations/{conv_id}/messages")
async def get_conv_messages(conv_id: int, request: Request) -> JSONResponse:
    user = _get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    messages = db.get_messages(conv_id)
    return JSONResponse({"messages": messages})


@app.get("/api/usage")
async def get_usage(request: Request) -> JSONResponse:
    user = _get_current_user(request)
    if not user:
        raise HTTPException(401, "Not authenticated")
    stats = db.get_usage_stats(user.id)
    return JSONResponse(stats)


@app.post("/api/admin/update-plan")
async def admin_update_plan(request: Request) -> JSONResponse:
    user = _get_current_user(request)
    if not user or not user.is_admin:
        raise HTTPException(403, "Admin only")
    body = await request.json()
    db.update_user_plan(body["user_id"], body["plan"])
    return JSONResponse({"ok": True})
