"""Pipeline modes (sales/winback), the RFM win-back launcher, and merchant settings toggle."""
from app.tests.factories import make_world
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token


def _captured(client, w, email, phone=None):
    cust = register_customer(client, email=email, phone=phone)
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    checkout(client, cust["access_token"], order["id"])
    return cust["customer"]["id"]


def test_winback_pipeline_mode(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    cid = _captured(client, w, "wb@b.sg")

    o = client.post(f"/api/v1/crm/customers/{cid}/opportunities",
                    json={"name": "Recover", "amount": 50, "pipeline_type": "winback", "stage": "at_risk"},
                    headers=H(otok))
    assert o.status_code == 201 and o.json()["pipeline_type"] == "winback"

    pipe = client.get("/api/v1/crm/pipeline?pipeline_type=winback", headers=H(otok)).json()
    assert pipe["pipeline_type"] == "winback" and pipe["open_count"] == 1
    stages = [s["stage"] for s in pipe["stages"]]
    assert "at_risk" in stages and "recovered" in stages
    # The sales pipeline is a separate board.
    assert client.get("/api/v1/crm/pipeline?pipeline_type=sales", headers=H(otok)).json()["open_count"] == 0

    r = client.patch(f"/api/v1/crm/opportunities/{o.json()['id']}", json={"stage": "recovered"}, headers=H(otok))
    assert r.status_code == 200 and r.json()["stage"] == "recovered" and r.json()["closed_at"]
    assert client.get("/api/v1/crm/pipeline?pipeline_type=winback", headers=H(otok)).json()["won_value"] == 50.0


def test_stage_must_match_pipeline_type(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    cid = _captured(client, w, "wb2@b.sg")
    r = client.post(f"/api/v1/crm/customers/{cid}/opportunities",
                    json={"name": "X", "pipeline_type": "winback", "stage": "prospecting"}, headers=H(otok))
    assert r.status_code == 409  # prospecting isn't a winback stage


def test_winback_launcher_creates_opps_and_campaign(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    c1 = _captured(client, w, "l1@b.sg", "+6590001001")
    c2 = _captured(client, w, "l2@b.sg", "+6590001002")
    r = client.post("/api/v1/crm/winback",
                    json={"customer_ids": [c1, c2], "create_campaign": True}, headers=H(otok))
    assert r.status_code == 200
    body = r.json()
    assert body["targets"] == 2 and body["opportunities_created"] == 2
    assert body["campaign_id"] and body["campaign_delivered"] == 2
    assert client.get("/api/v1/crm/pipeline?pipeline_type=winback", headers=H(otok)).json()["open_count"] == 2


def test_winback_requires_targets(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    assert client.post("/api/v1/crm/winback", json={}, headers=H(otok)).status_code == 409


def test_merchant_settings_toggle(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    assert client.get("/api/v1/org/settings", headers=H(otok)).json()["pipeline_enabled"] is True
    upd = client.patch("/api/v1/org/settings", json={"pipeline_enabled": False}, headers=H(otok))
    assert upd.status_code == 200 and upd.json()["pipeline_enabled"] is False
    assert client.get("/api/v1/org/settings", headers=H(otok)).json()["pipeline_enabled"] is False


def test_settings_patch_requires_owner(client, db):
    w = make_world(db)
    mgr = staff_token(client, w.outlet_mgr_email)  # outlet manager lacks merchant.manage
    assert client.patch("/api/v1/org/settings", json={"pipeline_enabled": False}, headers=H(mgr)).status_code == 403
