"""Database models and helpers — SQLite-backed user, plan, and usage storage."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from agent_v5.config import DATA_DIR

DB_PATH = str(DATA_DIR / "saas.db")


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create all tables if they don't exist."""
    conn = _get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            plan TEXT NOT NULL DEFAULT 'free',
            tokens_used INTEGER NOT NULL DEFAULT 0,
            tokens_limit INTEGER NOT NULL DEFAULT 50000,
            queries_today INTEGER NOT NULL DEFAULT 0,
            last_query_date TEXT NOT NULL DEFAULT '',
            api_key TEXT UNIQUE,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at REAL NOT NULL,
            last_login REAL
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL DEFAULT 'New Chat',
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            tokens_in INTEGER NOT NULL DEFAULT 0,
            tokens_out INTEGER NOT NULL DEFAULT 0,
            model TEXT NOT NULL DEFAULT '',
            created_at REAL NOT NULL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tokens_in INTEGER NOT NULL DEFAULT 0,
            tokens_out INTEGER NOT NULL DEFAULT 0,
            model TEXT NOT NULL DEFAULT '',
            cost_usd REAL NOT NULL DEFAULT 0.0,
            created_at REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    # Seed admin user if not exists
    existing = conn.execute("SELECT id FROM users WHERE email = ?", ("admin@cornerstone.ai",)).fetchone()
    if not existing:
        admin_pw = os.getenv("ADMIN_PASSWORD") or secrets.token_hex(8)
        conn.execute(
            "INSERT INTO users (email, password_hash, name, plan, tokens_limit, is_admin, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("admin@cornerstone.ai", _hash_password(admin_pw), "Admin", "enterprise", 99999999, 1, time.time()),
        )
        conn.commit()
    conn.close()


def _hash_password(password: str) -> str:
    salt = os.getenv("PASSWORD_SALT") or secrets.token_hex(16)
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


# ── Plan definitions ──────────────────────────────────────────────────

PLANS: dict[str, dict[str, Any]] = {
    "free": {
        "name": "Free",
        "price": 0,
        "tokens_limit": 50_000,
        "models": ["claude-haiku-4-20250414"],
        "features": ["Basic chat", "5 conversations", "Community support"],
    },
    "pro": {
        "name": "Pro",
        "price": 29,
        "tokens_limit": 500_000,
        "models": ["claude-haiku-4-20250414", "claude-sonnet-4-20250514"],
        "features": ["Unlimited conversations", "Tool use", "Memory", "Priority support"],
    },
    "enterprise": {
        "name": "Enterprise",
        "price": 99,
        "tokens_limit": 2_000_000,
        "models": ["claude-haiku-4-20250414", "claude-sonnet-4-20250514", "claude-opus-4-20250514"],
        "features": ["All Pro features", "All models", "API access", "Custom prompts", "Dedicated support"],
    },
}


# ── User operations ───────────────────────────────────────────────────

@dataclass
class User:
    id: int
    email: str
    name: str
    plan: str
    tokens_used: int
    tokens_limit: int
    queries_today: int
    is_admin: bool
    api_key: Optional[str]
    created_at: float


def create_user(email: str, password: str, name: str = "") -> Optional[User]:
    conn = _get_db()
    try:
        api_key = f"cs-{secrets.token_hex(24)}"
        conn.execute(
            "INSERT INTO users (email, password_hash, name, api_key, created_at) VALUES (?, ?, ?, ?, ?)",
            (email, _hash_password(password), name, api_key, time.time()),
        )
        conn.commit()
        return get_user_by_email(email)
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def authenticate(email: str, password: str) -> Optional[User]:
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ? AND password_hash = ?",
        (email, _hash_password(password)),
    ).fetchone()
    conn.close()
    if row:
        return _row_to_user(row)
    return None


def get_user_by_email(email: str) -> Optional[User]:
    conn = _get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return _row_to_user(row) if row else None


def get_user_by_id(user_id: int) -> Optional[User]:
    conn = _get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return _row_to_user(row) if row else None


def get_user_by_api_key(api_key: str) -> Optional[User]:
    conn = _get_db()
    row = conn.execute("SELECT * FROM users WHERE api_key = ?", (api_key,)).fetchone()
    conn.close()
    return _row_to_user(row) if row else None


