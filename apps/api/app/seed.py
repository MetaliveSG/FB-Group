"""Seed a realistic two-merchant demo dataset.

Two merchants (isolation), a coalition spanning both, brands/outlets/tables/QR,
menus, reward rules, role-scoped users, and ~25 customers with backdated order
history so the CRM shows live segments (VIP, new, inactive, frequent, birthday...).

Run:  python -m app.seed   (resets the configured DATABASE_URL)
"""
from __future__ import annotations

import random
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.permissions import seed_rbac
from app.core.security import hash_password
from app.db.base import utcnow
from app.db.session import SessionLocal, engine
from app.loyalty.engine import accrue_on_transaction
from app.models import Base
from app.models.enums import (
    AuthProvider,
    OrderChannel,
    OrderType,
    PaymentMethod,
    RewardRuleType,
    RewardScope,
    RoleName,
    ScopeType,
)
from app.models.identity import Customer, CustomerAuthIdentity, User, UserRoleAssignment
from app.models.campaigns import CampaignAudience
from app.models.engagement import CrmTask, JackpotPrize, RewardCatalogItem, WheelSegment
from app.models.loyalty import Coalition, LoyaltyAccount, RewardRule, coalition_members
from app.models.payments import Payment, Transaction
from app.models.tenancy import Brand, DiningTable, Merchant, Outlet, QRCode
from app.core.errors import ConflictError
from app.services import campaigns as campaign_service
from app.services.jackpot import ensure_grand_anchor
from app.services import winback as winback_service
from app.services.activities import log_activity
from app.services.opportunities import create_opportunity
from app.services.orders import OrderItemInput, create_order

DEMO_PASSWORD = "Password123!"
CUSTOMER_PASSWORD = "Customer123!"

_rng = random.Random(42)


# ---- builders ----------------------------------------------------------
def _menu(db: Session, outlet: Outlet, spec: dict) -> list[str]:
    from app.models.catalog import Menu, MenuCategory, MenuItem, MenuModifier

    menu = Menu(merchant_id=outlet.merchant_id, outlet_id=outlet.id, name="Main Menu")
    db.add(menu)
    db.flush()
    item_ids: list[str] = []
    for ci, (cat_name, items) in enumerate(spec.items()):
        cat = MenuCategory(menu_id=menu.id, name=cat_name, sort_order=ci)
        db.add(cat)
        db.flush()
        for ii, entry in enumerate(items):
            name, price, mods = entry[0], entry[1], entry[2]
            image_url = entry[3] if len(entry) > 3 else None
            item = MenuItem(category_id=cat.id, name=name, description=f"{name}", price=price,
                            image_url=image_url, is_available=True, sort_order=ii)
            db.add(item)
            db.flush()
            for mname, delta in mods:
                db.add(MenuModifier(item_id=item.id, name=mname, price_delta=delta))
            item_ids.append(item.id)
    db.flush()
    return item_ids


def _outlet(db: Session, brand: Brand, name: str, address: str, slug: str, n_tables: int = 8) -> Outlet:
    outlet = Outlet(merchant_id=brand.merchant_id, brand_id=brand.id, name=name, address=address)
    db.add(outlet)
    db.flush()
    for t in range(1, n_tables + 1):
        table = DiningTable(merchant_id=brand.merchant_id, outlet_id=outlet.id, label=f"T{t:02d}")
        db.add(table)
        db.flush()
        # Stable, human-readable token so demo links survive reseeds (e.g. "orchard-01").
        db.add(QRCode(merchant_id=brand.merchant_id, outlet_id=outlet.id, table_id=table.id,
                      token=f"{slug}-{t:02d}"))
    db.flush()
    return outlet


def _user(db: Session, roles: dict, email: str, name: str, role: RoleName,
          scope_type: ScopeType, scope_id: str | None) -> User:
    user = User(email=email, full_name=name, password_hash=hash_password(DEMO_PASSWORD))
    db.add(user)
    db.flush()
    db.add(UserRoleAssignment(user_id=user.id, role_id=roles[role.value].id,
                              scope_type=scope_type.value, scope_id=scope_id))
    db.flush()
    return user


def _rule(db: Session, scope_type: RewardScope, scope_id: str, code: str,
          rule_type: RewardRuleType, config: dict) -> None:
    db.add(RewardRule(scope_type=scope_type.value, scope_id=scope_id, code=code,
                      rule_type=rule_type.value, config=config, is_active=True))


def _customer(db: Session, name: str, phone: str, email: str | None, birthday=None) -> Customer:
    c = Customer(full_name=name, phone=phone, email=email, birthday=birthday)
    db.add(c)
    db.flush()
    if email:
        db.add(CustomerAuthIdentity(customer_id=c.id, provider=AuthProvider.PASSWORD.value,
                                    identifier=email, secret_hash=hash_password(CUSTOMER_PASSWORD),
                                    is_verified=True))
    db.add(CustomerAuthIdentity(customer_id=c.id, provider=AuthProvider.MOBILE_OTP.value,
                                identifier=phone, is_verified=True))
    db.flush()
    return c


