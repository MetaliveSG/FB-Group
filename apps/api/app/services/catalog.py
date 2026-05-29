"""Menu read + admin (CRUD) helpers."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError
from app.core.money import money
from app.models.catalog import Menu, MenuCategory, MenuItem, MenuModifier
from app.models.tenancy import Outlet


def get_active_menu(db: Session, outlet_id: str) -> Menu:
    menu = db.scalar(
        select(Menu)
        .where(Menu.outlet_id == outlet_id, Menu.is_active.is_(True))
        .options(selectinload(Menu.categories).selectinload(MenuCategory.items).selectinload(MenuItem.modifiers))
    )
    if not menu:
        raise NotFoundError("No active menu for this outlet", code="no_menu")
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
