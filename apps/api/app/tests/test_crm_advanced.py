"""Salesforce features: Opportunities/Pipeline, Activity logging, Bulk actions."""
from app.tests.factories import make_world
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token


def _captured(client, w, email):
    cust = register_customer(client, email=email)
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    checkout(client, cust["access_token"], order["id"])
    return cust["customer"]["id"]


def test_pipeline_summary(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    cid = _captured(client, w, "opp@b.sg")
    assert client.post(f"/api/v1/crm/customers/{cid}/opportunities",
                       json={"name": "Catering", "amount": 1000, "stage": "qualified"}, headers=H(otok)).status_code == 201
    client.post(f"/api/v1/crm/customers/{cid}/opportunities",
                json={"name": "Hamper", "amount": 500, "stage": "won"}, headers=H(otok))
    pipe = client.get("/api/v1/crm/pipeline", headers=H(otok)).json()
    assert pipe["open_value"] == 1000.0 and pipe["won_value"] == 500.0 and pipe["open_count"] == 1


def test_opportunity_advance_to_won(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    cid = _captured(client, w, "opp2@b.sg")
    oid = client.post(f"/api/v1/crm/customers/{cid}/opportunities",
                      json={"name": "Deal", "amount": 200, "stage": "proposal"}, headers=H(otok)).json()["id"]
    r = client.patch(f"/api/v1/crm/opportunities/{oid}", json={"stage": "won"}, headers=H(otok))
    assert r.status_code == 200 and r.json()["stage"] == "won" and r.json()["closed_at"]


def test_activity_logged_into_timeline(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    cid = _captured(client, w, "act@b.sg")
    a = client.post(f"/api/v1/crm/customers/{cid}/activities",
                    json={"activity_type": "call", "subject": "Called customer", "body": "Nice chat"}, headers=H(otok))
    assert a.status_code == 201
    acts = client.get(f"/api/v1/crm/customers/{cid}/activities", headers=H(otok)).json()
    assert len(acts) == 1 and acts[0]["activity_type"] == "call"
    tl = client.get(f"/api/v1/crm/customers/{cid}/timeline", headers=H(otok)).json()
    assert any(e["type"] == "activity_call" for e in tl)


def test_bulk_tag_by_ids(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    c1 = _captured(client, w, "b1@b.sg")
    c2 = _captured(client, w, "b2@b.sg")
    r = client.post("/api/v1/crm/bulk/tag", json={"tag": "promo-target", "customer_ids": [c1, c2]}, headers=H(otok))
    assert r.status_code == 200 and r.json()["affected"] == 2
    prof = client.get(f"/api/v1/crm/customers/{c1}", headers=H(otok)).json()
    assert "promo-target" in prof["tags"]


def test_bulk_tag_by_segment(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    _captured(client, w, "s1@b.sg")  # one-visit customer → 'new' segment
    r = client.post("/api/v1/crm/bulk/tag", json={"tag": "newbie", "segment": "new"}, headers=H(otok))
    assert r.status_code == 200 and r.json()["affected"] >= 1


def test_bulk_task_creates_for_many(client, db):
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    c1 = _captured(client, w, "bt1@b.sg")
    c2 = _captured(client, w, "bt2@b.sg")
    r = client.post("/api/v1/crm/bulk/task", json={"title": "Follow up", "customer_ids": [c1, c2]}, headers=H(otok))
    assert r.json()["affected"] == 2
    mine = client.get("/api/v1/crm/tasks", headers=H(otok)).json()
    assert len([t for t in mine if t["title"] == "Follow up"]) == 2


def test_opportunity_tenant_isolation(client, db):
    w1 = make_world(db, name="M1", token_suffix="1")
    w2 = make_world(db, name="M2", token_suffix="2")
    o1 = staff_token(client, w1.owner_email)
    cid = _captured(client, w1, "iso@b.sg")
    oid = client.post(f"/api/v1/crm/customers/{cid}/opportunities",
                      json={"name": "X", "amount": 10}, headers=H(o1)).json()["id"]
    o2 = staff_token(client, w2.owner_email)
    r = client.patch(f"/api/v1/crm/opportunities/{oid}?merchant_id={w2.merchant_id}",
                     json={"stage": "won"}, headers=H(o2))
    assert r.status_code in (403, 404)
