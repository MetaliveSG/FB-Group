"""Module 2 — Customer Identity & Authentication."""
import time

import jwt

from app.core.config import settings
from app.tests.factories import make_world
from app.tests.helpers import H, register_customer, staff_token


def test_register_login_refresh(client):
    body = register_customer(client, email="a@b.sg")
    assert body["actor"] == "customer" and body["access_token"] and body["refresh_token"]

    r = client.post("/api/v1/auth/customer/login", json={"email": "a@b.sg", "password": "secret123"})
    assert r.status_code == 200

    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]})
    assert r2.status_code == 200 and r2.json()["access_token"]


def test_duplicate_account_prevented(client):
    register_customer(client, email="dup@b.sg")
    r = client.post("/api/v1/auth/customer/register",
                    json={"email": "dup@b.sg", "password": "secret123"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "email_taken"


def test_wrong_password_rejected(client):
    register_customer(client, email="p@b.sg")
    r = client.post("/api/v1/auth/customer/login", json={"email": "p@b.sg", "password": "nope!!"})
    assert r.status_code == 401


def test_otp_login_and_invalid_otp_blocked(client):
    req = client.post("/api/v1/auth/customer/otp/request", json={"phone": "+6580000001"})
    assert req.status_code == 200
    code = req.json()["debug_code"]
    assert code and len(code) == settings.OTP_LENGTH

    bad = client.post("/api/v1/auth/customer/otp/verify", json={"phone": "+6580000001", "code": "000000"})
    assert bad.status_code == 401 and bad.json()["error"]["code"] == "invalid_otp"

    good = client.post("/api/v1/auth/customer/otp/verify", json={"phone": "+6580000001", "code": code})
    assert good.status_code == 200 and good.json()["actor"] == "customer"


def test_expired_token_rejected(client):
    now = int(time.time())
    token = jwt.encode(
        {"sub": "x", "type": "access", "actor": "customer", "iat": now - 100, "exp": now - 10},
        settings.JWT_SECRET, algorithm=settings.JWT_ALG,
    )
    r = client.get("/api/v1/orders/whatever", headers=H(token))
    assert r.status_code == 401 and r.json()["error"]["code"] == "token_expired"


def test_role_based_auth_separates_actors(client, db):
    w = make_world(db)
    cust = register_customer(client, email="c@b.sg")
    # Customer token cannot reach a staff/CRM endpoint.
    r = client.get("/api/v1/crm/customers", headers=H(cust["access_token"]))
    assert r.status_code == 403 and r.json()["error"]["code"] == "wrong_actor"
    # Staff token cannot place a customer QR order.
    stok = staff_token(client, w.staff_email)
    r2 = client.post("/api/v1/orders",
                     json={"qr_token": w.qr_token, "items": [{"menu_item_id": w.burger_id, "quantity": 1}]},
                     headers=H(stok))
    assert r2.status_code == 403


def test_sso_mock_links_by_email(client, db):
    make_world(db)
    register_customer(client, email="link@b.sg")
    r = client.post("/api/v1/auth/customer/sso",
                    json={"provider": "google", "sub": "google-123", "email": "link@b.sg"})
    assert r.status_code == 200
    # Same email -> linked to the existing customer (no duplicate).
    assert r.json()["customer"]["email"] == "link@b.sg"
