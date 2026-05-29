"""Lightweight builders for tests — a self-contained merchant 'world'."""
from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy.orm import Session

from app.auth.permissions import seed_rbac
from app.core.security import hash_password
from app.models.catalog import Menu, MenuCategory, MenuItem, MenuModifier
from app.models.enums import RewardRuleType, RewardScope, RoleName, ScopeType
from app.models.identity import User, UserRoleAssignment
from app.models.loyalty import RewardRule
from app.models.tenancy import Brand, DiningTable, Merchant, Outlet, QRCode

DEMO_PW = "Password123!"


def make_world(db: Session, name: str = "Acme", token_suffix: str = "A", earn_rate: int = 1) -> SimpleNamespace:
    roles = seed_rbac(db)

    merchant = Merchant(name=name)
    db.add(merchant)
    db.flush()
    brand = Brand(merchant_id=merchant.id, name=f"{name} Brand")
    db.add(brand)
    db.flush()
    outlet = Outlet(merchant_id=merchant.id, brand_id=brand.id, name=f"{name} Outlet")
    db.add(outlet)
    db.flush()
    table = DiningTable(merchant_id=merchant.id, outlet_id=outlet.id, label="T01")
    db.add(table)
    db.flush()
    qr = QRCode(merchant_id=merchant.id, outlet_id=outlet.id, table_id=table.id, token=f"QR-{token_suffix}")
    db.add(qr)
    db.flush()

    menu = Menu(merchant_id=merchant.id, outlet_id=outlet.id, name="Main")
    db.add(menu)
    db.flush()
    cat = MenuCategory(menu_id=menu.id, name="Mains", sort_order=0)
    db.add(cat)
    db.flush()
    burger = MenuItem(category_id=cat.id, name="Burger", price=10.00, is_available=True)
    drink = MenuItem(category_id=cat.id, name="Drink", price=5.00, is_available=True)
    unavailable = MenuItem(category_id=cat.id, name="Sold Out Item", price=9.00, is_available=False)
    db.add_all([burger, drink, unavailable])
    db.flush()
    cheese = MenuModifier(item_id=burger.id, name="Extra Cheese", price_delta=2.00)
    db.add(cheese)
    db.flush()

    # Reward rules: earn rate + first-visit bonus.
    db.add(RewardRule(scope_type=RewardScope.MERCHANT.value, scope_id=merchant.id, code="earn",
                      rule_type=RewardRuleType.EARN_RATE.value, config={"points_per_dollar": earn_rate}, is_active=True))
    db.add(RewardRule(scope_type=RewardScope.MERCHANT.value, scope_id=merchant.id, code="welcome",
                      rule_type=RewardRuleType.FIRST_VISIT.value, config={"bonus": 50}, is_active=True))
    db.flush()

    def _user(email, role, scope_type, scope_id):
        u = User(email=email, full_name=email, password_hash=hash_password(DEMO_PW))
        db.add(u)
        db.flush()
        db.add(UserRoleAssignment(user_id=u.id, role_id=roles[role.value].id,
                                  scope_type=scope_type.value, scope_id=scope_id))
        db.flush()
        return u

    owner = _user(f"owner@{name.lower()}.sg", RoleName.MERCHANT_OWNER, ScopeType.MERCHANT, merchant.id)
    outlet_mgr = _user(f"mgr@{name.lower()}.sg", RoleName.OUTLET_MANAGER, ScopeType.OUTLET, outlet.id)
    staff = _user(f"staff@{name.lower()}.sg", RoleName.STAFF, ScopeType.OUTLET, outlet.id)
    db.commit()

    return SimpleNamespace(
        merchant=merchant, brand=brand, outlet=outlet, table=table, qr=qr, menu=menu,
        burger=burger, drink=drink, unavailable=unavailable, cheese=cheese,
        owner=owner, outlet_mgr=outlet_mgr, staff=staff,
        merchant_id=merchant.id, brand_id=brand.id, outlet_id=outlet.id, qr_token=qr.token,
        burger_id=burger.id, drink_id=drink.id, cheese_id=cheese.id, unavailable_id=unavailable.id,
        owner_email=owner.email, outlet_mgr_email=outlet_mgr.email, staff_email=staff.email,
    )


def add_outlet(db: Session, world: SimpleNamespace, suffix: str = "B") -> SimpleNamespace:
    """Add a second outlet (+menu/item/QR) to an existing merchant world."""
    outlet = Outlet(merchant_id=world.merchant_id, brand_id=world.brand_id, name=f"Outlet {suffix}")
    db.add(outlet)
    db.flush()
    table = DiningTable(merchant_id=world.merchant_id, outlet_id=outlet.id, label="T01")
    db.add(table)
    db.flush()
    qr = QRCode(merchant_id=world.merchant_id, outlet_id=outlet.id, table_id=table.id, token=f"QR-{suffix}")
    db.add(qr)
    db.flush()
    menu = Menu(merchant_id=world.merchant_id, outlet_id=outlet.id, name="Main")
    db.add(menu)
    db.flush()
    cat = MenuCategory(menu_id=menu.id, name="Mains", sort_order=0)
    db.add(cat)
    db.flush()
    item = MenuItem(category_id=cat.id, name="Laksa", price=8.00, is_available=True)
    db.add(item)
    db.flush()
    db.commit()
    return SimpleNamespace(outlet_id=outlet.id, qr_token=qr.token, item_id=item.id)


def super_admin(db: Session, email: str = "root@platform.sg") -> User:
    roles = seed_rbac(db)
    u = User(email=email, full_name="Root", password_hash=hash_password(DEMO_PW))
    db.add(u)
    db.flush()
    db.add(UserRoleAssignment(user_id=u.id, role_id=roles[RoleName.SUPER_ADMIN.value].id,
                              scope_type=ScopeType.PLATFORM.value, scope_id=None))
    db.commit()
    return u