def _visit(db: Session, *, customer: Customer, outlet: Outlet, item_ids: list[str], when,
           heavy: bool = False) -> None:
    n = _rng.randint(2, 4) if heavy else _rng.randint(1, 3)
    chosen = _rng.sample(item_ids, k=min(n, len(item_ids)))
    qty = (lambda: _rng.randint(2, 4)) if heavy else (lambda: _rng.randint(1, 2))
    items = [OrderItemInput(menu_item_id=i, quantity=qty()) for i in chosen]
    order = create_order(db, outlet_id=outlet.id, items=items, customer_id=customer.id,
                         channel=OrderChannel.QR, order_type=OrderType.DINE_IN)
    order.created_at = when
    order.placed_at = when
    order.status = "completed"
    order.completed_at = when
    payment = Payment(order_id=order.id, method=PaymentMethod.PAYNOW.value, amount=order.total,
                      status="success", reference="MOCK-SEED")
    db.add(payment)
    db.flush()
    txn = Transaction(merchant_id=order.merchant_id, outlet_id=order.outlet_id,
                      customer_id=customer.id, order_id=order.id, payment_id=payment.id,
                      amount=order.total)
    db.add(txn)
    db.flush()
    txn.created_at = when
    pts = accrue_on_transaction(db, customer=customer, merchant_id=order.merchant_id,
                                amount=order.total, order_id=order.id, now=when)
    txn.points_earned = pts
    db.flush()


