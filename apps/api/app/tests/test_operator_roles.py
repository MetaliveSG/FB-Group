"""Granular operator (platform-tier) roles — Owner / Admin / Onboarder / Support.

Verifies least-privilege + separation-of-duties on the operator console, and the
read-vs-full drill-in capability into a merchant.
"""
from app.auth.permissions import seed_rbac
from app.core.security import hash_password
from app.models.enums import ScopeType
from app.models.identity import User, UserRoleAssignment
from app.tests.factories import make_world, super_admin
from app.tests.helpers import H, staff_token


def _operator(db, email, role):
    """Create a platform operator login holding `role` (a platform-tier role name)."""
    roles = seed_rbac(db)
    u = User(email=email, full_name=email, password_hash=hash_password("Password123!"))
    db.add(u)
    db.flush()
    db.add(UserRoleAssignment(user_id=u.id, role_id=roles[role].id,
                              scope_type=ScopeType.PLATFORM.value, scope_id=None))
    db.commit()
    return u


def test_admin_manages_merchants_but_not_operators(client, db):
    w = make_world(db, name="A", token_suffix="A")
    _operator(db, "admin@platform.sg", "platform_admin")
    t = staff_token(client, "admin@platform.sg")
    # Can run the merchant side of the console.
    assert client.get("/api/v1/platform/overview", headers=H(t)).status_code == 200
    assert client.get("/api/v1/platform/merchants", headers=H(t)).status_code == 200
    assert client.post("/api/v1/platform/merchants",
                       json={"name": "NewCo", "owner_email": "no@x.sg", "owner_password": "Password123!"},
                       headers=H(t)).status_code == 201
    assert client.patch(f"/api/v1/platform/merchants/{w.merchant_id}",
                        json={"is_active": False}, headers=H(t)).status_code == 200
    assert client.post("/api/v1/platform/coalitions", json={"name": "Ring"}, headers=H(t)).status_code == 201
    # ...but CANNOT manage operators (separation of duties — Owner-only).
    assert client.get("/api/v1/platform/operators", headers=H(t)).status_code == 403
    assert client.post("/api/v1/platform/operators",
                       json={"email": "x@x.sg", "password": "Password123!"}, headers=H(t)).status_code == 403


def test_onboarder_can_onboard_not_suspend_or_coalitions(client, db):
    w = make_world(db, name="B", token_suffix="B")
    _operator(db, "sales@platform.sg", "platform_onboarder")
    t = staff_token(client, "sales@platform.sg")
    assert client.get("/api/v1/platform/merchants", headers=H(t)).status_code == 200
    assert client.post("/api/v1/platform/merchants",
                       json={"name": "OnbCo", "owner_email": "onb@x.sg", "owner_password": "Password123!"},
                       headers=H(t)).status_code == 201
    # No suspend, no coalitions, no operators, no drill-in.
    assert client.patch(f"/api/v1/platform/merchants/{w.merchant_id}",
                        json={"is_active": False}, headers=H(t)).status_code == 403
    assert client.post("/api/v1/platform/coalitions", json={"name": "X"}, headers=H(t)).status_code == 403
    assert client.get("/api/v1/platform/operators", headers=H(t)).status_code == 403
    assert client.get(f"/api/v1/crm/customers?merchant_id={w.merchant_id}", headers=H(t)).status_code == 403


