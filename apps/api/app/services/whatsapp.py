"""WhatsApp messaging abstraction + mock provider with retry.

Production swaps `MockWhatsAppProvider` for Twilio/Meta behind the same `send()`
interface. `send_with_retry` gives the resilient delivery path (exponential-ish
backoff is logged but not slept in the PoC) the BC/DR doc references.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger("app.whatsapp")


@dataclass
class SendResult:
    status: str          # "delivered" | "failed"
    provider_ref: str | None
    attempts: int
    reason: str | None = None


class MockWhatsAppProvider:
    """Logs the 'send' and returns delivered. Fails for blank/invalid numbers,
    and (optionally) for the first `fail_first` attempts to exercise retries."""

    def __init__(self, fail_first: int = 0) -> None:
        self.fail_first = fail_first
        self._calls = 0

    def send_once(self, to: str, body: str) -> tuple[bool, str | None, str | None]:
        self._calls += 1
        if not to or not to.strip():
            return False, None, "no_recipient"
        if self._calls <= self.fail_first:
            return False, None, "transient_error"
        ref = "WA-" + secrets.token_hex(5).upper()
        logger.info("whatsapp_sent", extra={"extra": {"to": to, "ref": ref, "len": len(body)}})
        return True, ref, None


def send_with_retry(provider: MockWhatsAppProvider, *, to: str, body: str, max_attempts: int = 3) -> SendResult:
    attempts = 0
    last_reason = None
    while attempts < max_attempts:
        attempts += 1
        ok, ref, reason = provider.send_once(to, body)
        if ok:
            return SendResult(status="delivered", provider_ref=ref, attempts=attempts)
        last_reason = reason
        if reason == "no_recipient":
            break  # non-retryable
        logger.info("whatsapp_retry", extra={"extra": {"to": to, "attempt": attempts, "reason": reason}})
    return SendResult(status="failed", provider_ref=None, attempts=attempts, reason=last_reason)


def get_provider() -> MockWhatsAppProvider:
    return MockWhatsAppProvider()
