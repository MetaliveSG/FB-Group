"""Shared HTTP helpers for tests."""
from __future__ import annotations

DEMO_PW = "Password123!"


def H(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_customer(client, email="diner@b.sg", phone=None, full_name="Diner", birthday=None,
                      marketing_opt_in=False):
    # accepted_terms=True: PDPA consent is required to create an account (see services/consent.py).
    payload = {"email": email, "password": "secret123", "full_name": full_name,
               "accepted_terms": True, "marketing_opt_in": marketing_opt_in}
    if phone:
        payload["phone"] = phone
    if birthday:
        payload["birthday"] = birthday
    r = client.post("/api/v1/auth/customer/register", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def staff_token(client, email):
    r = client.post("/api/v1/auth/staff/login", json={"email": email, "password": DEMO_PW})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def place_order(client, token, qr_token, items):
    r = client.post("/api/v1/orders", json={"qr_token": qr_token, "items": items}, headers=H(token))
    assert r.status_code == 201, r.text
    return r.json()


def checkout(client, token, order_id, method="paynow", force_outcome=None):
    body = {"method": method}
    if force_outcome:
        body["force_outcome"] = force_outcome
    r = client.post(f"/api/v1/orders/{order_id}/checkout", json=body, headers=H(token))
    assert r.status_code == 200, r.text
    return r.json()
