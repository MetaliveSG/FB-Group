"""BreadTalk Group — a real-shape **Chain/Storefront** member-tree, used to PROVE the unlimited
member-tree + node-scoped RBAC cascade.

The member tree has TWO node kinds (the engine keys off the `sells` flag, not the label):
  * **Chain** — structural; nests Chain/Storefront children (unless it *stops the chain*).
  * **Storefront** — the only node that SELLS / has a menu; a hard leaf.

Two **Chain** nodes are tenants (settlement boundaries → own GST/payout → typed Merchant rows →
operator directory): BreadTalk (F&B) Pte Ltd and Din Tai Fung SG Pte Ltd. The top Chain
(BreadTalk Group) carries the **loyalty domain** (coins free across the group).

    Chain  BreadTalk Group                         (btg, loyalty domain)
     ├ Chain  BreadTalk (F&B) Pte Ltd               (m1, TENANT/settlement boundary)
     │  ├ Chain  BreadTalk Bakery
     │  │   ├ Storefront  BreadTalk @ ION
     │  │   └ Storefront  BreadTalk @ VivoCity
     │  ├ Chain  Toast Box
     │  │   └ Storefront  Toast Box @ Tampines
     │  ├ Chain  Food Republic
     │  │   └ Chain  Food Republic @ VivoCity   (chain_stopped → storefronts only) ── VENUE
     │  │       ├ Storefront  Chicken Rice          ┐ house stalls (m1's money)
     │  │       ├ Storefront  Laksa                 │
     │  │       ├ Storefront  Western               ┘
     │  │       └╌╌[GTO 18%]╌► Mr Bean Soya  ‡      leased-in (own tenant t_mb; m1 reads turnover)
     │  └ Chain  BT Coffeeshop @ AMK   (chain_stopped) ── VENUE
     │      ├ Storefront  Kopi & Drinks (BT)        ┐ house stalls (m1's money)
     │      ├ Storefront  Toast Box Toast (BT)      ┘
     │      ├╌╌[FIXED $2,500]╌► Lim's Chicken Rice ‡  leased-in (own tenant t_lim; m1 sees NOTHING)
     │      └╌╌[FIXED $3,200]╌► Ah Huat Wok Hei    ‡  leased-in (own tenant t_ah;  m1 sees NOTHING)
     └ Chain  Din Tai Fung SG Pte Ltd              (m2, TENANT)
        └ Chain  Din Tai Fung
            └ Storefront  Din Tai Fung @ Paragon

  Independent tenants (own forest roots, own settlement boundaries; ‡ above = where they trade):
    Chain t_lim → o_lim   ·   Chain t_ah → o_ah   ·   Chain t_mb → o_mb

The `╌╌►` edges are `leases` rows, NOT parent_id — a leased stall is its OWN tenant; it only shares
the venue's QR. `rent_type` (FIXED|GTO) is the sole switch: FIXED → landlord blind + flat rent;
GTO → landlord reads turnover + a % flows up. House stalls have NO lease (same owner as the venue).

Authority = tree position. A **Manager** high on a Chain commands its whole branch; at a Storefront
it's the storefront manager. **Cashier/Staff** sit at a Storefront. **Finance** is read-only across
a subtree. Idempotent (upsert by stable id). Call `build_breadtalk(db)`; used by the proof test +
the live demo.
"""
from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from decimal import Decimal

from app.auth.permissions import seed_rbac
from app.core.security import hash_password
from app.models.enums import RoleName, ScopeType
from app.models.identity import User, UserRoleAssignment
from app.models.leases import Lease
from app.models.org import PATH_SEP, OrgNode
from app.models.tenancy import Merchant

PW = "Password123!"
CHAIN, STOREFRONT = "CHAIN", "STOREFRONT"

