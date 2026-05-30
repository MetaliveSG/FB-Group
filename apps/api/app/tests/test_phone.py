"""Region-aware phone normalization → canonical E.164 (app/core/phone.py), and the
OTP flow honoring the selected region (multi-region readiness)."""
import pytest

from app.core.phone import to_e164


# ── unit: to_e164 ────────────────────────────────────────────────────────────
def test_sg_local_number_gets_country_code():
    assert to_e164("91780055", "SG") == "+6591780055"


def test_my_drops_national_trunk_zero():
    # the classic gotcha: '+60' + '016…' would be invalid; the leading trunk 0 is dropped
    assert to_e164("0161234567", "MY") == "+60161234567"
    assert to_e164("019-123 4567", "MY") == "+60191234567"


def test_id_and_th_trunk_prefix():
    assert to_e164("0812345678", "ID") == "+62812345678"
    assert to_e164("0812345678", "TH") == "+66812345678"


def test_already_international_is_honored():
    assert to_e164("+60161234567", "SG") == "+60161234567"


def test_none_blank_and_garbage():
    assert to_e164(None, "SG") is None
    with pytest.raises(ValueError):
        to_e164("   ", "SG")          # present-but-blank rejected
    with pytest.raises(ValueError):
        to_e164("<script>", "SG")     # non-numeric
    with pytest.raises(ValueError):
        to_e164("12", "SG")           # too short


# ── API: OTP honors region; store key + stored phone are E.164 ───────────────
def test_otp_with_region_normalizes_consistently(client, db):
    # A Malaysian diner types their local '016…' number with region MY.
    body = {"phone": "0161234567", "region": "MY"}
    code = client.post("/api/v1/auth/customer/otp/request", json=body).json()["debug_code"]
    # verify must normalize the SAME way (same OTP store key) and store E.164.
    r = client.post("/api/v1/auth/customer/otp/verify", json={**body, "code": code})
    assert r.status_code == 200, r.text
    assert r.json()["customer"]["phone"] == "+60161234567"


def test_otp_rejects_unsupported_region(client):
    r = client.post("/api/v1/auth/customer/otp/request", json={"phone": "91780055", "region": "US"})
    assert r.status_code == 422  # region pattern ^(SG|MY|ID|TH)$
