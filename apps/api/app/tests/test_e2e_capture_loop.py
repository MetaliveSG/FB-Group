"""THE golden flow: scan QR -> register -> order -> checkout -> points -> captured in CRM.

This single test exercises required flows 1-11 end to end.
"""
from app.tests.factories import make_world
from app.tests.helpers import H, staff_token


def test_scan_qr_to_crm_capture(client, db):
    w = make_world(db, name="Golden")

    # 1) SCAN QR  -> resolves merchant/brand/outlet/table + menu (no auth).
    ctx = client.get(f"/api/v1/qr/{w.qr_token}").json()
    assert ctx["outlet"]["id"] == w.outlet_id and ctx["table"]["label"] == "T01"
    item_id = ctx["menu"]["categories"][0]["items"][0]["id"]

    # 2) REGISTER / LOG IN via mobile OTP (mock).
    phone = "+6588881234"
    code = client.post("/api/v1/auth/customer/otp/request", json={"phone": phone}).json()["debug_code"]
    auth = client.post("/api/v1/auth/customer/otp/verify",
                       json={"phone": phone, "code": code, "full_name": "Golden Guest",
                             "accepted_terms": True}).json()
    ctok = auth["access_token"]
    customer_id = auth["customer"]["id"]

    # 3) ORDER items (table context preserved via qr_token).
    order = client.post("/api/v1/orders",
                        json={"qr_token": w.qr_token, "items": [{"menu_item_id": item_id, "quantity": 2}]},
                        headers=H(ctok)).json()
    assert order["status"] == "pending" and order["total"] > 0

    # 4) CHECKOUT with simulated payment.
    co = client.post(f"/api/v1/orders/{order['id']}/checkout",
                     json={"method": "paynow"}, headers=H(ctok)).json()
    assert co["payment"]["status"] == "success" and co["transaction_id"]

    # 5) REWARDS points issued.
    assert co["points_earned"] > 0

    # 6) MERCHANT LOGS IN.
    otok = staff_token(client, w.owner_email)

    # 7) MERCHANT VIEWS CUSTOMER IN CRM — the captured diner is present and profiled.
    custs = client.get("/api/v1/crm/customers", headers=H(otok)).json()
    assert any(c["id"] == customer_id for c in custs)

    profile = client.get(f"/api/v1/crm/customers/{customer_id}", headers=H(otok)).json()
    assert profile["metrics"]["visit_count"] == 1
    assert profile["metrics"]["points_balance"] == co["points_earned"]
    assert profile["metrics"]["lifecycle_stage"] == "new"
    assert len(profile["transactions"]) == 1 and len(profile["rewards"]) >= 1

    # 9) MERCHANT VIEWS SALES DASHBOARD.
    summary = client.get("/api/v1/reports/summary", headers=H(otok)).json()
    assert summary["orders"] == 1 and summary["revenue"] == co["payment"]["amount"]

    # 10) MERCHANT VIEWS FORECAST.
    fc = client.get("/api/v1/reports/forecast", headers=H(otok)).json()
    assert fc["method"] == "moving_average" and len(fc["forecast"]) == 7

    # 11) PERMISSION BOUNDARY — a different merchant cannot see this customer.
    other = make_world(db, name="Other", token_suffix="OTH")
    other_owner = staff_token(client, other.owner_email)
    other_list = client.get("/api/v1/crm/customers", headers=H(other_owner)).json()
    assert all(c["id"] != customer_id for c in other_list)
