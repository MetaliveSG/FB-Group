"""Password hashing (bcrypt) and JWT token helpers (PyJWT, HS256)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


# --- Passwords -----------------------------------------------------------
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# --- JWT -----------------------------------------------------------------
def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str, claims: dict[str, Any] | None = None,
                        ttl_minutes: int | None = None) -> str:
    minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES if ttl_minutes is None else ttl_minutes
    return _encode(subject, "access", timedelta(minutes=minutes), claims)


def create_refresh_token(subject: str, claims: dict[str, Any] | None = None) -> str:
    return _encode(subject, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), claims)


def _encode(subject: str, token_type: str, ttl: timedelta, claims: dict[str, Any] | None) -> str:
    now = _now()
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + ttl).timestamp()),
    }
    if claims:
        payload.update(claims)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def decode_token(token: str) -> dict[str, Any]:
    """Decode + verify a JWT. Raises jwt.PyJWTError (incl. ExpiredSignatureError) on failure."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
