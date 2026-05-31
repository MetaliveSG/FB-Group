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


# ─── Merchant management (rename + module flags) ─────────────────────────────
def test_update_merchant_name_and_flags(client, db):
    w = make_world(db, name="EditCo", token_suffix="E")
    super_admin(db)
    rtok = staff_token(client, "root@platform.sg")
    r = client.put(f"/api/v1/platform/merchants/{w.merchant_id}",
                   json={"name": "Renamed", "module_flags": {"pos_enabled": True}}, headers=H(rtok))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["name"] == "Renamed"
    assert body["module_flags"]["pos_enabled"] is True
    # Persisted: a fresh listing reflects both edits.
    ms = client.get("/api/v1/platform/merchants", headers=H(rtok)).json()
    row = next(m for m in ms if m["id"] == w.merchant_id)
    assert row["name"] == "Renamed" and row["module_flags"]["pos_enabled"] is True


def test_update_merchant_rejects_unknown_flag(client, db):
    w = make_world(db, name="FlagCo", token_suffix="F")
    super_admin(db)
    rtok = staff_token(client, "root@platform.sg")
    r = client.put(f"/api/v1/platform/merchants/{w.merchant_id}",
                   json={"module_flags": {"made_up_flag": True}}, headers=H(rtok))
    assert r.status_code == 400


def test_update_merchant_requires_operator(client, db):
    w = make_world(db)
    owner = staff_token(client, w.owner_email)
    assert client.put(f"/api/v1/platform/merchants/{w.merchant_id}",
                      json={"name": "Nope"}, headers=H(owner)).status_code == 403


# ─── Platform operators (super admins) ───────────────────────────────────────
def test_list_invite_operators(client, db):
    super_admin(db)
    rtok = staff_token(client, "root@platform.sg")
    ops = client.get("/api/v1/platform/operators", headers=H(rtok)).json()
    me = next(o for o in ops if o["email"] == "root@platform.sg")
    assert me["is_self"] is True
    # Invite a second operator who can then reach the console.
    r = client.post("/api/v1/platform/operators",
                    json={"email": "op2@platform.sg", "password": "Password123!", "full_name": "Op Two"},
                    headers=H(rtok))
    assert r.status_code == 201, r.text
    op2 = staff_token(client, "op2@platform.sg")
    assert client.get("/api/v1/platform/overview", headers=H(op2)).status_code == 200
    # Duplicate email rejected.
    dup = client.post("/api/v1/platform/operators",
                      json={"email": "op2@platform.sg", "password": "Password123!"}, headers=H(rtok))
    assert dup.status_code == 409


def test_revoke_operator_guards(client, db):
    me = super_admin(db)
    rtok = staff_token(client, "root@platform.sg")
    # Can't revoke yourself.
    assert client.delete(f"/api/v1/platform/operators/{me.id}", headers=H(rtok)).status_code == 403
    # Can't revoke the last operator (here `me` is the only one besides any invited).
    client.post("/api/v1/platform/operators",
                json={"email": "op3@platform.sg", "password": "Password123!"}, headers=H(rtok))
    ops = client.get("/api/v1/platform/operators", headers=H(rtok)).json()
    op3 = next(o for o in ops if o["email"] == "op3@platform.sg")
    # Revoking the freshly-invited one succeeds (more than one operator exists).
    assert client.delete(f"/api/v1/platform/operators/{op3['id']}", headers=H(rtok)).status_code == 204
    op3tok = client.post("/api/v1/auth/staff/login",
                         json={"email": "op3@platform.sg", "password": "Password123!"}).json()["access_token"]
    assert client.get("/api/v1/platform/overview", headers=H(op3tok)).status_code == 403


def test_operators_require_operator(client, db):
    w = make_world(db)
    owner = staff_token(client, w.owner_email)
    assert client.get("/api/v1/platform/operators", headers=H(owner)).status_code == 403
    assert client.post("/api/v1/platform/operators",
                       json={"email": "x@x.sg", "password": "Password123!"},
                       headers=H(owner)).status_code == 403


# ─── Coalition management (create / edit / membership) ───────────────────────
def test_coalition_crud_and_membership(client, db):
    w = make_world(db, name="CoaCo", token_suffix="K")
    super_admin(db)
    rtok = staff_token(client, "root@platform.sg")
    # Create.
    cid = client.post("/api/v1/platform/coalitions", json={"name": "New Ring"}, headers=H(rtok)).json()["id"]
    # Rename + deactivate.
    upd = client.patch(f"/api/v1/platform/coalitions/{cid}",
                       json={"name": "Ring SG", "is_active": False}, headers=H(rtok)).json()
    assert upd["name"] == "Ring SG" and upd["is_active"] is False
    # Add member.
    added = client.post(f"/api/v1/platform/coalitions/{cid}/members",
                        json={"merchant_id": w.merchant_id}, headers=H(rtok))
    assert added.status_code == 201
    assert w.merchant_id in added.json()["member_ids"]
    # Duplicate add rejected.
    assert client.post(f"/api/v1/platform/coalitions/{cid}/members",
                       json={"merchant_id": w.merchant_id}, headers=H(rtok)).status_code == 409
    # Remove member.
    removed = client.delete(f"/api/v1/platform/coalitions/{cid}/members/{w.merchant_id}", headers=H(rtok))
    assert removed.status_code == 200 and w.merchant_id not in removed.json()["member_ids"]
    # Removing a non-member 404s.
    assert client.delete(f"/api/v1/platform/coalitions/{cid}/members/{w.merchant_id}",
                         headers=H(rtok)).status_code == 404


def test_coalition_management_requires_operator(client, db):
    w = make_world(db)
    owner = staff_token(client, w.owner_email)
    assert client.post("/api/v1/platform/coalitions", json={"name": "X"},
                       headers=H(owner)).status_code == 403