# ---- main seed ---------------------------------------------------------
def build_demo(db: Session) -> dict:
    roles = seed_rbac(db)
    now = utcnow()
    month = now.month

    # --- Merchant 1: Makan Express (fast food chain) ---
    m1 = Merchant(name="Makan Express", legal_name="Makan Express Pte Ltd")
    db.add(m1)
    db.flush()
    b1 = Brand(merchant_id=m1.id, name="Makan Express", cuisine_type="Fast Food")
    db.add(b1)
    db.flush()
    o_orchard = _outlet(db, b1, "Makan Express — Orchard", "111 Orchard Rd", slug="orchard")
    o_tampines = _outlet(db, b1, "Makan Express — Tampines", "10 Tampines Central", slug="tampines")
    fastfood_menu = {
        "Burgers": [("Chicken Burger", 6.50, [("Extra Cheese", 1.00), ("Add Egg", 1.50)]),
                    ("Beef Burger", 8.00, [("Extra Cheese", 1.00)]),
                    ("Fish Burger", 7.00, [])],
        "Sides": [("Fries", 3.50, [("Make it Large", 1.50)]), ("Nuggets (6pc)", 5.00, [])],
        "Drinks": [("Kopi", 2.00, []), ("Teh", 2.00, []), ("Soft Drink", 2.50, [])],
    }
    items_orchard = _menu(db, o_orchard, fastfood_menu)
    items_tampines = _menu(db, o_tampines, fastfood_menu)

    # --- Merchant 2: Kopi Culture (café) ---
    m2 = Merchant(name="Kopi Culture", legal_name="Kopi Culture LLP")
    db.add(m2)
    db.flush()
    b2 = Brand(merchant_id=m2.id, name="Kopi Culture", cuisine_type="Cafe")
    db.add(b2)
    db.flush()
    o_holland = _outlet(db, b2, "Kopi Culture — Holland Village", "5 Lor Mambong", slug="holland")
    cafe_menu = {
        "Coffee": [("Flat White", 5.50, [("Oat Milk", 0.80)]), ("Latte", 5.50, []),
                   ("Espresso", 4.00, [])],
        "Cakes": [("Cheesecake", 7.50, []), ("Brownie", 6.00, [])],
    }
    items_holland = _menu(db, o_holland, cafe_menu)

    # --- Merchant 3: Hawker Hub (food court) ---
    m3 = Merchant(name="Hawker Hub", legal_name="Hawker Hub Pte Ltd")
    db.add(m3)
    db.flush()
    b3 = Brand(merchant_id=m3.id, name="Hawker Hub", cuisine_type="Food Court")
    db.add(b3)
    db.flush()
    o_maxwell = _outlet(db, b3, "Hawker Hub — Maxwell", "1 Kadayanallur St", slug="hawker-maxwell")
    o_chinatown = _outlet(db, b3, "Hawker Hub — Chinatown", "335 Smith St", slug="hawker-chinatown")
    foodcourt_menu = {
        "Local Mains": [("Chicken Rice", 5.00, [("Extra Chicken", 2.00)]),
                        ("Char Kway Teow", 6.00, []), ("Laksa", 6.50, [("Extra Cockles", 1.50)])],
        "Drinks": [("Sugarcane", 2.50, []), ("Bandung", 2.50, []), ("Kopi-O", 1.60, [])],
    }
    items_maxwell = _menu(db, o_maxwell, foodcourt_menu)
    items_chinatown = _menu(db, o_chinatown, foodcourt_menu)

    # --- Reward rules (configurable, per merchant) ---
    _rule(db, RewardScope.MERCHANT, m1.id, "base-earn", RewardRuleType.EARN_RATE, {"points_per_dollar": 1})
    _rule(db, RewardScope.MERCHANT, m1.id, "welcome", RewardRuleType.FIRST_VISIT, {"bonus": 50})
    _rule(db, RewardScope.MERCHANT, m1.id, "birthday", RewardRuleType.BIRTHDAY, {"bonus": 100})
    _rule(db, RewardScope.MERCHANT, m1.id, "loyal-5", RewardRuleType.REPEAT_VISIT, {"every": 5, "bonus": 30})
    _rule(db, RewardScope.MERCHANT, m2.id, "base-earn", RewardRuleType.EARN_RATE, {"points_per_dollar": 2})
    _rule(db, RewardScope.MERCHANT, m2.id, "welcome", RewardRuleType.FIRST_VISIT, {"bonus": 30})
    _rule(db, RewardScope.MERCHANT, m3.id, "base-earn", RewardRuleType.EARN_RATE, {"points_per_dollar": 1})
    _rule(db, RewardScope.MERCHANT, m3.id, "welcome", RewardRuleType.FIRST_VISIT, {"bonus": 40})

    # --- Coalition spanning all three merchants ---
    coalition = Coalition(name="SG Eats Rewards")
    db.add(coalition)
    db.flush()
    db.execute(coalition_members.insert().values([
        {"coalition_id": coalition.id, "merchant_id": m1.id},
        {"coalition_id": coalition.id, "merchant_id": m2.id},
        {"coalition_id": coalition.id, "merchant_id": m3.id},
    ]))
    _rule(db, RewardScope.COALITION, coalition.id, "coalition-earn", RewardRuleType.EARN_RATE,
          {"points_per_dollar": 0.2})
    db.flush()

    # --- Users (role-scoped) ---
    _user(db, roles, "superadmin@platform.sg", "Platform Admin", RoleName.SUPER_ADMIN, ScopeType.PLATFORM, None)
    owner_user = _user(db, roles, "owner@makan.sg", "Makan Owner", RoleName.MERCHANT_OWNER, ScopeType.MERCHANT, m1.id)
    _user(db, roles, "manager.orchard@makan.sg", "Orchard Manager", RoleName.OUTLET_MANAGER, ScopeType.OUTLET, o_orchard.id)
    _user(db, roles, "staff.orchard@makan.sg", "Orchard Staff", RoleName.STAFF, ScopeType.OUTLET, o_orchard.id)
    _user(db, roles, "owner@kopiculture.sg", "Kopi Owner", RoleName.MERCHANT_OWNER, ScopeType.MERCHANT, m2.id)
    _user(db, roles, "owner@hawkerhub.sg", "Hawker Owner", RoleName.MERCHANT_OWNER, ScopeType.MERCHANT, m3.id)

    # --- Customers with backdated history ---
    # profile -> (count, min_visits, max_visits, recency_days_range, outlet pool, birthday_month?)
    first_names = ["Wei", "Siti", "Raj", "Mei", "Aiman", "Priya", "Jun", "Nurul", "Hao", "Devi",
                   "Bryan", "Farah", "Kumar", "Ling", "Hafiz", "Joanne", "Tan", "Indra", "Zoe", "Arun",
                   "Lina", "Chong", "Maya", "Ken", "Suri"]
    pool_a = items_orchard
    pool_b = items_tampines
    outlets_items = {o_orchard.id: (o_orchard, pool_a), o_tampines.id: (o_tampines, pool_b)}

    profiles = (
        [("vip", 8, 12, (1, 20), "A", True)] * 4
        + [("frequent", 5, 8, (2, 35), "AB", False)] * 7
        + [("active", 2, 4, (3, 30), "AB", True)] * 10
        + [("new", 1, 1, (1, 9), "B", False)] * 7
        + [("inactive", 2, 5, (75, 120), "A", False)] * 7
        + [("lowfreq", 2, 2, (40, 55), "B", False)] * 3
        + [("active", 3, 5, (5, 25), "A", False)] * 2
    )
    customers = []
    kinds = []
    for idx, (kind, vmin, vmax, recency, outlet_sel, bday) in enumerate(profiles):
        name = f"{first_names[idx % len(first_names)]} {kind.title()}{idx}"
        phone = f"+65{80000000 + idx}"
        email = f"cust{idx}@example.sg"
        birthday = None
        if bday and idx % 4 == 0:
            birthday = utcnow().replace(month=month, day=15).date()
        c = _customer(db, name, phone, email, birthday)
        customers.append(c)
        kinds.append(kind)

        n_visits = _rng.randint(vmin, vmax)
        # spread visit dates between recency window start and end (ascending)
        last_days = _rng.randint(*recency)
        span = _rng.randint(20, 90)
        for v in range(n_visits):
            frac = v / max(n_visits - 1, 1)
            days_ago = int(last_days + (1 - frac) * span)
            when = now - timedelta(days=days_ago, hours=_rng.randint(8, 21))
            if outlet_sel == "A":
                o, pool = outlets_items[o_orchard.id]
            elif outlet_sel == "B":
                o, pool = outlets_items[o_tampines.id]
            else:
                o, pool = outlets_items[_rng.choice([o_orchard.id, o_tampines.id])]
            _visit(db, customer=c, outlet=o, item_ids=pool, when=when, heavy=kind in ("vip", "frequent"))

    # A few coalition cross-visits at Kopi Culture (merchant 2)
    for c in customers[:3]:
        _visit(db, customer=c, outlet=o_holland, item_ids=items_holland,
               when=now - timedelta(days=_rng.randint(2, 20)))

    # Cross-visits at Hawker Hub (merchant 3) so its CRM is populated too
    for c in customers[:8]:
        o, pool = _rng.choice([(o_maxwell, items_maxwell), (o_chinatown, items_chinatown)])
        for _ in range(_rng.randint(1, 3)):
            _visit(db, customer=c, outlet=o, item_ids=pool,
                   when=now - timedelta(days=_rng.randint(2, 45)))

    # --- Redeemable reward catalog ---
    # Coins are NOT redeemable for cash — rewards are free items only (no discounts).
    catalog = {
        m1.id: [("Free Kopi", "free_item", 0, 150), ("Free Fries", "free_item", 0, 250)],
        m2.id: [("Free Espresso", "free_item", 0, 200)],
    }
    for mid, items in catalog.items():
        for i, (name, kind, val, cost) in enumerate(items):
            db.add(RewardCatalogItem(merchant_id=mid, name=name, kind=kind,
                                     value=Decimal(str(val)), cost_points=cost, sort_order=i))

    # --- Spin-the-wheel segments ---
    wheels = {
        m1.id: [("10 coins", "points", 10, 3, "#f87171"), ("50 coins", "points", 50, 2, "#fbbf24"),
                ("Free Kopi", "voucher", 0, 1, "#34d399"), ("Try again", "nothing", 0, 3, "#a3a3a3"),
                ("100 coins", "points", 100, 1, "#60a5fa"), ("20 coins", "points", 20, 3, "#c084fc")],
        m2.id: [("5 coins", "points", 5, 3, "#f87171"), ("Free Espresso", "voucher", 0, 1, "#34d399"),
                ("Try again", "nothing", 0, 3, "#a3a3a3"), ("50 coins", "points", 50, 1, "#60a5fa")],
    }
    for mid, segs in wheels.items():
        for i, (label, kind, val, w, color) in enumerate(segs):
            db.add(WheelSegment(merchant_id=mid, label=label, prize_kind=kind, prize_value=val,
                                voucher_name=label if kind == "voucher" else None,
                                weight=w, color=color, sort_order=i))
    db.flush()

    # --- CRM: owner assignment, tasks, opportunities, logged activities (Makan) ---
    def _pick(kind: str, n: int = 1):
        chosen = [customers[i] for i, k in enumerate(kinds) if k == kind][:n]
        return chosen or [customers[0]]

    def _g(lst, i):
        return lst[i] if i < len(lst) else lst[0]

    vips = _pick("vip", 4)
    freqs = _pick("frequent", 4)
    inactives = _pick("inactive", 3)

    for c in customers[:12]:
        acct = db.scalar(select(LoyaltyAccount).where(
            LoyaltyAccount.customer_id == c.id,
            LoyaltyAccount.scope_type == RewardScope.MERCHANT.value,
            LoyaltyAccount.scope_id == m1.id))
        if acct:
            acct.owner_user_id = owner_user.id

    for c, title, prio in [
        (_g(vips, 0), "Call VIP for feedback", "high"),
        (_g(vips, 1), "Send birthday voucher", "normal"),
        (_g(inactives, 0), "Win-back: inactive customer", "high"),
        (_g(freqs, 0), "Offer catering package", "normal"),
    ]:
        db.add(CrmTask(merchant_id=m1.id, customer_id=c.id, title=title, priority=prio,
                       assignee_user_id=owner_user.id, created_by_user_id=owner_user.id,
                       due_date=now.date()))

    # Opportunities (sales pipeline)
    opp_specs = [
        (_g(vips, 0), "Corporate lunch catering — 50 pax", "qualified", 1200),
        (_g(vips, 1), "Office pantry weekly supply", "proposal", 3500),
        (_g(freqs, 0), "Birthday party package", "prospecting", 600),
        (_g(vips, 2), "Wedding catering", "negotiation", 8000),
        (_g(freqs, 1), "Festive hamper bulk order", "won", 2200),
        (_g(inactives, 0), "Loyalty win-back deal", "prospecting", 300),
        (_g(vips, 3), "Franchise inquiry", "proposal", 15000),
        (_g(freqs, 2), "Monthly team dinner", "lost", 900),
    ]
    for cust, name, stage, amt in opp_specs:
        create_opportunity(db, merchant_id=m1.id, customer_id=cust.id, name=name, amount=amt,
                           stage=stage, owner_user_id=owner_user.id, created_by_user_id=owner_user.id,
                           expected_close_date=(now + timedelta(days=_rng.randint(7, 60))).date())

    # Logged activities (calls / emails / meetings / WhatsApp)
    act_specs = [
        (_g(vips, 0), "call", "Thanked for loyalty", "Very happy; will refer friends"),
        (_g(vips, 0), "email", "Sent VIP voucher", "$10 voucher emailed"),
        (_g(vips, 1), "meeting", "Catering discussion", "Discussed 50-pax menu + pricing"),
        (_g(freqs, 0), "whatsapp", "Birthday greeting", "Sent birthday message + 2x coins offer"),
        (_g(freqs, 1), "call", "Follow-up on hamper order", "Confirmed quantities"),
        (_g(inactives, 0), "call", "Win-back call", "No answer; left voicemail"),
        (_g(inactives, 1), "email", "We miss you — 100 bonus coins", "Re-engagement email sent"),
        (_g(vips, 2), "meeting", "Wedding tasting", "Tasting scheduled next week"),
    ]
    for cust, atype, subj, body in act_specs:
        log_activity(db, merchant_id=m1.id, customer_id=cust.id, activity_type=atype, subject=subj,
                     body=body, occurred_at=now - timedelta(days=_rng.randint(1, 30)),
                     logged_by_user_id=owner_user.id)
    db.flush()

    # --- Example campaign: built, mock-sent, with some redemptions ---
    campaign = campaign_service.create_campaign(
        db, merchant_id=m1.id, name="Weekend 2X Coins", campaign_type="whatsapp_promo",
        message_template="Hi {name}, enjoy 2X coins this weekend at Makan Express! 🍔",
        reward_points=0)
    makan_customers = db.scalars(select(LoyaltyAccount.customer_id).where(
        LoyaltyAccount.scope_type == RewardScope.MERCHANT.value,
        LoyaltyAccount.scope_id == m1.id)).all()
    for cust_id in makan_customers:
        db.add(CampaignAudience(campaign_id=campaign.id, customer_id=cust_id))
    db.flush()
    campaign_service.send_campaign(db, merchant_id=m1.id, campaign=campaign)
    for cust_id in list(makan_customers)[:6]:
        campaign_service.record_redemption(db, merchant_id=m1.id, campaign=campaign,
                                           customer_id=cust_id, revenue=_rng.choice([18.5, 24.0, 31.5, 12.0]))
    db.flush()

    # --- Win-back pipeline examples (retention deals for lapsed customers) ---
    try:
        winback_service.launch(db, merchant_id=m1.id, owner_user_id=owner_user.id,
                               rfm_segments=["At Risk", "Hibernating", "Can't Lose Them"], create_campaign=False)
    except ConflictError:
        pass  # no lapsed customers in this random seed — fine

    db.commit()

    # --- Merchant 4: Kampong Eats (SG local food) — joins the coalition ---
    kampong = seed_kampong(db, coalition_id=coalition.id)

    return {
        "merchants": [m1.name, m2.name, m3.name, kampong.get("merchant_name", "Kampong Eats")],
        "merchant1_id": m1.id,
        "merchant2_id": m2.id,
        "merchant3_id": m3.id,
        "merchant4_id": kampong.get("merchant_id"),
        "outlet_orchard_id": o_orchard.id,
        "outlet_tampines_id": o_tampines.id,
        "coalition": coalition.name,
        "customers": len(customers) + kampong.get("customers", 0),
        "opportunities": len(opp_specs),
        "activities": len(act_specs),
        "sample_qr_token": "orchard-01",
        "kampong_qr_token": "kampong-bedok-01",
    }