# (id, parent_id, kind, label) — parent-before-child so paths/depths derive in one pass.
NODES = [
    ("btg", None, CHAIN, "BreadTalk Group"),
    ("m1", "btg", CHAIN, "BreadTalk (F&B) Pte Ltd"),
    ("m2", "btg", CHAIN, "Din Tai Fung SG Pte Ltd"),
    ("b_bt", "m1", CHAIN, "BreadTalk Bakery"),
    ("b_tb", "m1", CHAIN, "Toast Box"),
    ("b_fr", "m1", CHAIN, "Food Republic"),
    ("b_dtf", "m2", CHAIN, "Din Tai Fung"),
    ("o_bt_ion", "b_bt", STOREFRONT, "BreadTalk @ ION"),
    ("o_bt_vivo", "b_bt", STOREFRONT, "BreadTalk @ VivoCity"),
    ("o_tb_tamp", "b_tb", STOREFRONT, "Toast Box @ Tampines"),
    ("o_fr_vivo", "b_fr", CHAIN, "Food Republic @ VivoCity"),      # foodcourt location (chain-stopped)
    ("s_fr_chic", "o_fr_vivo", STOREFRONT, "Chicken Rice (Food Republic)"),
    ("s_fr_laksa", "o_fr_vivo", STOREFRONT, "Laksa (Food Republic)"),
    ("s_fr_west", "o_fr_vivo", STOREFRONT, "Western (Food Republic)"),
    ("o_dtf_para", "b_dtf", STOREFRONT, "Din Tai Fung @ Paragon"),
    # BT Coffeeshop @ AMK — a VENUE owned by m1 (a fixed-rent kopitiam): m1 runs the drinks/toast
    # stalls itself (house stalls, under m1); independent hawkers lease the rest (see LEASES, below).
    ("bt_cs_amk", "m1", CHAIN, "BT Coffeeshop @ AMK"),             # venue (chain-stopped → stalls only)
    ("o_cs_kopi", "bt_cs_amk", STOREFRONT, "Kopi & Drinks (BT)"),  # house stall — m1's money
    ("o_cs_toast", "bt_cs_amk", STOREFRONT, "Toast Box Toast (BT)"),  # house stall — m1's money
    # Independent tenants — their OWN forest roots (own settlement boundary). They are NOT under m1;
    # they only touch a venue through a Lease (FIXED → m1 blind; GTO → m1 reads turnover).
    ("t_lim", None, CHAIN, "Lim's Chicken Rice Pte Ltd"),          # → FIXED lease into BT Coffeeshop
    ("o_lim", "t_lim", STOREFRONT, "Lim's Chicken Rice"),
    ("t_ah", None, CHAIN, "Ah Huat Wok Hei Pte Ltd"),             # → FIXED lease into BT Coffeeshop
    ("o_ah", "t_ah", STOREFRONT, "Ah Huat Wok Hei"),
    ("t_mb", None, CHAIN, "Mr Bean SG Pte Ltd"),                  # → GTO lease into Food Republic
    ("o_mb", "t_mb", STOREFRONT, "Mr Bean Soya"),
]

SETTLEMENT_BOUNDARIES = {"m1", "m2", "t_lim", "t_ah", "t_mb"}   # tenants — own GST/payout, directory
LOYALTY_DOMAINS = {"btg"}             # group-wide coin ring (independent tenants are their own ring)
CHAIN_STOPPED = {"o_fr_vivo", "bt_cs_amk"}   # under here, only Storefronts may be added

# Lease edges (venue↔stall). rent_type is the ONLY thing telling foodcourt (GTO) from coffeeshop
# (FIXED) apart. House stalls (o_cs_kopi/o_cs_toast, s_fr_*) have NO lease — same owner as the venue.
# (id, venue_id, tenant_storefront_id, rent_type, rate)  — rate: FIXED $/mo · GTO percent.
LEASES = [
    ("lease_lim", "bt_cs_amk", "o_lim", "FIXED", Decimal("2500.00")),   # coffeeshop: m1 sees nothing
    ("lease_ah", "bt_cs_amk", "o_ah", "FIXED", Decimal("3200.00")),     # coffeeshop: m1 sees nothing
    ("lease_mb", "o_fr_vivo", "o_mb", "GTO", Decimal("18.00")),         # foodcourt: m1 reads turnover, 18%
]

