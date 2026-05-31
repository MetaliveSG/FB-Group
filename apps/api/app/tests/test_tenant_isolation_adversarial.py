"""Adversarial cross-tenant probes — complements test_tenant_isolation.py.

Covers the angles a builder's happy-path isolation tests usually miss:
  - POSITIVE CONTROL: the operator (super admin) CAN cross merchants (200) — proves
    the per-tenant 403s are scope-driven, not a blanket-deny bug masquerading as security.
  - WRONG ACTOR: a customer JWT replayed on staff/operator surfaces → 403.
  - SYMMETRY: isolation holds B→A, not only A→B.
  - OPERATOR GUARDS: garbage/foreign ids on the new /platform/* mutators → 404, never
    a silent success that could nuke an unrelated row.
"""
from app.tests.factories import make_world, super_admin
from app.tests.helpers import H, register_customer, staff_token


def _ctok(client, email):
    return register_customer(client, email=email)["access_token"]


def test_operator_can_cross_merchants_positive_control(client, db):
    """The 403s elsewhere must be SCOPE-based: a super admin passing any merchant_id
    gets 200. If this failed, the merchant 403s would be a deny-all bug, not isolation."""
    a = make_world(db, name="AlphaCo", token_suffix="A")
    b = make_world(db, name="BravoCo", token_suffix="B")
    super_admin(db)
    rtok = staff_token(client, "root@platform.sg")
    # Operator reads BOTH merchants' scoped data via ?merchant_id=.
    for mid in (a.merchant_id, b.merchant_id):
        assert client.get(f"/api/v1/org/settings?merchant_id={mid}", headers=H(rtok)).status_code == 200
        assert client.get(f"/api/v1/crm/customers?merchant_id={mid}", headers=H(rtok)).status_code == 200
    # Operator can manage either merchant (the upline-over-downline direction).
    assert client.put(f"/api/v1/platform/merchants/{b.merchant_id}",
                      json={"name": "BravoCo Renamed"}, headers=H(rtok)).status_code == 200


def test_customer_jwt_rejected_on_staff_and_operator_surfaces(client, db):
    """A customer access token must not be replayable on any back-office route."""
    make_world(db, name="AlphaCo", token_suffix="A")
    super_admin(db)
    ctok = _ctok(client, "diner-adv@b.sg")
    for path in (
        "/api/v1/org/settings",
        "/api/v1/crm/customers",
        "/api/v1/admin/users",
        "/api/v1/orders",
        "/api/v1/platform/overview",
        "/api/v1/platform/operators",
    ):
        sc = client.get(path, headers=H(ctok)).status_code
        assert sc == 403, f"customer token reached {path} (status {sc})"


def test_isolation_is_symmetric(client, db):
    """B's owner is just as walled-off from A as A is from B."""
    a = make_world(db, name="AlphaCo", token_suffix="A")
    b = make_world(db, name="BravoCo", token_suffix="B")
    btok = staff_token(client, b.owner_email)
    assert client.get(f"/api/v1/org/settings?merchant_id={a.merchant_id}", headers=H(btok)).status_code == 403
    assert client.get(f"/api/v1/crm/customers?merchant_id={a.merchant_id}", headers=H(btok)).status_code == 403
    assert client.put(f"/api/v1/org/loyalty?merchant_id={a.merchant_id}",
                      json={"points_per_dollar": 7, "welcome_bonus": 0, "birthday_bonus": 0},
                      headers=H(btok)).status_code == 403


def test_operator_mutators_guard_foreign_and_garbage_ids(client, db):
    """New /platform/* mutators must 404 on unknown ids — never silently touch a row."""
    a = make_world(db, name="AlphaCo", token_suffix="A")
    super_admin(db)
    rtok = staff_token(client, "root@platform.sg")

    # Unknown merchant id → 404 (not a silent 200).
    assert client.put("/api/v1/platform/merchants/deadbeef",
                      json={"name": "ghost"}, headers=H(rtok)).status_code == 404
    # Revoking a NON-operator user id (e.g. a merchant owner) → 404; must not delete
    # the merchant-owner's assignment via the operator endpoint.
    assert client.delete(f"/api/v1/platform/operators/{a.owner.id}",
                         headers=H(rtok)).status_code == 404
    # Coalition member ops on an unknown coalition → 404.
    assert client.post("/api/v1/platform/coalitions/nope/members",
                       json={"merchant_id": a.merchant_id}, headers=H(rtok)).status_code == 404
    # Unknown module flag is rejected (can't smuggle arbitrary settings keys).
    assert client.put(f"/api/v1/platform/merchants/{a.merchant_id}",
                      json={"module_flags": {"is_admin": True}}, headers=H(rtok)).status_code == 400

    # The merchant owner is still a working owner after the failed revoke (assignment intact).
    assert client.get("/api/v1/crm/customers", headers=H(staff_token(client, a.owner_email))).status_code == 200
