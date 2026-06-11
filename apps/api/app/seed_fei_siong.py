"""Fei Siong Group (FSG) demo seed — the ENTERPRISE pitch tree, focused on Malaysia Boleh! first.

Models FSG's real structure (see memory `fsg-enterprise`): an enterprise CHAIN (FSG) above a foodcourt
venue (Malaysia Boleh!) that holds the tenant boundaries (settlement + loyalty ring), with each Malaysian
hawker stall a STOREFRONT (sells) carrying its own menu. So the DEMO *is* their org.

Scope of THIS seed: FSG → Malaysia Boleh! → 6 stalls with real menus. (The FSG-wide loyalty ring across
ALL brands = the M2 enterprise step; here Malaysia Boleh! is the settlement + loyalty boundary so it works
in the built single-ring model. Other FSG brands / hawker-centre landlording come later.)

Idempotent + ADDITIVE (the `seed_demo_merchants` convention): upserts nodes by id, backfills each stall's
Outlet+Menu+QR, seeds each stall's menu once (skips if it already has items), ensures one owner login + a
spin-the-wheel/jackpot. Safe to re-run; does NOT prune other data.

Run:  cd apps/api && .venv/bin/python -m app.seed_fei_siong
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.permissions import seed_rbac
from app.core.security import hash_password
from app.models.catalog import Menu, MenuCategory, MenuItem
from app.models.enums import RoleName, ScopeType
from app.models.identity import User, UserRoleAssignment
from app.models.org import PATH_SEP, OrgNode
from app.models.tenancy import Merchant
from app.services import storefronts
from app.services.jackpot import ensure_grand_anchor
from app.models.engagement import JackpotPrize, WheelSegment

PW = "Password123!"
CHAIN, STOREFRONT = "CHAIN", "STOREFRONT"

# Stable, readable node ids (≤32 chars) → reproducible QR tokens across a fresh rebuild.
FSG = "fsg"                              # enterprise (structural)
MB = "fsg_malaysia_boleh"               # foodcourt venue = the tenant (settlement + loyalty ring)
S_CHILLI = "mb_chilli_panmee"
S_CKT = "mb_char_kway_teow"
S_BKT = "mb_bak_kut_teh"
S_PRAWN = "mb_prawn_noodles"
S_CLAYPOT = "mb_claypot_rice"
S_CHENDOL = "mb_chendol"

# (id, parent_id, kind, label) — parent-before-child.
NODES = [
    (FSG, None, CHAIN, "Fei Siong Group"),
    (MB, FSG, CHAIN, "Malaysia Boleh!"),
    (S_CHILLI, MB, STOREFRONT, "Damansara Chilli Pan Mee"),
    (S_CKT, MB, STOREFRONT, "Penang Char Kway Teow"),
    (S_BKT, MB, STOREFRONT, "Klang Bak Kut Teh"),
    (S_PRAWN, MB, STOREFRONT, "Penang Prawn Noodles"),
    (S_CLAYPOT, MB, STOREFRONT, "Petaling St Claypot Rice"),
    (S_CHENDOL, MB, STOREFRONT, "Penang Road Chendol"),
]

# Malaysia Boleh! is the tenant: collects money (settlement) AND is the one loyalty ring for its stalls.
# FSG is a structural enterprise parent (the FSG-wide ring across brands = M2).
SETTLEMENT_BOUNDARIES = {MB}
LOYALTY_DOMAINS = {MB}

# Brand themes (cascade-merged enterprise → brand → stall). FSG = a corporate navy house style;
# Malaysia Boleh! overrides with its bold Malaysian red + yellow → every stall inherits the red.
THEMES = {
    FSG: {"primary": "#16335b"},                      # Fei Siong Group house navy (the default)
    MB: {                                             # Malaysia Boleh! — real brand kit (self-hosted assets)
        "primary": "#cc0001", "accent": "#ffcc00",   # Malaysian red + gold
        "logo_url": "/brands/malaysia-boleh/logo.png",
        "hero_image_url": "/brands/malaysia-boleh/hero.jpg",
        "tagline": "A Taste of Malaysia",
    },
}

# Per-stall signboard graphic (the real retro enamel sign) for the directory card — self-hosted.
STALL_SIGNBOARDS = {
    S_CHILLI: "damansara-chilli-pan-mee.png", S_CKT: "penang-char-kuay-teow.png",
    S_BKT: "klang-bak-kut-teh.png", S_PRAWN: "penang-prawn-mee.png",
    S_CLAYPOT: "petaling-claypot-rice.png", S_CHENDOL: "penang-road-chendol.png",
}

ACCOUNTS = [("owner@malaysiaboleh.sg", "Malaysia Boleh Owner", MB)]

# Per-stall menu: {cuisine, logo, items:[(name, description, price, image)]}. Real Malaysian hawker
# dishes; `image` = a file in /brands/malaysia-boleh/dishes/ (free-licensed, see CREDITS.md) or None.
STALL_MENUS: dict[str, dict] = {
    S_CHILLI: {"cuisine": "Noodles · KL", "logo": "🌶️", "items": [
        ("Chilli Ban Mee", "Springy noodles, minced pork, crispy anchovies, fiery dried-chilli", 5.50, "chilli-pan-mee.jpg"),
        ("Chilli Ban Mee (Soup)", "Same fiery noodles, served in a clear pork broth", 5.50, "chilli-pan-mee.jpg"),
        ("Tom Yam Pan Mee", "Handmade noodles in a spicy-sour tom yam soup", 7.30, "chilli-pan-mee.jpg"),
        ("Add: Onsen Egg", "A soft onsen egg on top", 1.50, None),
    ]},
    S_CKT: {"cuisine": "Penang Hawker", "logo": "🍳", "items": [
        ("Char Kway Teow", "Wok-fried flat noodles, cockles, prawns, Chinese sausage, chive", 6.00, "char-kway-teow.jpg"),
        ("Char Kway Teow (Special)", "Extra prawns + double cockles", 7.50, "char-kway-teow.jpg"),
    ]},
    S_BKT: {"cuisine": "Klang · Herbal", "logo": "🍲", "items": [
        ("Bak Kut Teh", "Pork ribs simmered in a peppery herbal broth, with you tiao", 8.00, "bak-kut-teh.jpg"),
        ("Dry Bak Kut Teh", "Klang-style dry, dark herbal gravy, dried chilli & lady's fingers", 9.00, "bak-kut-teh.jpg"),
        ("Pork Trotter", "Braised trotter, add-on", 6.00, "bak-kut-teh.jpg"),
    ]},
    S_PRAWN: {"cuisine": "Penang · Soup", "logo": "🦐", "items": [
        ("Prawn Mee", "Yellow & bee hoon noodles in a rich prawn-and-pork broth", 6.50, "prawn-mee.jpg"),
        ("Special Prawn Mee", "Big prawns, pork ribs & all the toppings", 8.50, "prawn-mee.jpg"),
    ]},
    S_CLAYPOT: {"cuisine": "Petaling St", "logo": "🍚", "items": [
        ("Claypot Chicken Rice", "Rice clay-pot cooked with chicken, lap cheong & dark soy", 7.00, "claypot-chicken-rice.jpg"),
        ("Claypot with Salted Fish", "Claypot rice with salted fish & chicken", 8.00, "claypot-chicken-rice.jpg"),
    ]},
    S_CHENDOL: {"cuisine": "Dessert · Drinks", "logo": "🍧", "items": [
        ("Penang Road Chendol", "Shaved ice, gula melaka, coconut milk, green jelly & red beans", 3.50, "chendol.jpg"),
        ("Ice Kacang", "Mountain of shaved ice, syrups, attap chee, sweet corn", 4.00, "ice-kacang.jpg"),
        ("Kopi / Teh", "Traditional kopitiam coffee or tea", 1.80, "kopi.jpg"),
    ]},
}


_WHEEL = [
    ("10 coins", "points", 10, 3, "#f87171"), ("50 coins", "points", 50, 2, "#fbbf24"),
    ("Free Chendol", "voucher", 0, 1, "#34d399"), ("Try again", "nothing", 0, 3, "#a3a3a3"),
    ("100 coins", "points", 100, 1, "#60a5fa"), ("20 coins", "points", 20, 3, "#c084fc"),
]
_JACKPOT = [
    ("Chilli Pan Mee", 5.50, "🌶️", 3), ("Char Kway Teow", 6.00, "🍳", 2), ("Bak Kut Teh", 8.00, "🍲", 2),
    ("Chendol", 3.50, "🍧", 4), ("Kopi", 1.80, "☕", 4), ("Free Meal", 12.00, "🎁", 1),
    ("Prawn Mee", 6.50, "🦐", 3), ("Egg", 1.50, "🥚", 5), ("You Tiao", 2.00, "🥖", 5),
]


def _ensure_games(db: Session, merchant_id: str) -> None:
    if not db.scalar(select(WheelSegment.id).where(WheelSegment.merchant_id == merchant_id)):
        for i, (label, kind, val, w, color) in enumerate(_WHEEL):
            db.add(WheelSegment(merchant_id=merchant_id, label=label, prize_kind=kind, prize_value=val,
                                voucher_name=label if kind == "voucher" else None, weight=w, color=color, sort_order=i))
    if not db.scalar(select(JackpotPrize.id).where(JackpotPrize.merchant_id == merchant_id)):
        for i, (name, price, emoji, w) in enumerate(_JACKPOT):
            db.add(JackpotPrize(merchant_id=merchant_id, item_name=name, item_price=Decimal(str(price)),
                                emoji=emoji, weight=w, sort_order=i))
    m = db.get(Merchant, merchant_id)
    if m is not None:
        ensure_grand_anchor(m)
    db.flush()


_DISH_DIR = "/brands/malaysia-boleh/dishes/"
_SIGN_DIR = "/brands/malaysia-boleh/stalls/"


def _seed_stall_menu(db: Session, stall_id: str) -> bool:
    """Populate a stall's Menu (id == node.id) with its category + items. Idempotent UPSERT: always
    refreshes the stall's signboard/cuisine/logo and each item's dish photo (matched by name) so re-running
    after adding assets reflects them without a wipe. Returns True the first time it creates the category."""
    menu = db.get(Menu, stall_id)
    if menu is None:
        return False
    spec = STALL_MENUS[stall_id]
    menu.cuisine = spec["cuisine"]      # nicer foodcourt-browse display
    menu.logo = spec["logo"]
    sign = STALL_SIGNBOARDS.get(stall_id)
    menu.signboard_url = f"{_SIGN_DIR}{sign}" if sign else None
    cat = db.scalar(select(MenuCategory).where(MenuCategory.menu_id == stall_id))
    fresh = cat is None
    if cat is None:
        cat = MenuCategory(menu_id=stall_id, name="Menu", sort_order=0)
        db.add(cat)
        db.flush()
    existing = {it.name: it for it in db.scalars(select(MenuItem).where(MenuItem.category_id == cat.id)).all()}
    for i, (name, desc, price, image) in enumerate(spec["items"]):
        img = f"{_DISH_DIR}{image}" if image else None
        it = existing.get(name)
        if it is None:
            db.add(MenuItem(category_id=cat.id, name=name, description=desc, price=Decimal(str(price)),
                            is_available=True, sort_order=i, image_url=img))
        else:
            it.description, it.sort_order, it.image_url = desc, i, img   # refresh (don't touch translations)
    db.flush()
    return fresh


def build_fei_siong(db: Session) -> dict:
    roles = seed_rbac(db)
    label_by_id = {nid: label for nid, _p, _k, label in NODES}

    for tid in SETTLEMENT_BOUNDARIES:
        if db.get(Merchant, tid) is None:
            db.add(Merchant(id=tid, name=label_by_id[tid], legal_name=label_by_id[tid], country="SG", is_active=True))
    db.flush()

    info: dict[str, tuple[str, int, str, str]] = {}
    for nid, pid, kind, label in NODES:
        if pid is None:
            path, depth, settle, loyalty = nid, 0, nid, nid
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
        node.chain_stopped = False
        node.is_settlement_boundary = nid in SETTLEMENT_BOUNDARIES
        node.is_loyalty_domain = nid in LOYALTY_DOMAINS
        node.settlement_account_id = settle
        node.loyalty_domain_id = loyalty
        node.is_active = True
        node.mod_rewards = node.mod_qr_ordering = node.mod_pos = True
        # Foodcourt stalls are self-service (collect from the stall) + takeaway — the SEA-first set.
        if kind == STOREFRONT:
            node.service_options = ["dine_in_pickup", "takeaway"]
        node.theme = THEMES.get(nid)   # brand theme (cascades; stalls inherit Malaysia Boleh!'s red)
        db.add(node)
    db.flush()

    storefronts.provision_missing(db)   # mints each stall's Outlet + Menu(id==node) + Table + QR

    seeded = sum(1 for sid in STALL_MENUS if _seed_stall_menu(db, sid))

    for email, name, node_id in ACCOUNTS:
        u = db.scalar(select(User).where(User.email == email))
        if u is None:
            u = User(email=email, full_name=name, password_hash=hash_password(PW))
            db.add(u)
            db.flush()
        else:
            u.password_hash = hash_password(PW)
            u.is_active = True
        for a in db.scalars(select(UserRoleAssignment).where(
            UserRoleAssignment.user_id == u.id, UserRoleAssignment.scope_type == ScopeType.NODE.value,
        )).all():
            db.delete(a)
        db.flush()
        db.add(UserRoleAssignment(user_id=u.id, role_id=roles[RoleName.MANAGER.value].id,
                                  scope_type=ScopeType.NODE.value, scope_id=node_id))
    db.flush()

    from app.services import pos_staff
    pos = pos_staff.provision_teams_missing(db)
    for tid in SETTLEMENT_BOUNDARIES:
        _ensure_games(db, tid)

    db.commit()
    return {
        "nodes": len(NODES),
        "stalls": sum(1 for _n, _p, k, _l in NODES if k == STOREFRONT),
        "menus_seeded": seeded,
        "tenant": "Malaysia Boleh!",
        "pos_teams_seeded": pos["storefronts_seeded"],
    }


if __name__ == "__main__":
    from app.db.session import SessionLocal
    with SessionLocal() as _db:
        print(build_fei_siong(_db))
