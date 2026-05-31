"""Phase 1a — the org spine (member-tree-map): sync + path-prefix queries.

The spine mirrors the typed tables (Merchant→Brand→Outlet→Menu); it must build correct
parent/depth/path/flags, stay idempotent, and answer subtree queries without recursion.
"""
from app.models.org import OrgNode
from app.services import catalog as catalog_service
from app.services import org_tree
from app.tests.factories import make_world


def test_sync_builds_one_node_per_entity_with_correct_shape(db):
    w = make_world(db)  # 1 merchant, 1 brand, 1 outlet, 1 menu(stall)
    counts = org_tree.sync_org_tree(db)
    assert counts == {"merchant": 1, "brand": 1, "outlet": 1, "stall": 1}

    merchant = org_tree.node_for(db, w.merchant_id)
    brand = org_tree.node_for(db, w.brand_id)
    outlet = org_tree.node_for(db, w.outlet_id)
    stall = org_tree.node_for(db, w.menu.id)

    # merchant = root, its own loyalty domain + settlement account
    assert merchant.parent_id is None and merchant.depth == 0
    assert merchant.is_loyalty_domain and merchant.is_settlement_boundary
    assert merchant.loyalty_domain_id == w.merchant_id and not merchant.sells

    # parent chain + depth
    assert brand.parent_id == w.merchant_id and brand.depth == 1
    assert outlet.parent_id == w.brand_id and outlet.depth == 2
    assert stall.parent_id == w.outlet_id and stall.depth == 3

    # the stall is the only sellable node; path is the full lineage
    assert stall.sells is True
    assert stall.path == ".".join([w.merchant_id, w.brand_id, w.outlet_id, w.menu.id])
    # boundaries inherited from the merchant
    assert stall.loyalty_domain_id == w.merchant_id and stall.settlement_account_id == w.merchant_id


def test_sellable_under_returns_subtree_stalls(db):
    w = make_world(db)
    org_tree.sync_org_tree(db)
    merchant = org_tree.node_for(db, w.merchant_id)

    sellable = org_tree.sellable_under(db, merchant)
    assert [n.id for n in sellable] == [w.menu.id]  # the one stall under the merchant

    # querying from the outlet yields the same stall (path-prefix, any anchor depth)
    outlet = org_tree.node_for(db, w.outlet_id)
    assert [n.id for n in org_tree.sellable_under(db, outlet)] == [w.menu.id]


def test_subtree_spans_all_descendants(db):
    w = make_world(db)
    org_tree.sync_org_tree(db)
    merchant = org_tree.node_for(db, w.merchant_id)
    ids = {n.id for n in org_tree.subtree(db, merchant)}
    assert ids == {w.merchant_id, w.brand_id, w.outlet_id, w.menu.id}


def test_sync_is_idempotent(db):
    w = make_world(db)
    org_tree.sync_org_tree(db)
    first = db.query(OrgNode).count()
    org_tree.sync_org_tree(db)  # re-run
    second = db.query(OrgNode).count()
    assert first == second == 4


def test_spine_backed_stall_resolution_matches_profile_query(db):
    """Phase 1b: list_outlet_stalls (spine) returns the same stalls as list_outlet_menus."""
    w = make_world(db)
    org_tree.sync_org_tree(db)
    via_spine = [m.id for m in catalog_service.list_outlet_stalls(db, w.outlet_id)]
    via_profile = [m.id for m in catalog_service.list_outlet_menus(db, w.outlet_id)]
    assert via_spine == via_profile == [w.menu.id]


def test_stall_resolution_falls_back_when_spine_unsynced(db):
    """If the outlet has no spine node yet, resolution falls back to the profile query."""
    w = make_world(db)  # NOT synced
    assert org_tree.node_for(db, w.outlet_id) is None
    via_spine = [m.id for m in catalog_service.list_outlet_stalls(db, w.outlet_id)]
    assert via_spine == [w.menu.id]  # fallback path still returns the stall


def test_tenant_isolation_two_worlds_dont_cross(db):
    a = make_world(db, name="Alpha", token_suffix="A")
    b = make_world(db, name="Beta", token_suffix="B")
    org_tree.sync_org_tree(db)

    a_merchant = org_tree.node_for(db, a.merchant_id)
    # Alpha's subtree must contain only Alpha's nodes — never Beta's.
    a_ids = {n.id for n in org_tree.subtree(db, a_merchant)}
    assert b.merchant_id not in a_ids and b.menu.id not in a_ids
    assert a_ids == {a.merchant_id, a.brand_id, a.outlet_id, a.menu.id}
