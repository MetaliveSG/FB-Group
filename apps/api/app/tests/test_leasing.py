"""PROOF: foodcourt vs coffeeshop on ONE associative `leases` edge (docs/architecture-org-tree.md §10).

Same wiring for both — an independent stall is its own forest root and only touches a venue through
a `leases` row. The SOLE difference is `rent_type`:
  * FIXED (coffeeshop) → the landlord (m1) is BLIND to the tenant's sales; flat rent.
  * GTO   (foodcourt)  → the landlord READS the tenant's turnover (to bill the %), but cannot manage.

BreadTalk (m1) owns two venues: BT Coffeeshop @ AMK (Lim's + Ah Huat on FIXED) and the Food Republic
foodcourt (Mr Bean on GTO). Asserts isolation falls out for FIXED, the GTO read-grant is narrow, the
shared-QR resolver unions house + leased stalls, and each stall settles to its own tenant.
"""
from sqlalchemy import select

from app.auth.access import resolve_scope
from app.models.identity import User
from app.models.org import OrgNode
from app.seed_breadtalk import build_breadtalk
from app.services import leasing, org_tree
from app.services.leasing import active_lease_for, storefronts_at_venue
from app.tests.helpers import staff_token


def _scope(db, email):
    return resolve_scope(db, db.scalar(select(User).where(User.email == email)))


def _auth(client, email):
    return {"Authorization": f"Bearer {staff_token(client, email)}"}


def test_rent_type_marks_foodcourt_vs_coffeeshop(client, db):
    build_breadtalk(db)
    assert active_lease_for(db, "o_lim").rent_type == "FIXED"        # coffeeshop tenant
    assert active_lease_for(db, "o_ah").rent_type == "FIXED"
    assert active_lease_for(db, "o_mb").rent_type == "GTO"           # foodcourt tenant
    assert str(active_lease_for(db, "o_mb").rate) in ("18.00", "18.0")
    # House stalls have NO lease — same owner as the venue.
    assert active_lease_for(db, "o_cs_kopi") is None
    assert active_lease_for(db, "s_fr_chic") is None


def test_fixed_rent_landlord_is_blind(client, db):
    build_breadtalk(db)
    gm = _scope(db, "owner.m1@breadtalk.sg")                         # Manager @ m1 — owns both venues
    # The coffeeshop's fixed-rent tenants are wholly invisible to the landlord.
    assert "t_lim" not in gm.accessible_merchant_ids
    assert "t_ah" not in gm.accessible_merchant_ids
    assert not gm.can("report.view", "t_lim")


def test_gto_landlord_reads_turnover_only(client, db):
    build_breadtalk(db)
    gm = _scope(db, "owner.m1@breadtalk.sg")
    assert "t_mb" in gm.accessible_merchant_ids                      # GTO → visible to landlord
    assert gm.can("report.view", "t_mb")                            # turnover read
    assert gm.can_view_outlet("t_mb", "o_mb")
    assert not gm.can("order.manage", "t_mb")                       # but never manage
    assert not gm.can("org.manage", "t_mb")
    assert not gm.can("customer.view", "t_mb")                      # no PII / CRM


def test_independent_tenant_sees_only_itself(client, db):
    build_breadtalk(db)
    for email, mid, sf in [("owner.lim@limschickenrice.sg", "t_lim", "o_lim"),
                           ("owner.ah@ahhuat.sg", "t_ah", "o_ah"),
                           ("owner.mb@mrbean.sg", "t_mb", "o_mb")]:
        s = _scope(db, email)
        assert s.accessible_merchant_ids == {mid}                   # its own tenant only
        assert s.can("order.manage", mid) and s.can_view_outlet(mid, sf)
        assert "m1" not in s.accessible_merchant_ids               # never the landlord's books


def test_shared_qr_resolver_unions_house_and_leased(client, db):
    build_breadtalk(db)
    # Coffeeshop: 2 BT house stalls + 2 FIXED-leased independents = one shared QR over all four.
    cs = {n.id for n in storefronts_at_venue(db, db.get(OrgNode, "bt_cs_amk"))}
    assert cs == {"o_cs_kopi", "o_cs_toast", "o_lim", "o_ah"}
    # Foodcourt: 3 house stalls + 1 GTO-leased independent.
    fr = {n.id for n in storefronts_at_venue(db, db.get(OrgNode, "o_fr_vivo"))}
    assert fr == {"s_fr_chic", "s_fr_laksa", "s_fr_west", "o_mb"}


