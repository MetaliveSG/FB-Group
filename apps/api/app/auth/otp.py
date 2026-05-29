"""Mock OTP provider — in-process store with TTL + attempt cap.

Production swaps `_send` for an SMS/WhatsApp gateway behind the same interface.
In local/dev the issued code is returned to the caller (clearly dev-only) so the
demo + tests can complete the flow without a real SMS.
"""
from __future__ import annotations

import secrets
import threading
import time
from dataclasses import dataclass

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("app.otp")


@dataclass
class _Entry:
    code: str
    expires_at: float
    attempts: int = 0


class OtpStore:
    def __init__(self) -> None:
        self._d: dict[str, _Entry] = {}
        self._lock = threading.Lock()

    def issue(self, key: str) -> str:
        code = "".join(secrets.choice("0123456789") for _ in range(settings.OTP_LENGTH))
        with self._lock:
            self._d[key] = _Entry(code=code, expires_at=time.monotonic() + settings.OTP_TTL_SECONDS)
        self._send(key, code)
        return code

    def _send(self, key: str, code: str) -> None:
        # Mock delivery — structured log line stands in for the SMS/WhatsApp send.
        logger.info("otp_sent", extra={"extra": {"to": key, "provider": "mock"}})

    def verify(self, key: str, code: str) -> bool:
        with self._lock:
            entry = self._d.get(key)
            if not entry:
                return False
            if time.monotonic() > entry.expires_at:
                self._d.pop(key, None)
                return False
            if entry.attempts >= settings.OTP_MAX_ATTEMPTS:
                self._d.pop(key, None)
                return False
            entry.attempts += 1
            if secrets.compare_digest(entry.code, code):
                self._d.pop(key, None)
                return True
            return False

    def peek(self, key: str) -> str | None:
        entry = self._d.get(key)
        return entry.code if entry else None

    def clear(self) -> None:
        with self._lock:
            self._d.clear()


otp_store = OtpStore()
