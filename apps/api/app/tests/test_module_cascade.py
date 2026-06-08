"""Phase A1 — per-node module flags resolve via the org-tree cascade (nearest explicit ancestor wins,
NULL = inherit, fallback to Merchant.settings)."""
from app.models.org import OrgNode
from app.seed_breadtalk import build_breadtalk
from app.services import boundaries


def test_resolve_modules_cascade(db):
    build_breadtalk(db)
    sf = db.get(OrgNode, "o_bt_ion")        # a storefront under tenant m1
    tenant = db.get(OrgNode, "m1")
    sib = db.get(OrgNode, "o_tb_tamp")      # another storefront under m1
    assert sf is not None and tenant is not None and "m1" in sf.path.split(".")

    # Nothing set anywhere → legacy defaults (rewards/qr on, pos off).
    r = boundaries.resolve_modules(db, node=sf, merchant_id="m1")
    assert r == {"rewards_enabled": True, "qr_ordering_enabled": True, "pos_enabled": False}

    # Turn POS on at the tenant → every storefront in the subtree inherits it.
    tenant.mod_pos = True
    db.flush()
    assert boundaries.resolve_modules(db, node=sf, merchant_id="m1")["pos_enabled"] is True
    assert boundaries.resolve_modules(db, node=sib, merchant_id="m1")["pos_enabled"] is True

    # A storefront overrides POS off → only it; the sibling still inherits the tenant's ON.
    sf.mod_pos = False
    db.flush()
    assert boundaries.resolve_modules(db, node=sf, merchant_id="m1")["pos_enabled"] is False
    assert boundaries.resolve_modules(db, node=sib, merchant_id="m1")["pos_enabled"] is True

    # Other flags untouched by the pos override.
    out = boundaries.resolve_modules(db, node=sf, merchant_id="m1")
    assert out["rewards_enabled"] is True and out["qr_ordering_enabled"] is True

    # node=None → pure legacy fallback.
    assert boundaries.resolve_modules(db, node=None, merchant_id="m1") == {
        "rewards_enabled": True, "qr_ordering_enabled": True, "pos_enabled": False}