def test_each_stall_settles_to_its_own_tenant(client, db):
    build_breadtalk(db)
    # Net money always settles to the stall's own boundary — never the landlord's, regardless of rent.
    assert db.get(OrgNode, "o_lim").settlement_account_id == "t_lim"
    assert db.get(OrgNode, "o_mb").settlement_account_id == "t_mb"
    assert db.get(OrgNode, "o_cs_kopi").settlement_account_id == "m1"   # house stall → landlord's own


def test_gto_grant_does_not_leak_across_venues(client, db):
    build_breadtalk(db)
    # The Toast Box manager (a branch with NO venue/lease beneath it) gains no turnover grants at all.
    tb = _scope(db, "mgr.toastbox@breadtalk.sg")
    assert tb.accessible_merchant_ids == {"m1"}
    assert "t_mb" not in tb.accessible_merchant_ids
    # And the resolver helper finds no GTO grants under that branch.
    assert leasing.gto_turnover_grants(db, db.get(OrgNode, "b_tb")) == []


# --- Lease management endpoints (the venue operator adjusts rent_type from the drawer) ---------
def test_list_venue_leases(client, db):
    build_breadtalk(db)
    r = client.get("/api/v1/org/nodes/bt_cs_amk/leases", headers=_auth(client, "ceo@breadtalk.sg"))
    assert r.status_code == 200
    by_tenant = {ls["tenant_node_id"]: ls for ls in r.json()}
    assert by_tenant.keys() == {"o_lim", "o_ah"}
    assert by_tenant["o_lim"]["rent_type"] == "FIXED" and by_tenant["o_lim"]["tenant_name"] == "Lim's Chicken Rice"


def test_create_update_delete_lease(client, db):
    build_breadtalk(db)
    ceo = _auth(client, "ceo@breadtalk.sg")
    # Lease an existing unleased storefront (Din Tai Fung's outlet) into the coffeeshop on GTO.
    created = client.post("/api/v1/org/nodes/bt_cs_amk/leases", headers=ceo,
                          json={"tenant_node_id": "o_dtf_para", "rent_type": "GTO", "rate": "15.00"})
    assert created.status_code == 201 and created.json()["rent_type"] == "GTO"
    lid = created.json()["id"]
    # Flip GTO → FIXED with a flat rent (the one switch that turns foodcourt into coffeeshop).
    upd = client.patch(f"/api/v1/org/nodes/bt_cs_amk/leases/{lid}", headers=ceo,
                       json={"rent_type": "FIXED", "rate": "1800.00"})
    assert upd.status_code == 200 and upd.json()["rent_type"] == "FIXED" and str(upd.json()["rate"]) in ("1800.00", "1800.0")
    # Remove it.
    assert client.delete(f"/api/v1/org/nodes/bt_cs_amk/leases/{lid}", headers=ceo).status_code == 204
    assert {ls["tenant_node_id"] for ls in client.get("/api/v1/org/nodes/bt_cs_amk/leases", headers=ceo).json()} == {"o_lim", "o_ah"}


def test_gto_lease_grants_landlord_turnover_after_create(client, db):
    build_breadtalk(db)
    ceo = _auth(client, "ceo@breadtalk.sg")
    client.post("/api/v1/org/nodes/bt_cs_amk/leases", headers=ceo,
                json={"tenant_node_id": "o_dtf_para", "rent_type": "GTO", "rate": "15.00"})
    # The landlord (m1, owns the coffeeshop) now reads m2's leased stall turnover — read-only.
    gm = _scope(db, "owner.m1@breadtalk.sg")
    assert gm.can("report.view", "m2") and gm.can_view_outlet("m2", "o_dtf_para")
    assert not gm.can("order.manage", "m2")


def test_lease_validation_and_gating(client, db):
    build_breadtalk(db)
    ceo = _auth(client, "ceo@breadtalk.sg")
    # A house stall (owned by the venue) needs no lease → rejected.
    assert client.post("/api/v1/org/nodes/bt_cs_amk/leases", headers=ceo,
                       json={"tenant_node_id": "o_cs_kopi", "rent_type": "FIXED", "rate": "100"}).status_code == 400
    # Already-leased stall → conflict.
    assert client.post("/api/v1/org/nodes/bt_cs_amk/leases", headers=ceo,
                       json={"tenant_node_id": "o_lim", "rent_type": "FIXED", "rate": "100"}).status_code == 409
    # A non-manager of the venue cannot read/grant leases there.
    tb = _auth(client, "mgr.toastbox@breadtalk.sg")
    assert client.get("/api/v1/org/nodes/bt_cs_amk/leases", headers=tb).status_code == 403
    assert client.post("/api/v1/org/nodes/bt_cs_amk/leases", headers=tb,
                       json={"tenant_node_id": "o_dtf_para", "rent_type": "GTO", "rate": "10"}).status_code == 403