def test_support_is_read_only_with_read_drilldown(client, db):
    w = make_world(db, name="C", token_suffix="C")
    _operator(db, "support@platform.sg", "platform_support")
    t = staff_token(client, "support@platform.sg")
    # Platform-level reads OK; platform-level writes blocked.
    assert client.get("/api/v1/platform/overview", headers=H(t)).status_code == 200
    assert client.get("/api/v1/platform/merchants", headers=H(t)).status_code == 200
    assert client.post("/api/v1/platform/merchants",
                       json={"name": "Nope", "owner_email": "n@x.sg", "owner_password": "Password123!"},
                       headers=H(t)).status_code == 403
    # Drill-in is READ-ONLY: view endpoints work, write/manage endpoints 403.
    assert client.get(f"/api/v1/crm/customers?merchant_id={w.merchant_id}", headers=H(t)).status_code == 200
    assert client.get(f"/api/v1/reports/summary?merchant_id={w.merchant_id}", headers=H(t)).status_code == 200
    assert client.get(f"/api/v1/org/nav-flags?merchant_id={w.merchant_id}", headers=H(t)).status_code == 200
    assert client.post(f"/api/v1/org/brands?merchant_id={w.merchant_id}",
                       json={"name": "hostile"}, headers=H(t)).status_code == 403
    assert client.patch(f"/api/v1/org/settings?merchant_id={w.merchant_id}",
                        json={"pos_enabled": True}, headers=H(t)).status_code == 403


def test_admin_full_drilldown(client, db):
    """An Admin operator drills in with FULL merchant access (acts like the owner)."""
    w = make_world(db, name="D", token_suffix="D")
    _operator(db, "admin2@platform.sg", "platform_admin")
    t = staff_token(client, "admin2@platform.sg")
    assert client.get(f"/api/v1/crm/customers?merchant_id={w.merchant_id}", headers=H(t)).status_code == 200
    assert client.patch(f"/api/v1/org/settings?merchant_id={w.merchant_id}",
                        json={"pos_enabled": True}, headers=H(t)).status_code == 200  # write allowed


def test_invite_with_role_and_list_shows_role(client, db):
    super_admin(db)  # Owner
    rtok = staff_token(client, "root@platform.sg")
    r = client.post("/api/v1/platform/operators",
                    json={"email": "newsupport@platform.sg", "password": "Password123!",
                          "role": "platform_support"}, headers=H(rtok))
    assert r.status_code == 201 and r.json()["role"] == "platform_support"
    ops = client.get("/api/v1/platform/operators", headers=H(rtok)).json()
    assert any(o["email"] == "newsupport@platform.sg" and o["role"] == "platform_support" for o in ops)
    assert any(o["email"] == "root@platform.sg" and o["role"] == "super_admin" for o in ops)
    # Bad role rejected.
    assert client.post("/api/v1/platform/operators",
                       json={"email": "z@x.sg", "password": "Password123!", "role": "god"},
                       headers=H(rtok)).status_code == 422


def test_cannot_remove_last_owner(client, db):
    """Revoking the only Owner is blocked even though other (non-owner) operators exist."""
    owner = super_admin(db)
    rtok = staff_token(client, "root@platform.sg")
    # Add a non-owner admin so there are 2 operators but still 1 Owner.
    client.post("/api/v1/platform/operators",
                json={"email": "adm@platform.sg", "password": "Password123!", "role": "platform_admin"},
                headers=H(rtok))
    ops = client.get("/api/v1/platform/operators", headers=H(rtok)).json()
    adm = next(o for o in ops if o["email"] == "adm@platform.sg")
    # Removing the non-owner admin is fine.
    assert client.delete(f"/api/v1/platform/operators/{adm['id']}", headers=H(rtok)).status_code == 204
    # Self-revoke of the Owner is blocked (and it's also the last Owner).
    assert client.delete(f"/api/v1/platform/operators/{owner.id}", headers=H(rtok)).status_code == 403


def test_platform_capabilities_endpoint(client, db):
    super_admin(db)
    _operator(db, "sup@platform.sg", "platform_support")
    owner = client.get("/api/v1/platform/permissions",
                       headers=H(staff_token(client, "root@platform.sg"))).json()
    assert owner["is_owner"] is True and "platform.operators.manage" in owner["permissions"]
    sup = client.get("/api/v1/platform/permissions",
                     headers=H(staff_token(client, "sup@platform.sg"))).json()
    assert sup["is_owner"] is False
    assert set(sup["permissions"]) == {"platform.overview.view", "platform.merchants.view",
                                       "platform.merchant.access"}