# ---- Merchant 4: Kampong Eats (SG local food) --------------------------
# The 11 Kampong menu items as 3x3 jackpot reel symbols. Weight is inversely
# proportional to price (cheap items hit more often → rare wins are bigger prizes).
KAMPONG_JACKPOT_PRIZES = [
    # (item_name, price, emoji, weight) — every emoji must be visually distinct
    # (the buns and the chicken pair previously collided on the spinning grid).
    ("Fish Ball Noodle",     5.50, "🍜", 1),
    ("Curry Rice",           5.50, "🍛", 1),
    ("Burger",               4.50, "🍔", 2),   # replaced Chicken Wings (no wing emoji existed)
    ("French Fries",         3.50, "🍟", 3),
    ("Chicken Drumstick",    3.50, "🍗", 3),
    ("Chendol",              3.00, "🍧", 4),
    ("Fish Soup (slice)",    7.00, "🐟", 1),
    ("Teh Tarik",            2.20, "🥤", 5),
    ("Chicken Bun",          1.80, "🐔", 5),   # was 🥟 (collided with pork bun)
    ("Pork Bun",             1.80, "🐷", 5),   # was 🥟
    ("Roti Prata (Plain)",   1.80, "🫓", 5),
]


def _ensure_kampong_jackpot(db: Session, merchant_id: str) -> dict:
    """Idempotent: bring the Kampong jackpot prizes in sync with the seed constant.

    The seed list is the source of truth — rows missing from the DB get inserted,
    drifted attrs (emoji, price, weight, sort_order) get patched, and rows whose
    item_name is no longer in the seed get removed (so renames like
    'Fish Cake (slice)' → 'Fish Soup (slice)' don't strand orphans).
    Guard: if the seed list is empty, we do nothing rather than wipe the merchant.
    """
    if not KAMPONG_JACKPOT_PRIZES:
        return {"inserted": 0, "updated": 0, "removed": 0}

    seed_by_name = {name: (i, price, emoji, w)
                    for i, (name, price, emoji, w) in enumerate(KAMPONG_JACKPOT_PRIZES)}
    rows = {p.item_name: p for p in db.scalars(
        select(JackpotPrize).where(JackpotPrize.merchant_id == merchant_id)
    ).all()}

    inserted = updated = removed = 0
    for name, (i, price, emoji, w) in seed_by_name.items():
        row = rows.get(name)
        if row is None:
            db.add(JackpotPrize(merchant_id=merchant_id, item_name=name,
                                item_price=Decimal(str(price)), emoji=emoji,
                                weight=w, sort_order=i))
            inserted += 1
        elif (row.emoji != emoji or float(row.item_price) != price
              or row.weight != w or row.sort_order != i):
            row.emoji = emoji
            row.item_price = Decimal(str(price))
            row.weight = w
            row.sort_order = i
            updated += 1

    for name, row in rows.items():
        if name not in seed_by_name:
            db.delete(row)
            removed += 1

    # Anchor the progressive grand-jackpot pot at seed time (idempotent) so it
    # starts ticking without a write-on-read in the GET path.
    merchant = db.get(Merchant, merchant_id)
    if merchant is not None:
        ensure_grand_anchor(merchant)

    db.flush()
    return {"inserted": inserted, "updated": updated, "removed": removed}