# --- The QR SCAN uses the SAME resolver: a leased-in stall appears at the venue ----------------
def test_qr_scan_unifies_house_and_leased_stalls(client, db):
    """One resolver for every venue: scanning a venue's QR lists its own stalls PLUS stalls leased
    in from another owner — and a leased stall's menu is reachable, while a foreign menu is not."""
    from app.tests.factories import make_world

    venue = make_world(db, name="Bedok Coffeeshop", token_suffix="VEN")   # the floor (has its own stall)
    tenant = make_world(db, name="Lim's Stall", token_suffix="LIM")        # an independent stall
    outsider = make_world(db, name="Somewhere Else", token_suffix="OUT")   # NOT leased — stays blocked
    org_tree.sync_org_tree(db)                                             # build the spine for all three
    db.commit()

    # Before leasing: the venue scan shows ONLY its own stall.
    before = client.get(f"/api/v1/qr/{venue.qr_token}").json()
    assert {s["menu_id"] for s in before["stalls"]} == {venue.menu.id}

    # Lease the tenant's stall into the venue (flat rent).
    leasing.create_lease(db, venue=db.get(OrgNode, venue.outlet_id),
                         tenant_node_id=tenant.menu.id, rent_type="FIXED", rate=2000)
    db.commit()

    # After leasing: the SAME scan now lists both stalls (house + leased) — one resolver.
    after = client.get(f"/api/v1/qr/{venue.qr_token}").json()
    assert {s["menu_id"] for s in after["stalls"]} == {venue.menu.id, tenant.menu.id}
    assert after["is_foodcourt"] is True

    # The leased stall's menu is reachable through the venue's QR…
    assert client.get(f"/api/v1/qr/{venue.qr_token}/menu/{tenant.menu.id}").status_code == 200
    # …but an outsider's menu (not leased here) is still blocked.
    assert client.get(f"/api/v1/qr/{venue.qr_token}/menu/{outsider.menu.id}").status_code == 404


def test_bt_coffeeshop_is_scannable_with_four_stalls(client, db):
    """The seeded BT Coffeeshop is a real scannable venue: one shared QR → 4 stalls (2 house +
    2 leased), and a leased stall's menu is reachable through that QR."""
    build_breadtalk(db)
    r = client.get("/api/v1/qr/bt-coffeeshop-01")
    assert r.status_code == 200
    body = r.json()
    assert body["is_foodcourt"] is True
    assert {s["stall_name"] for s in body["stalls"]} == {
        "Kopi & Drinks", "Toast Box Toast", "Lim's Chicken Rice", "Ah Huat Wok Hei"}
    # A leased stall's menu (lives under its own merchant) is reachable via the shared QR.
    lim = next(s for s in body["stalls"] if s["stall_name"] == "Lim's Chicken Rice")
    menu = client.get(f"/api/v1/qr/bt-coffeeshop-01/menu/{lim['menu_id']}")
    assert menu.status_code == 200 and menu.json()["categories"]
    # The leased stall's spine ownership is UNCHANGED — still its own tenant, never re-parented.
    assert db.get(OrgNode, "o_lim").settlement_account_id == "t_lim"


def test_chain_qr_group_browse_lists_direct_stalls(client, db):
    """A node's QR Menu lists its DIRECT sellable children + stalls leased DIRECTLY into it — never
    storefronts nested under a sub-chain (uniform rule, every node). The top group (only sub-chains
    beneath it) has none; the coffeeshop venue lists its 2 house stalls + 2 leased-in independents."""
    build_breadtalk(db)
    # Top group: every child is a sub-chain/venue → NO direct storefronts (nested ones don't show).
    rg = client.get("/api/v1/qr/node/btg")
    assert rg.status_code == 200 and rg.json()["is_group"] is True
    assert rg.json()["stalls"] == []
    # Coffeeshop venue: direct house stalls + stalls leased into THIS venue (not nested elsewhere).
    rv = client.get("/api/v1/qr/node/bt_cs_amk")
    assert rv.status_code == 200
    assert {s["stall_name"] for s in rv.json()["stalls"]} == {
        "Kopi & Drinks", "Toast Box Toast", "Lim's Chicken Rice", "Ah Huat Wok Hei"}
    # A stall's menu is reachable via the node browse; an out-of-scope id is blocked.
    lim = next(s for s in rv.json()["stalls"] if s["stall_name"] == "Lim's Chicken Rice")
    assert client.get(f"/api/v1/qr/node/bt_cs_amk/menu/{lim['menu_id']}").status_code == 200
    assert client.get("/api/v1/qr/node/bt_cs_amk/menu/o_bt_ion").status_code == 404   # not at venue → blocked
