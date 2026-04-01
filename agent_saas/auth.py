"""Authentication — signup, login, JWT tokens, password hashing."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from sqlalchemy.orm import Session

from agent_saas.config import JWT_ALGORITHM, JWT_EXPIRY_HOURS, SECRET_KEY
from agent_saas.models import User


# ── Password hashing (PBKDF2 — no extra deps) ──────────────────────

def _hash_password(password: str, salt: str | None = None) -> str:
    """Hash a password with PBKDF2-SHA256. Returns 'salt$hash'."""
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return f"{salt}${dk.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    """Verify a password against a stored 'salt$hash' string."""
    if "$" not in stored:
        return False
    salt = stored.split("$")[0]
    return hmac.compare_digest(_hash_password(password, salt), stored)


# ── JWT tokens ──────────────────────────────────────────────────────

def create_token(user_id: str, email: str, is_admin: bool = False) -> str:
    """Create a JWT token for a user."""
    payload = {
        "sub": user_id,
        "email": email,
        "admin": is_admin,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ── User operations ─────────────────────────────────────────────────

def signup_user(db: Session, email: str, password: str, name: str = "") -> tuple[User | None, str]:
    """Create a new user. Returns (user, error_message)."""
    email = email.strip().lower()
    if not email or "@" not in email:
        return None, "Invalid email address."
    if len(password) < 6:
        return None, "Password must be at least 6 characters."

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return None, "An account with this email already exists."

    user = User(
        email=email,
        password_hash=_hash_password(password),
        name=name or email.split("@")[0],
        plan="free",
        month_reset=datetime.now(timezone.utc).strftime("%Y-%m"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, ""


def login_user(db: Session, email: str, password: str) -> tuple[User | None, str]:
    """Authenticate a user. Returns (user, error_message)."""
    email = email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None, "No account found with this email."
    if not _verify_password(password, user.password_hash):
        return None, "Incorrect password."
    if not user.is_active:
        return None, "Account is disabled."

    user.last_login = datetime.now(timezone.utc)
    db.commit()
    return user, ""


def get_user_from_token(db: Session, token: str) -> Optional[User]:
    """Look up a user from a JWT token."""
    payload = decode_token(token)
    if not payload:
        return None
    return db.query(User).filter(User.id == payload["sub"]).first()