# (email, full_name, role, node_id) — authority = where they sit on the tree.
ACCOUNTS = [
    ("ceo@breadtalk.sg", "Group CEO", RoleName.MANAGER.value, "btg"),            # commands the whole group
    ("cfo@breadtalk.sg", "Group CFO", RoleName.FINANCE.value, "btg"),            # read-only finance, group-wide
    ("owner.m1@breadtalk.sg", "BreadTalk Pte Ltd GM", RoleName.MANAGER.value, "m1"),   # one tenant
    ("mgr.toastbox@breadtalk.sg", "Toast Box Manager", RoleName.MANAGER.value, "b_tb"),
    ("mgr.foodrepublic@breadtalk.sg", "Food Republic Manager", RoleName.MANAGER.value, "b_fr"),
    ("mgr.ion@breadtalk.sg", "BreadTalk ION Storefront Manager", RoleName.MANAGER.value, "o_bt_ion"),
    ("cashier.ion@breadtalk.sg", "BreadTalk ION Cashier", RoleName.CASHIER.value, "o_bt_ion"),
    ("staff.chicken@breadtalk.sg", "Chicken Rice Staff", RoleName.STAFF.value, "s_fr_chic"),
    ("cashier.tampines@breadtalk.sg", "Toast Box Tampines Cashier", RoleName.CASHIER.value, "o_tb_tamp"),
    ("mgr.dtf@breadtalk.sg", "Din Tai Fung Manager", RoleName.MANAGER.value, "b_dtf"),
    # Independent hawkers — each commands ONLY its own stall (proves the landlord can't see them).
    ("owner.lim@limschickenrice.sg", "Lim's Owner", RoleName.MANAGER.value, "t_lim"),
    ("owner.ah@ahhuat.sg", "Ah Huat Owner", RoleName.MANAGER.value, "t_ah"),
    ("owner.mb@mrbean.sg", "Mr Bean Owner", RoleName.MANAGER.value, "t_mb"),
]


def _cs_menu(db: Session, *, menu_id: str, merchant_id: str, outlet_id: str, stall_name: str,
            cuisine: str, logo: str, sort_order: int, spec: dict) -> None:
    """One stall = a branded Menu (id == its spine Storefront node id) + categories/items.
    Idempotent by menu_id. The id MUST equal the org-node id so the venue resolver
    (`storefronts_at_venue` → nodes) maps back to this Menu."""
    from app.models.catalog import Menu, MenuCategory, MenuItem

    if db.get(Menu, menu_id) is not None:
        return
    menu = Menu(id=menu_id, merchant_id=merchant_id, outlet_id=outlet_id, name=stall_name,
                stall_name=stall_name, cuisine=cuisine, logo=logo, sort_order=sort_order, is_open=True)
    db.add(menu)
    db.flush()
    for ci, (cat_name, items) in enumerate(spec.items()):
        cat = MenuCategory(menu_id=menu.id, name=cat_name, sort_order=ci)
        db.add(cat)
        db.flush()
        for ii, (iname, price) in enumerate(items):
            db.add(MenuItem(category_id=cat.id, name=iname, description=iname,
                            price=Decimal(str(price)), is_available=True, sort_order=ii))
    db.flush()