# (name, price, modifiers, image_url) — images are real food photos served from
# apps/web/public/menu/ (sourced from Wikimedia Commons, see docs). The image path
# is the single source of truth; _ensure_kampong_images() syncs them onto live rows.
KAMPONG_MENU = {
    "Hawker Mains": [
        ("Fish Ball Noodle", 5.50, [("Extra Fish Ball", 1.50), ("Less Spicy", 0.00)], "/menu/fish-ball-noodle.jpg"),
        ("Fish Soup (slice)", 7.00, [("Extra Fish", 1.50), ("Less Spicy", 0.00)], "/menu/fish-soup.jpg"),
        ("Curry Rice", 5.50, [("Add Chicken", 2.00), ("Add Egg", 1.00)], "/menu/curry-rice.jpg"),
        ("Roti Prata (Plain)", 1.80, [("Add Egg", 1.00), ("Add Cheese", 1.50)], "/menu/roti-prata.jpg"),
    ],
    "Bakery": [
        ("Chicken Bun", 1.80, [], "/menu/chicken-bun.jpg"),
        ("Pork Bun", 1.80, [], "/menu/pork-bun.jpg"),
    ],
    "Fried Snacks": [
        ("Chicken Drumstick", 3.50, [], "/menu/chicken-drumstick.jpg"),
        ("Burger", 4.50, [("Spicy", 0.00)], "/menu/burger.jpg"),
        ("French Fries", 3.50, [("Make it Large", 1.50)], "/menu/french-fries.jpg"),
    ],
    "Drinks": [
        ("Teh Tarik", 2.20, [("Iced", 0.50)], "/menu/teh-tarik.jpg"),
    ],
    "Dessert": [
        ("Chendol", 3.00, [("Extra Gula Melaka", 0.50)], "/menu/chendol.jpg"),
    ],
}


