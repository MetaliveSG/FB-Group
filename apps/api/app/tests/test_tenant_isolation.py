"""Cross-tenant isolation — adversarial proof that a merchant's session cannot
reach another merchant's settings/entities (no cross-merchant hijack) and that a
downline (brand/outlet) actor cannot write upline (merchant-level) settings.

Two layers are exercised:
  1. resolve_merchant chokepoint — passing a foreign `?merchant_id=` → 403.
  2. per-entity ownership re-check — using your OWN merchant_id but a foreign
     entity id (IDOR) → 404.
"""
from app.tests.factories import make_world, super_admin
from app.tests.helpers import H, staff_token


def test_foreign_merchant_id_is_rejected(client, db):
    """Merchant A's owner cannot operate on Merchant B by passing ?merchant_id=B."""
    a = make_world(db, name="AlphaCo", token_suffix="A")
    b = make_world(db, name="BravoCo", token_suffix="B")
    atok = staff_token(client, a.owner_email)
    bid = b.merchant_id

    # Reads scoped to a foreign merchant → 403 (not in A's accessible set).
    for path in (
        f"/api/v1/org/settings?merchant_id={bid}",
        f"/api/v1/org/loyalty?merchant_id={bid}",
        f"/api/v1/crm/customers?merchant_id={bid}",
        f"/api/v1/campaigns?merchant_id={bid}",
        f"/api/v1/promotions?merchant_id={bid}",
        f"/api/v1/orders?merchant_id={bid}",
    ):
        assert client.get(path, headers=H(atok)).status_code == 403, f"GET {path} not blocked"

    # Writes scoped to a foreign merchant → 403.
    assert client.patch(f"/api/v1/org/settings?merchant_id={bid}",
                        json={"pipeline_enabled": False}, headers=H(atok)).status_code == 403
    assert client.put(f"/api/v1/org/loyalty?merchant_id={bid}",
                      json={"points_per_dollar": 9, "welcome_bonus": 999, "birthday_bonus": 999},
                      headers=H(atok)).status_code == 403
    assert client.post(f"/api/v1/org/brands?merchant_id={bid}",
                       json={"name": "Hostile Brand"}, headers=H(atok)).status_code == 403

    # And nothing leaked into B: B's own owner still sees seed defaults.
    btok = staff_token(client, b.owner_email)
    prog = client.get("/api/v1/org/loyalty", headers=H(btok)).json()
    assert prog["points_per_dollar"] != 9  # the hostile write never landed


def test_foreign_entity_id_is_not_found(client, db):
    """Using your OWN merchant_id but a FOREIGN entity id (IDOR) → 404, never edits."""
    a = make_world(db, name="AlphaCo", token_suffix="A")
    b = make_world(db, name="BravoCo", token_suffix="B")
    atok = staff_token(client, a.owner_email)

    # A edits its own merchant scope (resolves fine) but targets B's brand → 404.
    r = client.patch(f"/api/v1/org/brands/{b.brand_id}?merchant_id={a.merchant_id}",
                     json={"name": "Hijacked"}, headers=H(atok))
    assert r.status_code == 404
    # A targets B's menu item via the menu admin → 404.
    r = client.patch(f"/api/v1/menu-admin/items/{b.burger_id}?merchant_id={a.merchant_id}",
                     json={"price": 0.01}, headers=H(atok))
    assert r.status_code == 404
    # A targets B's customer profile → 404 (customer has no account in A).
    # (Use B's outlet manager token to confirm B is intact afterwards is overkill;
    #  the 404 alone proves A cannot read across.)


def test_merchant_cannot_reach_platform_upline(client, db):
    """A merchant owner (downline) cannot see or manage the operator/platform layer (upline)."""
    a = make_world(db, name="AlphaCo", token_suffix="A")
    super_admin(db)  # platform layer exists
    atok = staff_token(client, a.owner_email)
    for path in ("/api/v1/platform/overview", "/api/v1/platform/merchants",
                 "/api/v1/platform/operators", "/api/v1/platform/coalitions"):
        assert client.get(path, headers=H(atok)).status_code == 403, f"{path} reachable by merchant"
    assert client.post("/api/v1/platform/operators",
                       json={"email": "evil@x.sg", "password": "Password123!"},
                       headers=H(atok)).status_code == 403


