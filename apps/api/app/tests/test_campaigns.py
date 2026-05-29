"""Module 8 — Promotions & Retention Campaigns (+ WhatsApp mock + retry + ROI)."""
from app.services.whatsapp import MockWhatsAppProvider, send_with_retry
from app.tests.factories import make_world
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token


def _captured(client, w, email, phone):
    cust = register_customer(client, email=email, phone=phone)
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    checkout(client, cust["access_token"], order["id"])
    return cust["customer"]["id"]


def test_campaign_create_audience_send_metrics(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    c1 = _captured(client, w, "cam1@b.sg", "+6590000001")
    _captured(client, w, "cam2@b.sg", "+6590000002")

    created = client.post("/api/v1/campaigns",
                          json={"name": "Promo", "campaign_type": "whatsapp_promo",
                                "message_template": "Hi {name}, weekend promo!"}, headers=H(otok))
    assert created.status_code == 201
    cid = created.json()["id"]

    aud = client.post(f"/api/v1/campaigns/{cid}/audience", headers=H(otok))
    assert aud.status_code == 200 and aud.json()["audience_size"] == 2

    send = client.post(f"/api/v1/campaigns/{cid}/send", headers=H(otok))
    assert send.status_code == 200 and send.json()["delivered"] == 2 and send.json()["failed"] == 0

    red = client.post(f"/api/v1/campaigns/{cid}/redemptions",
                      json={"customer_id": c1, "revenue": 20.0}, headers=H(otok))
    assert red.status_code == 201

    m = client.get(f"/api/v1/campaigns/{cid}/metrics", headers=H(otok)).json()
    assert m["delivered"] == 2 and m["redeemed"] == 1 and m["revenue_generated"] == 20.0
    assert m["conversion_rate"] == 0.5      # 1 of 2 delivered
    assert m["cost"] == 0.04                # 2 * $0.02
    assert m["roi"] > 0                     # (20 - 0.04) / 0.04


def test_campaign_segment_audience(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    _captured(client, w, "new1@b.sg", "+6590000010")  # one visit -> 'new' segment
    camp = client.post("/api/v1/campaigns",
                       json={"name": "Welcome back", "campaign_type": "new_customer_return",
                             "message_template": "Welcome {name}"}, headers=H(otok)).json()
    aud = client.post(f"/api/v1/campaigns/{camp['id']}/audience", headers=H(otok)).json()
    assert aud["audience_size"] >= 1


def test_campaign_listing_includes_metrics(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    client.post("/api/v1/campaigns", json={"name": "C1", "campaign_type": "vip_reward"}, headers=H(otok))
    lst = client.get("/api/v1/campaigns", headers=H(otok)).json()
    assert lst and "metrics" in lst[0] and "roi" in lst[0]["metrics"]


def test_whatsapp_mock_retry():
    # Fails twice then succeeds -> delivered on the 3rd attempt.
    res = send_with_retry(MockWhatsAppProvider(fail_first=2), to="+6590000000", body="hi", max_attempts=3)
    assert res.status == "delivered" and res.attempts == 3
    # No recipient -> failed immediately, not retried.
    res2 = send_with_retry(MockWhatsAppProvider(), to="", body="hi")
    assert res2.status == "failed" and res2.attempts == 1


def test_campaign_tenant_isolation(client, db):
    w1 = make_world(db, name="M1", token_suffix="1")
    w2 = make_world(db, name="M2", token_suffix="2")
    o1 = staff_token(client, w1.owner_email)
    cid = client.post("/api/v1/campaigns", json={"name": "X", "campaign_type": "whatsapp_promo"},
                      headers=H(o1)).json()["id"]
    o2 = staff_token(client, w2.owner_email)
    r = client.get(f"/api/v1/campaigns/{cid}?merchant_id={w2.merchant_id}", headers=H(o2))
    assert r.status_code in (403, 404)