def _build_coffeeshop_orderable(db: Session) -> None:
    """Make BT Coffeeshop @ AMK a real *scannable* venue (token `bt-coffeeshop-01`) with all four
    stalls orderable. The venue + its HOUSE stalls (Kopi, Toast) are typed under m1; the LEASED
    stalls (Lim's, Ah Huat) get menus under THEIR OWN merchants/outlets, so the spine keeps them
    under their own tenants and the FIXED-rent privacy can never be broken by a re-parent. The
    leases (already seeded) bridge them to the venue; the QR resolver unions house ∪ leased.
    Idempotent (guarded by the QR token). Menu ids == their spine Storefront node ids."""
    from app.models.catalog import Menu
    from app.models.tenancy import Brand, DiningTable, Outlet, QRCode

    # Each piece below is guarded by its own id/token (insert-if-absent), so adding a new stall to
    # this list later reaches an already-seeded DB on the next run — no blanket early-return.

    # Venue: typed Brand + Outlet (id == spine node `bt_cs_amk`) under m1, + a table + the shared QR.
    if db.get(Brand, "cb_bt_cs") is None:
        db.add(Brand(id="cb_bt_cs", merchant_id="m1", name="BT Coffeeshops"))
        db.flush()
    if db.get(Outlet, "bt_cs_amk") is None:
        db.add(Outlet(id="bt_cs_amk", merchant_id="m1", brand_id="cb_bt_cs",
                      name="BT Coffeeshop @ AMK", address="710 Ang Mo Kio Ave 8, Singapore"))
        db.flush()
    if db.get(DiningTable, "bt_cs_amk_t1") is None:
        db.add(DiningTable(id="bt_cs_amk_t1", merchant_id="m1", outlet_id="bt_cs_amk", label="T01"))
        db.flush()
    if db.scalar(select(QRCode).where(QRCode.token == "bt-coffeeshop-01")) is None:
        db.add(QRCode(merchant_id="m1", outlet_id="bt_cs_amk", table_id="bt_cs_amk_t1",
                      token="bt-coffeeshop-01"))
        db.flush()

    # House stalls — m1's money; menus under the coffeeshop outlet.
    _cs_menu(db, menu_id="o_cs_kopi", merchant_id="m1", outlet_id="bt_cs_amk",
             stall_name="Kopi & Drinks", cuisine="Drinks", logo="☕", sort_order=0,
             spec={"Hot": [("Kopi", 1.40), ("Teh", 1.40), ("Milo", 2.00)],
                   "Cold": [("Kopi Peng", 1.80), ("Teh Peng", 1.80)]})
    _cs_menu(db, menu_id="o_cs_toast", merchant_id="m1", outlet_id="bt_cs_amk",
             stall_name="Toast Box Toast", cuisine="Local", logo="\U0001f35e", sort_order=1,
             spec={"Toast": [("Kaya Butter Toast", 2.80), ("Thick Toast Set", 4.80)],
                   "Eggs": [("Soft-boiled Eggs (2)", 2.00)]})

    # Leased stalls — under their OWN merchants/outlets (keeps them off m1; privacy-safe).
    for mid, bid, oid, menu_id, name, cuisine, logo, spec in [
        ("t_lim", "b_lim", "ol_lim", "o_lim", "Lim's Chicken Rice", "Chicken Rice", "\U0001f357",
         {"Rice": [("Steamed Chicken Rice", 4.50), ("Roasted Chicken Rice", 4.80)], "Sides": [("Soup", 1.00)]}),
        ("t_ah", "b_ah", "ol_ah", "o_ah", "Ah Huat Wok Hei", "Zi Char", "\U0001f373",
         {"Fried": [("Hokkien Mee", 6.00), ("Char Kway Teow", 5.50)], "Veg": [("Sambal Kang Kong", 5.00)]}),
        ("t_mb", "b_mb", "ol_mb", "o_mb", "Mr Bean Soya", "Beverages", "\U0001f964",
         {"Soya": [("Soya Milk", 1.50), ("Tau Huay", 1.80)], "Pancake": [("Soya Pancake", 1.20)]}),
    ]:
        if db.get(Outlet, oid) is None:
            if db.get(Brand, bid) is None:
                db.add(Brand(id=bid, merchant_id=mid, name=name))
                db.flush()
            db.add(Outlet(id=oid, merchant_id=mid, brand_id=bid, name=name,
                          address="710 Ang Mo Kio Ave 8 (at BT Coffeeshop)"))
            db.flush()
        if db.get(Menu, menu_id) is None:
            _cs_menu(db, menu_id=menu_id, merchant_id=mid, outlet_id=oid, stall_name=name,
                     cuisine=cuisine, logo=logo, sort_order=0, spec=spec)