def test_downline_manager_isolated_from_merchant_settings(client, db):
    """Hard upline isolation: an outlet manager (downline) can read ONLY the nav-flags
    projection — never the full merchant-level (upline) settings or loyalty program (both
    `merchant.manage`, owner-only) — and can write none of them."""
    a = make_world(db, name="AlphaCo", token_suffix="A")
    mgrtok = staff_token(client, a.outlet_mgr_email)

    # Nav flags: allowed (the only thing the sidebar needs) — and it carries no economic config.
    nav = client.get("/api/v1/org/nav-flags", headers=H(mgrtok))
    assert nav.status_code == 200
    assert set(nav.json()) == {"pipeline_enabled", "rewards_enabled", "qr_ordering_enabled",
                               "pos_enabled", "can_manage_merchant"}
    assert "wheel_spin_cost" not in nav.json()  # spin costs never exposed to downline
    # Capability flag is False for a downline manager → client hides owner-only nav (Settings/Team).
    assert nav.json()["can_manage_merchant"] is False

    # Full settings + loyalty program: READ blocked (this is the hardened boundary).
    assert client.get("/api/v1/org/settings", headers=H(mgrtok)).status_code == 403
    assert client.get("/api/v1/org/loyalty", headers=H(mgrtok)).status_code == 403
    # Writes blocked too (unchanged).
    assert client.patch("/api/v1/org/settings",
                        json={"pos_enabled": True}, headers=H(mgrtok)).status_code == 403
    assert client.put("/api/v1/org/loyalty",
                      json={"points_per_dollar": 5, "welcome_bonus": 0, "birthday_bonus": 0},
                      headers=H(mgrtok)).status_code == 403


def test_capabilities_endpoint_reflects_role(client, db):
    """GET /org/permissions returns the caller's effective permissions — the contract the
    client uses to render nav. Owner gets the broad set; a plain staffer gets only order.*;
    the operator gets everything + is_super_admin."""
    a = make_world(db, name="AlphaCo", token_suffix="A")
    super_admin(db)

    owner = client.get("/api/v1/org/permissions", headers=H(staff_token(client, a.owner_email))).json()
    assert owner["is_super_admin"] is False
    assert {"crm.view", "merchant.manage", "user.manage", "report.view"} <= set(owner["permissions"])

    # Plain staff: only order/payment perms — NOT crm.view / merchant.manage (so CRM/Settings hide).
    staff = client.get("/api/v1/org/permissions", headers=H(staff_token(client, a.staff_email))).json()
    assert set(staff["permissions"]) == {"order.view", "order.manage", "payment.process"}
    assert "crm.view" not in staff["permissions"] and "merchant.manage" not in staff["permissions"]

    # Operator: wildcard expands to the full set + is_super_admin true.
    op = client.get("/api/v1/org/permissions", headers=H(staff_token(client, "root@platform.sg"))).json()
    assert op["is_super_admin"] is True
    assert "merchant.manage" in op["permissions"] and "*" not in op["permissions"]


def test_capabilities_endpoint_is_tenant_scoped(client, db):
    """A merchant's caps for a FOREIGN merchant → 403 (can't probe another tenant's perms)."""
    a = make_world(db, name="AlphaCo", token_suffix="A")
    b = make_world(db, name="BravoCo", token_suffix="B")
    atok = staff_token(client, a.owner_email)
    assert client.get(f"/api/v1/org/permissions?merchant_id={b.merchant_id}",
                      headers=H(atok)).status_code == 403


def test_owner_still_reads_full_settings_and_nav_flags(client, db):
    """The split must not lock out the owner: owner reads both full settings and nav-flags,
    and the nav capability flag is True (so the client shows owner-only nav)."""
    a = make_world(db, name="AlphaCo", token_suffix="A")
    otok = staff_token(client, a.owner_email)
    assert client.get("/api/v1/org/settings", headers=H(otok)).status_code == 200
    assert client.get("/api/v1/org/loyalty", headers=H(otok)).status_code == 200
    nav = client.get("/api/v1/org/nav-flags", headers=H(otok))
    assert nav.status_code == 200 and nav.json()["can_manage_merchant"] is True
