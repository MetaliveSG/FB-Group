"""Operator console — platform super admin APIs + access control."""
from app.models.loyalty import Coalition, coalition_members
from app.tests.factories import make_world, super_admin
from app.tests.helpers import H, staff_token


def test_overview_aggregates_ecosystem(client, db):
    make_world(db, name="A", token_suffix="A")
    make_world(db, name="B", token_suffix="B")
    super_admin(db)
    rtok = staff_token(client, "root@platform.sg")
    ov = client.get("/api/v1/platform/overview", headers=H(rtok)).json()
    assert ov["merchants_total"] >= 2 and ov["brands"] >= 2 and "gmv" in ov


def test_merchant_directory_with_kpis(client, db):
    make_world(db, name="A", token_suffix="A")
    super_admin(db)
    rtok = staff_token(client, "root@platform.sg")
    ms = client.get("/api/v1/platform/merchants", headers=H(rtok)).json()
    a = next(m for m in ms if m["name"] == "A")
    assert a["owner_email"] and a["outlets"] >= 1 and a["is_active"] is True


def test_non_operator_blocked(client, db):
    w = make_world(db)
    owner = staff_token(client, w.owner_email)  # merchant owner, NOT super admin
    assert client.get("/api/v1/platform/overview", headers=H(owner)).status_code == 403
    assert client.get("/api/v1/platform/merchants", headers=H(owner)).status_code == 403


def test_onboard_merchant_creates_working_owner(client, db):
    super_admin(db)
    rtok = staff_token(client, "root@platform.sg")
    r = client.post("/api/v1/platform/merchants",
                    json={"name": "NewCo", "owner_email": "newowner@x.sg",
                          "owner_password": "Password123!", "owner_name": "New Owner"}, headers=H(rtok))
    assert r.status_code == 201
    # The freshly-created owner can log in and reach their (empty) CRM.
    ntok = staff_token(client, "newowner@x.sg")
    crm = client.get("/api/v1/crm/customers", headers=H(ntok))
    assert crm.status_code == 200 and crm.json() == []
    # Duplicate owner email rejected.
    dup = client.post("/api/v1/platform/merchants",
                      json={"name": "NewCo2", "owner_email": "newowner@x.sg", "owner_password": "Password123!"},
                      headers=H(rtok))
    assert dup.status_code == 409


def test_suspend_merchant(client, db):
    super_admin(db)
    rtok = staff_token(client, "root@platform.sg")
    mid = client.post("/api/v1/platform/merchants",
                      json={"name": "SuspendCo", "owner_email": "s@x.sg", "owner_password": "Password123!"},
                      headers=H(rtok)).json()["merchant_id"]
    r = client.patch(f"/api/v1/platform/merchants/{mid}", json={"is_active": False}, headers=H(rtok))
    assert r.status_code == 200 and r.json()["is_active"] is False


def test_coalitions_listing(client, db):
    w = make_world(db, name="C", token_suffix="C")
    coa = Coalition(name="SG Eats")
    db.add(coa)
    db.flush()
    db.execute(coalition_members.insert().values(coalition_id=coa.id, merchant_id=w.merchant_id))
    db.commit()
    super_admin(db)
    rtok = staff_token(client, "root@platform.sg")
    cs = client.get("/api/v1/platform/coalitions", headers=H(rtok)).json()
    assert any(c["name"] == "SG Eats" and "C" in c["members"] for c in cs)
