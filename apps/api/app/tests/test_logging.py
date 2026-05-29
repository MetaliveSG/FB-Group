"""Logging behaviour (MMQRDepositBot method): secret redaction, per-request access
logging that captures 4xx/5xx, and business errors logged with their code.

These close the gap where 4xx/business errors produced zero log output.
"""
import logging

from app.core.logging import _redact, log_with_context, get_logger
from app.tests.factories import make_world
from app.tests.helpers import H, register_customer


# ── secret redaction (ported from MMQRDepositBot) ────────────────────────────
def test_redact_scrubs_jwt_auth_and_passwords():
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N"
    assert jwt not in _redact(f'{{"token": "{jwt}"}}')
    assert "[REDACTED]" in _redact(f'{{"token": "{jwt}"}}')
    assert "[REDACTED]" in _redact("Authorization: Bearer abc.def.ghi")
    assert "supersecret" not in _redact('password="supersecret123"')


def test_redact_keeps_ordinary_values():
    # short identifiers (hex UUIDs are 32 chars < 40) must survive untouched
    assert _redact('{"merchant_id": "188c3eb57c694330922197f18aeda3d5"}') == \
        '{"merchant_id": "188c3eb57c694330922197f18aeda3d5"}'


def test_log_with_context_tags_caller_and_context(caplog):
    logger = get_logger("app.test")
    with caplog.at_level(logging.INFO, logger="app.test"):
        log_with_context(logger, logging.INFO, "did_thing", order_id="T1", amount=9.9)
    rec = caplog.records[-1]
    assert rec.msg == "did_thing"
    assert rec.extra["caller"] == "test_log_with_context_tags_caller_and_context"
    assert rec.extra["order_id"] == "T1" and rec.extra["amount"] == 9.9


# ── per-request access log ───────────────────────────────────────────────────
def test_request_access_log_records_success(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.request"):
        client.get("/health")
    reqs = [r for r in caplog.records if r.name == "app.request"]
    assert reqs, "no app.request access log emitted"
    last = reqs[-1]
    assert last.extra["status"] == 200 and last.extra["path"] == "/health"
    assert "duration_ms" in last.extra


def test_request_access_log_flags_client_error(client, caplog):
    """An unauthenticated call is now captured as a WARNING-level access line —
    previously 4xx produced no log at all."""
    with caplog.at_level(logging.WARNING, logger="app.request"):
        r = client.get("/api/v1/me/loyalty?merchant_id=nope")
    assert r.status_code >= 400
    warned = [rec for rec in caplog.records
              if rec.name == "app.request" and rec.extra.get("status", 0) >= 400]
    assert warned, "4xx request was not logged"


# ── business errors carry their code ─────────────────────────────────────────
def test_app_error_logged_with_code(client, db, caplog):
    w = make_world(db)
    cust = register_customer(client, email="logtest@b.sg", phone="+6593330001")
    with caplog.at_level(logging.WARNING, logger="app.errors"):
        r = client.post("/api/v1/me/rewards/redeem",
                        json={"merchant_id": w.merchant_id, "item_id": "does-not-exist"},
                        headers=H(cust["access_token"]))
    assert r.status_code == 404
    errs = [rec for rec in caplog.records if rec.name == "app.errors"]
    assert errs and errs[-1].extra["code"] == "reward_not_found"
    assert errs[-1].extra["status"] == 404 and errs[-1].extra["path"].endswith("/rewards/redeem")