def get_all_users() -> list[User]:
    conn = _get_db()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return [_row_to_user(r) for r in rows]


def update_user_plan(user_id: int, plan: str) -> None:
    if plan not in PLANS:
        return
    conn = _get_db()
    conn.execute(
        "UPDATE users SET plan = ?, tokens_limit = ? WHERE id = ?",
        (plan, PLANS[plan]["tokens_limit"], user_id),
    )
    conn.commit()
    conn.close()


def record_usage(user_id: int, tokens_in: int, tokens_out: int, model: str, cost_usd: float = 0.0) -> None:
    conn = _get_db()
    today = time.strftime("%Y-%m-%d")

    # Reset daily counter if new day
    row = conn.execute("SELECT last_query_date FROM users WHERE id = ?", (user_id,)).fetchone()
    if row and row["last_query_date"] != today:
        conn.execute("UPDATE users SET queries_today = 0, last_query_date = ? WHERE id = ?", (today, user_id))

    total = tokens_in + tokens_out
    conn.execute(
        "UPDATE users SET tokens_used = tokens_used + ?, queries_today = queries_today + 1, last_query_date = ? WHERE id = ?",
        (total, today, user_id),
    )
    conn.execute(
        "INSERT INTO usage_logs (user_id, tokens_in, tokens_out, model, cost_usd, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, tokens_in, tokens_out, model, cost_usd, time.time()),
    )
    conn.commit()
    conn.close()


def get_usage_stats(user_id: int) -> dict[str, Any]:
    conn = _get_db()
    row = conn.execute(
        "SELECT SUM(tokens_in) as total_in, SUM(tokens_out) as total_out, SUM(cost_usd) as total_cost, COUNT(*) as total_queries FROM usage_logs WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return {
        "total_tokens_in": row["total_in"] or 0,
        "total_tokens_out": row["total_out"] or 0,
        "total_cost_usd": round(row["total_cost"] or 0, 4),
        "total_queries": row["total_queries"] or 0,
    }


def get_admin_stats() -> dict[str, Any]:
    conn = _get_db()
    users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    queries = conn.execute("SELECT COUNT(*) as c FROM usage_logs").fetchone()["c"]
    tokens = conn.execute("SELECT SUM(tokens_in) + SUM(tokens_out) as t FROM usage_logs").fetchone()["t"] or 0
    revenue = conn.execute("SELECT SUM(cost_usd) as r FROM usage_logs").fetchone()["r"] or 0
    plan_counts = {}
    for row in conn.execute("SELECT plan, COUNT(*) as c FROM users GROUP BY plan").fetchall():
        plan_counts[row["plan"]] = row["c"]
    conn.close()
    return {
        "total_users": users,
        "total_queries": queries,
        "total_tokens": tokens,
        "total_revenue": round(revenue, 4),
        "plan_counts": plan_counts,
    }


# ── Conversation operations ──────────────────────────────────────────

def create_conversation(user_id: int, title: str = "New Chat") -> int:
    conn = _get_db()
    now = time.time()
    cursor = conn.execute(
        "INSERT INTO conversations (user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (user_id, title, now, now),
    )
    conn.commit()
    conv_id = cursor.lastrowid
    conn.close()
    return conv_id


def get_conversations(user_id: int) -> list[dict[str, Any]]:
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_message(conversation_id: int, role: str, content: str, tokens_in: int = 0, tokens_out: int = 0, model: str = "") -> None:
    conn = _get_db()
    now = time.time()
    conn.execute(
        "INSERT INTO messages (conversation_id, role, content, tokens_in, tokens_out, model, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (conversation_id, role, content, tokens_in, tokens_out, model, now),
    )
    conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, conversation_id))
    conn.commit()
    conn.close()


def get_messages(conversation_id: int) -> list[dict[str, Any]]:
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
        (conversation_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _row_to_user(row: sqlite3.Row) -> User:
    return User(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        plan=row["plan"],
        tokens_used=row["tokens_used"],
        tokens_limit=row["tokens_limit"],
        queries_today=row["queries_today"],
        is_admin=bool(row["is_admin"]),
        api_key=row["api_key"],
        created_at=row["created_at"],
    )
