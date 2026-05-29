"""Salesforce-style CRM: activity timeline, tasks, record owner."""
from app.tests.factories import make_world
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token


def _captured(client, w, email="sf@b.sg"):
    cust = register_customer(client, email=email)
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    checkout(client, cust["access_token"], order["id"])
    return cust


def test_activity_timeline_merges_events(client, db):
    w = make_world(db)
    cust = _captured(client, w)
    otok = staff_token(client, w.owner_email)
    tl = client.get(f"/api/v1/crm/customers/{cust['customer']['id']}/timeline", headers=H(otok)).json()
    types = {e["type"] for e in tl}
    assert "order" in types and "payment" in types and "reward_earn" in types
    # newest first
    assert tl == sorted(tl, key=lambda e: e["ts"], reverse=True)


def test_task_create_list_complete(client, db):
    w = make_world(db)
    cust = _captured(client, w)
    cid = cust["customer"]["id"]
    otok = staff_token(client, w.owner_email)

    created = client.post(f"/api/v1/crm/customers/{cid}/tasks",
                          json={"title": "Call back", "priority": "high"}, headers=H(otok))
    assert created.status_code == 201
    tid = created.json()["id"]

    mine = client.get("/api/v1/crm/tasks", headers=H(otok)).json()
    assert any(t["id"] == tid for t in mine)

    custs = client.get("/api/v1/crm/customers", headers=H(otok)).json()
    assert next(c for c in custs if c["id"] == cid)["open_tasks"] == 1

    done = client.patch(f"/api/v1/crm/tasks/{tid}", json={"status": "done"}, headers=H(otok))
    assert done.status_code == 200 and done.json()["status"] == "done"
    mine2 = client.get("/api/v1/crm/tasks", headers=H(otok)).json()
    assert all(t["id"] != tid for t in mine2)


def test_record_owner_assignment(client, db):
    w = make_world(db)
    cust = _captured(client, w)
    cid = cust["customer"]["id"]
    login = client.post("/api/v1/auth/staff/login",
                        json={"email": w.owner_email, "password": "Password123!"}).json()
    uid = login["user"]["id"]
    otok = login["access_token"]

    r = client.put(f"/api/v1/crm/customers/{cid}/owner", json={"owner_user_id": uid}, headers=H(otok))
    assert r.status_code == 200
    prof = client.get(f"/api/v1/crm/customers/{cid}", headers=H(otok)).json()
    assert prof["owner_user_id"] == uid and prof["owner_name"]


def test_task_tenant_isolation(client, db):
    w1 = make_world(db, name="M1", token_suffix="1")
    w2 = make_world(db, name="M2", token_suffix="2")
    cust = _captured(client, w1, email="iso@b.sg")
    o1 = staff_token(client, w1.owner_email)
    task = client.post(f"/api/v1/crm/customers/{cust['customer']['id']}/tasks",
                       json={"title": "private"}, headers=H(o1)).json()
    # M2 owner cannot complete M1's task.
    o2 = staff_token(client, w2.owner_email)
    r = client.patch(f"/api/v1/crm/tasks/{task['id']}?merchant_id={w2.merchant_id}",
                     json={"status": "done"}, headers=H(o2))
    assert r.status_code in (403, 404)