def build_breadtalk(db: Session) -> dict:
    """Idempotently build the BreadTalk Chain/Storefront member-tree + accounts. Returns a summary."""
    roles = seed_rbac(db)

    # Typed Merchant rows for the tenant (settlement-boundary) Chains, so the two companies appear
    # in the operator merchant directory (id == org-node id, per the spine contract).
    label_by_id = {nid: label for nid, _p, _k, label in NODES}
    for tid in SETTLEMENT_BOUNDARIES:
        if db.get(Merchant, tid) is None:
            db.add(Merchant(id=tid, name=label_by_id[tid], legal_name=label_by_id[tid],
                            country="SG", is_active=True))
    db.flush()

    # path/depth + nearest-ancestor boundary resolution in one parent-before-child pass.
    info: dict[str, tuple[str, int, str, str]] = {}  # id -> (path, depth, settlement_acct, loyalty_dom)
    for nid, pid, kind, label in NODES:
        if pid is None:
            path, depth = nid, 0
            settle = nid if nid in SETTLEMENT_BOUNDARIES else nid   # top: self placeholder
            loyalty = nid if nid in LOYALTY_DOMAINS else nid
        else:
            ppath, pdepth, psettle, ployalty = info[pid]
            path, depth = PATH_SEP.join([ppath, nid]), pdepth + 1
            settle = nid if nid in SETTLEMENT_BOUNDARIES else psettle
            loyalty = nid if nid in LOYALTY_DOMAINS else ployalty
        info[nid] = (path, depth, settle, loyalty)

        node = db.get(OrgNode, nid) or OrgNode(id=nid)
        node.parent_id = pid
        node.role = kind
        node.name = label
        node.depth = depth
        node.path = path
        node.sells = kind == STOREFRONT
        node.chain_stopped = nid in CHAIN_STOPPED
        node.is_settlement_boundary = nid in SETTLEMENT_BOUNDARIES
        node.is_loyalty_domain = nid in LOYALTY_DOMAINS
        node.settlement_account_id = settle
        node.loyalty_domain_id = loyalty
        node.is_active = True
        db.add(node)
    db.flush()

    # Prune stale nodes from an earlier seed shape (insert+update+REMOVE, keyed by stable id):
    # any node under the BreadTalk Group path that is no longer in NODES. Leaves-first.
    valid_ids = {nid for nid, _p, _k, _l in NODES}
    for stale in db.scalars(
        select(OrgNode).where(
            or_(OrgNode.path == "btg", OrgNode.path.like("btg" + PATH_SEP + "%")),
            OrgNode.id.not_in(valid_ids),
        ).order_by(OrgNode.depth.desc())
    ).all():
        db.delete(stale)
    db.flush()

    emails = {e for e, _n, _r, _nid in ACCOUNTS}
    # Drop BreadTalk users no longer in ACCOUNTS (+ their assignments).
    for u in db.scalars(select(User).where(User.email.like("%@breadtalk.sg"),
                                           User.email.not_in(emails))).all():
        for a in db.scalars(select(UserRoleAssignment).where(UserRoleAssignment.user_id == u.id)).all():
            db.delete(a)
        db.delete(u)
    db.flush()

    for email, name, role, node_id in ACCOUNTS:
        u = db.scalar(select(User).where(User.email == email))
        if u is None:
            u = User(email=email, full_name=name, password_hash=hash_password(PW))
            db.add(u)
            db.flush()
        # Reconcile NODE assignments (the role/scope may have changed): clear + re-add the one we want.
        for a in db.scalars(select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == u.id,
            UserRoleAssignment.scope_type == ScopeType.NODE.value,
        )).all():
            db.delete(a)
        db.flush()
        db.add(UserRoleAssignment(user_id=u.id, role_id=roles[role].id,
                                  scope_type=ScopeType.NODE.value, scope_id=node_id))

    # Lease edges (idempotent upsert by stable id). rent_type is the foodcourt/coffeeshop switch.
    for lid, venue_id, tenant_id, rent_type, rate in LEASES:
        lease = db.get(Lease, lid) or Lease(id=lid)
        lease.venue_id = venue_id
        lease.tenant_node_id = tenant_id
        lease.rent_type = rent_type
        lease.rate = rate
        lease.is_active = True
        db.add(lease)

    # Make the coffeeshop a real scannable, orderable venue (token bt-coffeeshop-01).
    _build_coffeeshop_orderable(db)

    db.commit()
    return {
        "nodes": len(NODES),
        "accounts": len(ACCOUNTS),
        "storefronts": sum(1 for _n, _p, k, _l in NODES if k == STOREFRONT),
        "tenants": len(SETTLEMENT_BOUNDARIES),
        "leases": len(LEASES),
        "max_depth": max(d for _p, d, _s, _ly in info.values()),
    }


if __name__ == "__main__":  # `python -m app.seed_breadtalk` against the configured DB
    from app.db.session import SessionLocal
    with SessionLocal() as _db:
        print(build_breadtalk(_db))