def _kampong_image_map() -> dict[str, str]:
    """name → image_url, derived from KAMPONG_MENU (single source of truth)."""
    return {
        entry[0]: entry[3]
        for items in KAMPONG_MENU.values()
        for entry in items
        if len(entry) > 3 and entry[3]
    }


def _ensure_kampong_images(db: Session, merchant_id: str) -> dict:
    """Idempotently sync real-food photos onto Kampong Eats' live menu rows.

    seed_kampong() no-ops once the merchant exists, so newly-added image_urls must
    be patched onto already-seeded rows here. Matches by item name across all the
    merchant's outlets; only writes when the value actually drifts.
    """
    from app.models.catalog import Menu, MenuCategory, MenuItem

    images = _kampong_image_map()
    rows = db.scalars(
        select(MenuItem)
        .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
        .join(Menu, MenuCategory.menu_id == Menu.id)
        .where(Menu.merchant_id == merchant_id)
    ).all()
    updated = 0
    for row in rows:
        want = images.get(row.name)
        if want and row.image_url != want:
            row.image_url = want
            updated += 1
    return {"items": len(rows), "images_updated": updated}


def seed_kampong(db: Session, *, coalition_id: str | None = None,
                 seed_customers: bool = True) -> dict:
    """Add 'Kampong Eats' — a Singapore local F&B merchant — to the existing seed.

    Idempotent: no-op if the merchant already exists. Safe to run repeatedly
    against the live Postgres without nuking data / invalidating issued tokens.
    Joins the SG Eats Rewards coalition automatically if it's present.
    """
    existing = db.scalar(select(Merchant).where(Merchant.name == "Kampong Eats"))
    if existing:
        # Bolt on any new add-ons / sync drifted symbols — idempotent.
        jackpot = _ensure_kampong_jackpot(db, existing.id)
        images = _ensure_kampong_images(db, existing.id)
        db.commit()
        return {"merchant_id": existing.id, "merchant_name": existing.name,
                "status": "already_exists", "jackpot_sync": jackpot, "image_sync": images}

    roles = seed_rbac(db)  # idempotent
    now = utcnow()

    m = Merchant(name="Kampong Eats", legal_name="Kampong Eats Pte Ltd")
    db.add(m)
    db.flush()
    brand = Brand(merchant_id=m.id, name="Kampong Eats", cuisine_type="Singapore Local")
    db.add(brand)
    db.flush()

    o_bedok = _outlet(db, brand, "Kampong Eats — Bedok", "501 Bedok North St 3", slug="kampong-bedok")
    o_toapayoh = _outlet(db, brand, "Kampong Eats — Toa Payoh", "190 Toa Payoh Lor 6", slug="kampong-toapayoh")
    items_bedok = _menu(db, o_bedok, KAMPONG_MENU)
    items_toapayoh = _menu(db, o_toapayoh, KAMPONG_MENU)

    # Reward rules — slightly different shape from Makan to keep merchants distinct.
    _rule(db, RewardScope.MERCHANT, m.id, "base-earn", RewardRuleType.EARN_RATE, {"points_per_dollar": 1})
    _rule(db, RewardScope.MERCHANT, m.id, "welcome", RewardRuleType.FIRST_VISIT, {"bonus": 30})
    _rule(db, RewardScope.MERCHANT, m.id, "birthday", RewardRuleType.BIRTHDAY, {"bonus": 80})
    _rule(db, RewardScope.MERCHANT, m.id, "loyal-3", RewardRuleType.REPEAT_VISIT, {"every": 3, "bonus": 20})

    # Join the SG Eats coalition (so coalition points accrue here too).
    if coalition_id is None:
        coa = db.scalar(select(Coalition).where(Coalition.name == "SG Eats Rewards"))
        coalition_id = coa.id if coa else None
    if coalition_id:
        already = db.scalar(
            select(coalition_members).where(
                coalition_members.c.coalition_id == coalition_id,
                coalition_members.c.merchant_id == m.id,
            )
        )
        if not already:
            db.execute(coalition_members.insert().values(coalition_id=coalition_id, merchant_id=m.id))

    owner = _user(db, roles, "owner@kampongeats.sg", "Kampong Owner",
                  RoleName.MERCHANT_OWNER, ScopeType.MERCHANT, m.id)
    _user(db, roles, "manager.bedok@kampongeats.sg", "Bedok Manager",
          RoleName.OUTLET_MANAGER, ScopeType.OUTLET, o_bedok.id)

    # Reward catalog — local-flavoured, free items only (no cash redemption).
    for i, (name, kind, val, cost) in enumerate([
        ("Free Teh Tarik", "free_item", 0, 150),
        ("Free Chendol", "free_item", 0, 250),
    ]):
        db.add(RewardCatalogItem(merchant_id=m.id, name=name, kind=kind,
                                 value=Decimal(str(val)), cost_points=cost, sort_order=i))

    # Spin-the-wheel — same engine, kampong-themed segments.
    for i, (label, kind, val, w, color) in enumerate([
        ("5 coins", "points", 5, 3, "#f87171"),
        ("20 coins", "points", 20, 3, "#fbbf24"),
        ("Free Teh Tarik", "voucher", 0, 1, "#34d399"),
        ("Try again", "nothing", 0, 3, "#a3a3a3"),
        ("100 coins", "points", 100, 1, "#60a5fa"),
        ("50 coins", "points", 50, 2, "#c084fc"),
    ]):
        db.add(WheelSegment(merchant_id=m.id, label=label, prize_kind=kind, prize_value=val,
                            voucher_name=label if kind == "voucher" else None,
                            weight=w, color=color, sort_order=i))

    _ensure_kampong_jackpot(db, m.id)

    customer_count = 0
    if seed_customers:
        first_names = ["Ahmad", "Mei Lin", "Suresh", "Wati", "Daniel",
                       "Hui Min", "Vikram", "Aishah", "Marcus", "Geetha"]
        # (kind, vmin, vmax, recency_days_range, outlet_sel, birthday_eligible)
        profiles = (
            [("vip", 8, 12, (1, 15), "AB", True)] * 2
            + [("frequent", 5, 7, (3, 30), "AB", False)] * 3
            + [("new", 1, 1, (1, 7), "B", False)] * 3
            + [("inactive", 2, 4, (75, 110), "A", False)] * 2
        )
        outlets_items = {o_bedok.id: (o_bedok, items_bedok),
                         o_toapayoh.id: (o_toapayoh, items_toapayoh)}
        month = now.month
        for idx, (kind, vmin, vmax, recency, sel, bday) in enumerate(profiles):
            name = f"{first_names[idx]} {kind.title()}"
            phone = f"+65{81000000 + idx}"        # +6581000000–+6581000009 (distinct from m1's +658000xxxx)
            email = f"cust_kpe_{idx}@example.sg"
            birthday = utcnow().replace(month=month, day=15).date() if bday and idx % 2 == 0 else None
            c = _customer(db, name, phone, email, birthday)

            n_visits = _rng.randint(vmin, vmax)
            last_days = _rng.randint(*recency)
            span = _rng.randint(20, 90)
            for v in range(n_visits):
                frac = v / max(n_visits - 1, 1)
                days_ago = int(last_days + (1 - frac) * span)
                when = now - timedelta(days=days_ago, hours=_rng.randint(8, 21))
                if sel == "A":
                    o, pool = outlets_items[o_bedok.id]
                elif sel == "B":
                    o, pool = outlets_items[o_toapayoh.id]
                else:
                    o, pool = outlets_items[_rng.choice([o_bedok.id, o_toapayoh.id])]
                _visit(db, customer=c, outlet=o, item_ids=pool, when=when, heavy=kind == "vip")
            customer_count += 1

        # Owner record-assignment on all kampong customers (mirrors Makan).
        from sqlalchemy import update as _update
        db.execute(_update(LoyaltyAccount).where(
            LoyaltyAccount.scope_type == RewardScope.MERCHANT.value,
            LoyaltyAccount.scope_id == m.id,
        ).values(owner_user_id=owner.id))

    db.commit()
    return {
        "merchant_id": m.id,
        "merchant_name": m.name,
        "outlets": [o_bedok.name, o_toapayoh.name],
        "qr_tokens_sample": ["kampong-bedok-01", "kampong-toapayoh-01"],
        "items": len(items_bedok),
        "customers": customer_count,
        "owner_email": "owner@kampongeats.sg",
        "coalition_joined": coalition_id is not None,
        "status": "created",
    }


def reset_and_seed() -> dict:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        return build_demo(db)


def seed_if_empty() -> dict | None:
    """Idempotent seed — only populate when there are no merchants yet.

    Lets the API container restart/redeploy WITHOUT wiping data, so already-issued
    tokens (whose subject ids would otherwise change) stay valid. Schema is owned by
    Alembic (run before this). Use `python -m app.seed` to force a full reset+reseed.
    """
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Merchant)):
            return None
        return build_demo(db)


if __name__ == "__main__":
    summary = reset_and_seed()
    print("Seed complete:")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    print(f"\n  Demo staff password:    {DEMO_PASSWORD}")
    print(f"  Demo customer password: {CUSTOMER_PASSWORD}")
