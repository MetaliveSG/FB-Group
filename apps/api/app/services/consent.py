"""PDPA consent — capture, audit, and the current marketing flag.

SG PDPA: collect/use PII only with consent + notice of purpose; marketing needs EXPRESS opt-in
(also Spam Control Act); consent is withdrawable. We record every consent action in an append-only
`customer_consents` audit trail (the legal record) and keep `Customer.marketing_consent` as the
denormalised current flag campaigns filter on. `merchant_id` = the data-controller (loyalty domain).
"""
from __future__ import annotations

from app.core.errors import AppError
from app.models.identity import Customer, CustomerConsent

# Bump when the privacy notice / declared purposes change → re-prompt on next capture.
CONSENT_VERSION = "2026-06-05"

PURPOSE_TERMS = "terms"        # acknowledgement of the privacy notice / service-use purposes
PURPOSE_MARKETING = "marketing"  # express opt-in to promotional messages


def record_consent(db, *, customer_id: str, merchant_id: str | None, purpose: str,
                   granted: bool, source: str, ip: str | None = None,
                   version: str = CONSENT_VERSION) -> None:
    """Append one immutable consent event to the audit trail."""
    db.add(CustomerConsent(customer_id=customer_id, merchant_id=merchant_id, purpose=purpose,
                           granted=bool(granted), source=source, ip=ip, version=version))


def capture_signup_consent(db, *, customer: Customer, merchant_id: str | None, accepted_terms: bool,
                           marketing_opt_in: bool, source: str, ip: str | None = None) -> None:
    """At the point of capture (new customer): require the notice acknowledgement, then record the
    terms + marketing decisions and set the current marketing flag. Raises if terms not accepted."""
    if not accepted_terms:
        raise AppError("You must accept the Terms & Privacy Policy to continue",
                       code="consent_required", status_code=422)
    record_consent(db, customer_id=customer.id, merchant_id=merchant_id, purpose=PURPOSE_TERMS,
                   granted=True, source=source, ip=ip)
    record_consent(db, customer_id=customer.id, merchant_id=merchant_id, purpose=PURPOSE_MARKETING,
                   granted=bool(marketing_opt_in), source=source, ip=ip)
    customer.marketing_consent = bool(marketing_opt_in)


def set_marketing(db, *, customer: Customer, merchant_id: str | None, granted: bool,
                  source: str = "profile", ip: str | None = None) -> None:
    """Grant or WITHDRAW marketing consent (the withdrawal path) — records an event + updates the flag."""
    record_consent(db, customer_id=customer.id, merchant_id=merchant_id, purpose=PURPOSE_MARKETING,
                   granted=bool(granted), source=source, ip=ip)
    customer.marketing_consent = bool(granted)
