"""AI agent chat engine with usage metering."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import anthropic
from sqlalchemy.orm import Session

from agent_saas.config import (
    ANTHROPIC_API_KEYS,
    MODEL_COSTS,
    MODEL_MAP,
    PLANS,
    WORKSPACE,
)
from agent_saas.models import Conversation, Message, UsageRecord, User


SYSTEM_PROMPT = """You are an expert AI assistant powered by Cornerstone AI. You help users with:
- Writing, editing, and reviewing code
- Answering technical questions
- Explaining concepts clearly
- Debugging and troubleshooting
- Planning and architecture

Be concise, accurate, and helpful. Format code blocks with language tags.
If you don't know something, say so honestly."""


def _get_client() -> anthropic.Anthropic | None:
    """Get an Anthropic client with an available API key."""
    for key in ANTHROPIC_API_KEYS:
        try:
            return anthropic.Anthropic(api_key=key)
        except Exception:
            continue
    return None


def _calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Calculate USD cost for a request."""
    costs = MODEL_COSTS.get(model, {"input": 3.0, "output": 15.0})
    return (input_tokens * costs["input"] / 1_000_000) + (
        output_tokens * costs["output"] / 1_000_000
    )


def check_user_access(user: User, model_short: str) -> str | None:
    """Check if the user has access to the requested model. Returns error or None."""
    plan_info = PLANS.get(user.plan, PLANS["free"])
    allowed_models = plan_info["models"]
    if model_short not in allowed_models:
        return (
            f"Your {user.plan.title()} plan doesn't include the {model_short} model. "
            f"Upgrade to access it."
        )

    user.reset_if_new_month()
    if user.tokens_used_this_month >= plan_info["monthly_tokens"]:
        return (
            f"You've used all {plan_info['monthly_tokens']:,} tokens for this month. "
            f"Upgrade your plan for more tokens."
        )
    return None


def get_conversation_messages(db: Session, conversation_id: str) -> list[dict[str, str]]:
    """Load conversation history as Anthropic-compatible messages."""
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .all()
    )
    result: list[dict[str, str]] = []
    for m in msgs:
        result.append({"role": m.role, "content": m.content})
    return result


def chat(
    db: Session,
    user: User,
    conversation_id: str,
    user_message: str,
    model_short: str = "haiku",
) -> dict[str, Any]:
    """Send a message to Claude and return the response with usage stats."""
    # Check access
    access_error = check_user_access(user, model_short)
    if access_error:
        return {"error": access_error, "type": "limit"}

    # Resolve model
    model = MODEL_MAP.get(model_short, MODEL_MAP["haiku"])

    # Get or create conversation
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        conversation = Conversation(
            id=conversation_id,
            user_id=user.id,
            title=user_message[:80] if user_message else "New conversation",
            model=model,
        )
        db.add(conversation)
        db.commit()

    # Save user message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=user_message,
    )
    db.add(user_msg)
    db.commit()

    # Build messages for API
    history = get_conversation_messages(db, conversation_id)

    # Call Anthropic
    client = _get_client()
    if not client:
        return {"error": "No API keys configured. Contact support.", "type": "config"}

    try:
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=history,
        )
    except anthropic.RateLimitError:
        return {"error": "Rate limited. Please try again in a moment.", "type": "rate_limit"}
    except anthropic.BadRequestError as e:
        return {"error": f"Request error: {e}", "type": "bad_request"}
    except Exception as e:
        return {"error": f"API error: {e}", "type": "api_error"}

    # Extract response
    assistant_text = ""
    for block in response.content:
        if hasattr(block, "text"):
            assistant_text += block.text

    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    total_tokens = input_tokens + output_tokens
    cost = _calculate_cost(model, input_tokens, output_tokens)

    # Save assistant message
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
    )
    db.add(assistant_msg)

    # Update usage
    user.reset_if_new_month()
    user.tokens_used_this_month += total_tokens
    db.commit()

    # Record usage
    usage = UsageRecord(
        user_id=user.id,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost,
    )
    db.add(usage)
    db.commit()

    plan_info = PLANS.get(user.plan, PLANS["free"])
    tokens_remaining = max(0, plan_info["monthly_tokens"] - user.tokens_used_this_month)

    return {
        "response": assistant_text,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
        "tokens_used_this_month": user.tokens_used_this_month,
        "tokens_remaining": tokens_remaining,
        "monthly_limit": plan_info["monthly_tokens"],
    }
