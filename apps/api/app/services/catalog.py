"""Menu read + admin (CRUD) helpers."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError
from app.core.money import money
from app.models.catalog import Menu, MenuCategory, MenuItem, MenuModifier
from app.models.tenancy import Outlet

_MENU_LOAD = selectinload(Menu.categories).selectinload(MenuCategory.items).selectinload(MenuItem.modifiers)


def get_active_menu(db: Session, outlet_id: str) -> Menu:
    menu = db.scalar(
        select(Menu)
        .where(Menu.outlet_id == outlet_id, Menu.is_active.is_(True))
        .order_by(Menu.sort_order, Menu.id)
        .options(_MENU_LOAD)
    )
    if not menu:
        raise NotFoundError("No active menu for this outlet", code="no_menu")
    return menu


def list_outlet_menus(db: Session, outlet_id: str) -> list[Menu]:
    """All active menus (stalls) at an outlet, ordered. One for a single stall/restaurant,
    many for a foodcourt — the frontend shows a stall directory when there is >1."""
    return list(db.scalars(
        select(Menu)
        .where(Menu.outlet_id == outlet_id, Menu.is_active.is_(True))
        .order_by(Menu.sort_order, Menu.id)
    ).all())


def list_outlet_stalls(db: Session, outlet_id: str) -> list[Menu]:
    """Sellable stalls at an outlet, resolved via the org spine (member-tree-map): the set of
    sellable nodes in the outlet's subtree, mapped back to their Menu profiles. The structural
    set comes from the spine; the live `is_active` filter and ordering come from the profile.

    Falls back to the direct menu query when the outlet has no spine node yet (e.g. a freshly
    created outlet whose auto-menu pre-dates a sync), so a stall is never hidden by sync timing.
    The explicit `outlet_id` predicate is a defense-in-depth tenant guard.
    """
    from app.services import org_tree  # local import: avoids any import-order coupling

    node = org_tree.node_for(db, outlet_id)
    if node is None:
        return list_outlet_menus(db, outlet_id)
    sellable_ids = {n.id for n in org_tree.sellable_under(db, node, active_only=False)}
    if not sellable_ids:
        return list_outlet_menus(db, outlet_id)
    return list(db.scalars(
        select(Menu)
        .where(Menu.outlet_id == outlet_id, Menu.is_active.is_(True), Menu.id.in_(sellable_ids))
        .order_by(Menu.sort_order, Menu.id)
    ).all())


def menu_item_count(db: Session, menu_id: str) -> int:
    return db.scalar(
        select(func.count(MenuItem.id))
        .select_from(MenuItem)
        .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
        .where(MenuCategory.menu_id == menu_id, MenuItem.is_available.is_(True))
    ) or 0


def get_outlet_menu(db: Session, outlet_id: str, menu_id: str) -> Menu:
    """Full menu (categories+items+modifiers) for a specific stall, validated to belong
    to the given outlet — so a QR token can only reach menus at its own outlet."""
    menu = db.scalar(
        select(Menu)
        .where(Menu.id == menu_id, Menu.outlet_id == outlet_id, Menu.is_active.is_(True))
        .options(_MENU_LOAD)
    )
    if not menu:
        raise NotFoundError("Stall menu not found", code="menu_not_found")
    return menu


# --- Admin CRUD (tenant-validated: every target resolves to a merchant_id) ---
def _menu_for_category(db: Session, category: MenuCategory) -> Menu | None:
    return db.get(Menu, category.menu_id)


def _require_menu(db: Session, menu_id: str, merchant_id: str) -> Menu:
    menu = db.get(Menu, menu_id)
    if not menu or menu.merchant_id != merchant_id:
        raise NotFoundError("Menu not found", code="menu_not_found")
    return menu


def _require_category(db: Session, category_id: str, merchant_id: str) -> MenuCategory:
    cat = db.get(MenuCategory, category_id)
    menu = _menu_for_category(db, cat) if cat else None
    if not cat or not menu or menu.merchant_id != merchant_id:
        raise NotFoundError("Category not found", code="category_not_found")
    return cat


def _require_item(db: Session, item_id: str, merchant_id: str) -> MenuItem:
    item = db.get(MenuItem, item_id)
    if item:
        _require_category(db, item.category_id, merchant_id)  # raises if cross-tenant
        return item
    raise NotFoundError("Item not found", code="item_not_found")


def outlet_of_menu(db: Session, menu_id: str) -> str | None:
    menu = db.get(Menu, menu_id)
    return menu.outlet_id if menu else None


def list_outlets_with_menu(db: Session, *, merchant_id: str) -> list[dict]:
    """For the menu editor: each outlet + its active menu id."""
    rows = []
    for o in db.scalars(select(Outlet).where(Outlet.merchant_id == merchant_id).order_by(Outlet.name)).all():
        menu = db.scalar(select(Menu).where(Menu.outlet_id == o.id, Menu.is_active.is_(True)))
        rows.append({"outlet_id": o.id, "name": o.name, "menu_id": menu.id if menu else None})
    return rows


def create_category(db: Session, *, merchant_id: str, menu_id: str, name: str, sort_order: int = 0) -> MenuCategory:
    _require_menu(db, menu_id, merchant_id)
    cat = MenuCategory(menu_id=menu_id, name=name, sort_order=sort_order)
    db.add(cat)
    db.flush()
    return cat


def update_category(db: Session, *, merchant_id: str, category_id: str, name=None, sort_order=None) -> MenuCategory:
    cat = _require_category(db, category_id, merchant_id)
    if name is not None:
        cat.name = name
    if sort_order is not None:
        cat.sort_order = sort_order
    db.flush()
    return cat


def delete_category(db: Session, *, merchant_id: str, category_id: str) -> None:
    db.delete(_require_category(db, category_id, merchant_id))
    db.flush()


def create_item(db: Session, *, merchant_id: str, category_id: str, name: str, price: Decimal | float,
                description: str = "", sort_order: int = 0) -> MenuItem:
    _require_category(db, category_id, merchant_id)
    item = MenuItem(category_id=category_id, name=name, price=money(price),
                    description=description, sort_order=sort_order, is_available=True)
    db.add(item)
    db.flush()
    return item


def update_item(db: Session, *, merchant_id: str, item_id: str, name=None, price=None,
                description=None, is_available=None, sort_order=None) -> MenuItem:
    item = _require_item(db, item_id, merchant_id)
    if name is not None:
        item.name = name
    if price is not None:
        item.price = money(price)
    if description is not None:
        item.description = description
    if is_available is not None:
        item.is_available = is_available
    if sort_order is not None:
        item.sort_order = sort_order
    db.flush()
    return item


def delete_item(db: Session, *, merchant_id: str, item_id: str) -> None:
    db.delete(_require_item(db, item_id, merchant_id))
    db.flush()


def create_modifier(db: Session, *, merchant_id: str, item_id: str, name: str,
                    price_delta: Decimal | float = 0) -> MenuModifier:
    _require_item(db, item_id, merchant_id)
    mod = MenuModifier(item_id=item_id, name=name, price_delta=money(price_delta))
    db.add(mod)
    db.flush()
    return mod


def delete_modifier(db: Session, *, merchant_id: str, modifier_id: str) -> None:
    mod = db.get(MenuModifier, modifier_id)
    if mod:
        _require_item(db, mod.item_id, merchant_id)
        db.delete(mod)
        db.flush()
        return
    raise NotFoundError("Modifier not found", code="modifier_not_found")
