"""PSP-agnostic payment abstraction — the seam so HitPay (or any PSP) is a drop-in adapter.

Order-ahead checkout calls `create_payment(...)`; the webhook handler calls `verify_webhook(...)`; wallet
auto-reload calls `charge_saved(...)`; the void flow calls `refund(...)`. Today only `MockPaymentProvider`
is wired (deterministic, no network — same convention as the OTP/WhatsApp/AI mocks: real provider only when a
flag + key are set). When HitPay is approved, add a `HitPayProvider(PaymentProvider)` and
`register_provider("hitpay", HitPayProvider)` — nothing else changes.

Decisions locked (docs/payments-build-spec.md): PSP = HitPay · merchant-of-record = FSG · wallet FSG-issued.
"""
from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from app.core.money import money


@dataclass
class PaymentSession:
    """Result of starting a payment — the diner is sent to `checkout_url` (hosted checkout)."""
    provider: str
    provider_ref: str       # the PSP's payment id
    reference: str          # our reference (order id / reload ref) — echoed back on the webhook
    checkout_url: str
    status: str             # pending | completed


@dataclass
class PaymentResult:
    provider: str
    provider_ref: str
    ok: bool
    status: str             # completed | failed | refunded


@dataclass
class WebhookEvent:
    provider: str
    provider_ref: str
    reference: str          # our reference (order id / reload ref)
    status: str             # completed | failed
    amount: Decimal


class PaymentProvider(ABC):
    """The contract every PSP adapter implements. Keep methods provider-neutral."""

    name: str = "base"

    @abstractmethod
    def create_payment(
        self, *, amount: Decimal, currency: str, reference: str,
        purpose: str = "", redirect_url: str | None = None,
    ) -> PaymentSession:
        """Start a hosted-checkout payment (PayNow/cards/e-wallets/Apple/Google Pay)."""

    @abstractmethod
    def charge_saved(
        self, *, token: str, amount: Decimal, currency: str, reference: str,
    ) -> PaymentResult:
        """Off-session charge against a saved card token — for wallet auto-reload."""

    @abstractmethod
    def verify_webhook(self, *, headers: dict, body: bytes) -> WebhookEvent:
        """Verify the PSP signature + parse the completion event. Raises on bad signature."""

    @abstractmethod
    def refund(self, *, provider_ref: str, amount: Decimal) -> PaymentResult:
        """Refund a captured payment — for the supervisor void flow."""


class MockPaymentProvider(PaymentProvider):
    """Deterministic, no-network stand-in. Every payment 'succeeds'. Used until HitPay is wired."""

    name = "mock"

    def create_payment(self, *, amount, currency, reference, purpose="", redirect_url=None) -> PaymentSession:
        return PaymentSession(
            provider=self.name, provider_ref=f"mock_pay_{reference}", reference=reference,
            checkout_url=f"https://mock.pay/checkout/{reference}", status="pending",
        )

    def charge_saved(self, *, token, amount, currency, reference) -> PaymentResult:
        # Mock: a saved token always charges OK. (HitPay = recurring-billing off-session charge.)
        return PaymentResult(provider=self.name, provider_ref=f"mock_reload_{reference}", ok=True, status="completed")

    def verify_webhook(self, *, headers, body) -> WebhookEvent:
        data = json.loads(body or b"{}")
        return WebhookEvent(
            provider=self.name,
            provider_ref=data.get("payment_id", data.get("provider_ref", "")),
            reference=data.get("reference", data.get("reference_number", "")),
            status=data.get("status", "completed"),
            amount=money(data.get("amount", 0)),
        )

    def refund(self, *, provider_ref, amount) -> PaymentResult:
        return PaymentResult(provider=self.name, provider_ref=f"mock_refund_{provider_ref}", ok=True, status="refunded")


# Adapter registry — HitPay registers here when approved; selection via PAYMENT_PROVIDER env (default mock).
_REGISTRY: dict[str, type[PaymentProvider]] = {"mock": MockPaymentProvider}


def register_provider(name: str, cls: type[PaymentProvider]) -> None:
    _REGISTRY[name] = cls


def get_payment_provider(name: str | None = None) -> PaymentProvider:
    name = name or os.environ.get("PAYMENT_PROVIDER", "mock")
    return _REGISTRY.get(name, MockPaymentProvider)()
