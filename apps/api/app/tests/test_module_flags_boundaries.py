"""Phase 0c/0d — module-adoption flags + boundary indirection (behaviour-neutral seams)."""
from app.services import boundaries, merchant_settings
from app.tests.factories import make_world


def test_module_flags_default_backward_compatible(db):
    w = make_world(db)
    flags = boundaries.module_flags(db, merchant_id=w.merchant_id)
    # the three built modules default ON for every current merchant; wallet is opt-in (OFF)
    assert flags == {"rewards_enabled": True, "qr_ordering_enabled": True, "pos_enabled": True,
                     "wallet_enabled": False}


def test_module_flags_overridable_per_merchant(db):
    w = make_world(db)
    merchant_settings.update_settings(db, merchant_id=w.merchant_id, changes={"pos_enabled": True})
    flags = boundaries.module_flags(db, merchant_id=w.merchant_id)
    assert flags["pos_enabled"] is True
    assert flags["rewards_enabled"] is True  # untouched flags keep their default


def test_boundaries_resolve_to_merchant_today(db):
    """The two boundaries are concepts that equal the merchant today — the seam Phase 1/2 fills."""
    w = make_world(db)
    assert boundaries.loyalty_domain_id(w.merchant_id) == w.merchant_id
