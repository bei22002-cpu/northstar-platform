"""Platform configuration — loads from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from agent_saas directory
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)

# ── Core ────────────────────────────────────────────────────────────
SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-please")
DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(Path(__file__).resolve().parent / "data.db"))
DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

# ── Anthropic ───────────────────────────────────────────────────────
ANTHROPIC_API_KEYS: list[str] = []
for i in range(1, 11):
    key = os.getenv(f"ANTHROPIC_API_KEY_{i}")
    if key:
        ANTHROPIC_API_KEYS.append(key)
if not ANTHROPIC_API_KEYS:
    single = os.getenv("ANTHROPIC_API_KEY", "")
    if single:
        ANTHROPIC_API_KEYS.append(single)

WORKSPACE: str = os.getenv("WORKSPACE", "./backend")

# ── Stripe ──────────────────────────────────────────────────────────
STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# Price IDs from Stripe Dashboard
STRIPE_PRICE_PRO: str = os.getenv("STRIPE_PRICE_PRO", "")
STRIPE_PRICE_ENTERPRISE: str = os.getenv("STRIPE_PRICE_ENTERPRISE", "")

# ── Plans ───────────────────────────────────────────────────────────
PLANS: dict[str, dict] = {
    "free": {
        "name": "Free",
        "price": 0,
        "monthly_tokens": 50_000,
        "models": ["haiku"],
        "features": ["Basic AI chat", "Haiku model only", "50K tokens/month"],
    },
    "pro": {
        "name": "Pro",
        "price": 29,
        "monthly_tokens": 500_000,
        "models": ["haiku", "sonnet"],
        "features": [
            "Sonnet + Haiku models",
            "500K tokens/month",
            "RAG codebase search",
            "Persistent memory",
            "Priority support",
        ],
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 99,
        "monthly_tokens": 2_000_000,
        "models": ["haiku", "sonnet", "opus"],
        "features": [
            "All models including Opus",
            "2M tokens/month",
            "Multi-agent orchestration",
            "GitHub integration",
            "Auto test generation",
            "Linting integration",
            "Custom system prompts",
            "Dedicated support",
        ],
    },
}

# Model mapping
MODEL_MAP: dict[str, str] = {
    "opus": "claude-opus-4-5",
    "sonnet": "claude-sonnet-4-5-20250514",
    "haiku": "claude-haiku-4-5-20250514",
}

# Cost per 1M tokens (USD)
MODEL_COSTS: dict[str, dict[str, float]] = {
    "claude-opus-4-5": {"input": 15.0, "output": 75.0},
    "claude-sonnet-4-5-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5-20250514": {"input": 0.80, "output": 4.0},
}

# ── JWT ─────────────────────────────────────────────────────────────
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRY_HOURS: int = 72

# ── App ─────────────────────────────────────────────────────────────
APP_NAME: str = os.getenv("APP_NAME", "Cornerstone AI")
APP_URL: str = os.getenv("APP_URL", "http://localhost:8000")

# ── Admin ───────────────────────────────────────────────────────────
ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@cornerstone.ai")
ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")
