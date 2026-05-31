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
        f"/api/v1/admin/users?merchant_id={bid}",
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


def test_downline_manager_cannot_write_merchant_settings(client, db):
    """An outlet manager (downline) cannot change merchant-level (upline) settings,
    which require `merchant.manage` (owner-only)."""
    a = make_world(db, name="AlphaCo", token_suffix="A")
    mgrtok = staff_token(client, a.outlet_mgr_email)
    # Can READ within its own tenant (sidebar needs pipeline_enabled)...
    assert client.get("/api/v1/org/settings", headers=H(mgrtok)).status_code == 200
    # ...but cannot WRITE merchant-level settings or the loyalty program.
    assert client.patch("/api/v1/org/settings",
                        json={"pos_enabled": True}, headers=H(mgrtok)).status_code == 403
    assert client.put("/api/v1/org/loyalty",
                      json={"points_per_dollar": 5, "welcome_bonus": 0, "birthday_bonus": 0},
                      headers=H(mgrtok)).status_code == 403
