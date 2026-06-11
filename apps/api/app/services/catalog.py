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
    """Sellable stalls a diner can order from at this venue, resolved via the org spine — the SINGLE
    resolver used for every venue (single shop, foodcourt, coffeeshop): house stalls (the venue's
    own sellable subtree) PLUS stalls leased in from another owner (`leasing.storefronts_at_venue`).
    The structural set comes from the spine; `is_active` + display come from the Menu profile.

    Mapping is by node id (node.id == menu.id), so a leased-in stall — whose Menu lives under a
    DIFFERENT outlet/merchant — still resolves. Falls back to the direct menu query when the venue
    has no spine subtree (a collapsed single-storefront merchant, or pre-sync timing), so a stall is
    never hidden; lease support kicks in for venues that have a real spine subtree.
    """
    from app.services import leasing, org_tree  # local import: avoids any import-order coupling

    node = org_tree.node_for(db, outlet_id)
    if node is None:
        return list_outlet_menus(db, outlet_id)
    stall_ids = [n.id for n in leasing.storefronts_at_venue(db, node, active_only=False)]
    if not stall_ids:
        return list_outlet_menus(db, outlet_id)
    by_id = {m.id: m for m in db.scalars(
        select(Menu).where(Menu.id.in_(stall_ids), Menu.is_active.is_(True))
    ).all()}
    ordered = [by_id[i] for i in stall_ids if i in by_id]   # house-then-leased (storefronts_at_venue order)
    return ordered or list_outlet_menus(db, outlet_id)


def direct_storefronts(db: Session, node) -> list[Menu]:
    """The stalls a node's QR Menu lists: its DIRECT sellable children (immediate, not nested under a
    sub-chain) PLUS any stall leased DIRECTLY into it (a venue's tenants). A Storefront → itself.
    Uniform for every node — to reach storefronts deeper down you open the sub-chain (same rule one
    level down). Only stalls that actually have a Menu (id == node id) are returned."""
    from app.models.leases import Lease
    from app.models.org import OrgNode

    if node.sells:
        ids = {node.id}
    else:
        ids = set(db.scalars(
            select(OrgNode.id).where(OrgNode.parent_id == node.id, OrgNode.sells.is_(True),
                                     OrgNode.is_active.is_(True))
        ).all())
        for tid in db.scalars(
            select(Lease.tenant_node_id).where(Lease.venue_id == node.id, Lease.is_active.is_(True))
        ).all():
            ids.add(tid)
    if not ids:
        return []
    return list(db.scalars(
        select(Menu).where(Menu.id.in_(ids), Menu.is_active.is_(True))
        .order_by(Menu.sort_order, Menu.stall_name)
    ).all())


def node_scope_stalls(db: Session, node) -> list[Menu]:
    """Menu-backed leaf stalls in a node's scope — its OWN sellable leaves (subtree) PLUS any stall
    leased into a venue within it. The whole-subtree set (used for menu-reachability validation +
    the venue QR resolver); the QR-Menu *display* uses `direct_storefronts` (direct children only).
    Only stalls that actually have a menu (id == node id) are returned."""
    from app.models.leases import Lease
    from app.models.org import OrgNode
    from app.services import org_tree

    ids = {n.id for n in org_tree.sellable_under(db, node, active_only=False)}
    sub = select(OrgNode.id).where(org_tree._subtree_filter(node.path))
    for tid in db.scalars(
        select(Lease.tenant_node_id).where(Lease.venue_id.in_(sub), Lease.is_active.is_(True))
    ).all():
        ids.add(tid)
    if not ids:
        return []
    return list(db.scalars(
        select(Menu).where(Menu.id.in_(ids), Menu.is_active.is_(True))
        .order_by(Menu.sort_order, Menu.stall_name)
    ).all())


def get_menu_full(db: Session, menu_id: str) -> Menu:
    """Full menu (categories+items+modifiers) by id — caller has already authorised scope."""
    menu = db.scalar(
        select(Menu).where(Menu.id == menu_id, Menu.is_active.is_(True)).options(_MENU_LOAD)
    )
    if not menu:
        raise NotFoundError("Stall menu not found", code="menu_not_found")
    return menu


def get_venue_stall_menu(db: Session, outlet_id: str, menu_id: str) -> Menu:
    """Full menu for a stall reachable AT this venue — its own stalls OR stalls leased in. The
    venue membership check (via the spine) replaces the strict same-outlet check so a leased-in
    menu (a different outlet/merchant) is reachable, while a foreign menu is still blocked. Falls
    back to the strict outlet-scoped check for collapsed/typed-only venues with no spine subtree."""
    from app.services import leasing, org_tree

    node = org_tree.node_for(db, outlet_id)
    if node is not None:
        stall_ids = {n.id for n in leasing.storefronts_at_venue(db, node, active_only=False)}
        if menu_id in stall_ids:
            menu = db.scalar(
                select(Menu).where(Menu.id == menu_id, Menu.is_active.is_(True)).options(_MENU_LOAD)
            )
            if menu:
                return menu
    return get_outlet_menu(db, outlet_id, menu_id)   # strict same-outlet fallback (also 404s foreign)


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


def create_category(db: Session, *, merchant_id: str, menu_id: str, name: str, sort_order: int = 0,
                    translations: dict | None = None) -> MenuCategory:
    _require_menu(db, menu_id, merchant_id)
    cat = MenuCategory(menu_id=menu_id, name=name, sort_order=sort_order, translations=translations)
    db.add(cat)
    db.flush()
    return cat


def update_category(db: Session, *, merchant_id: str, category_id: str, name=None, sort_order=None,
                    translations=None) -> MenuCategory:
    cat = _require_category(db, category_id, merchant_id)
    if name is not None:
        cat.name = name
    if sort_order is not None:
        cat.sort_order = sort_order
    if translations is not None:
        cat.translations = translations or None  # {} clears back to canonical-only
    db.flush()
    return cat


def delete_category(db: Session, *, merchant_id: str, category_id: str) -> None:
    db.delete(_require_category(db, category_id, merchant_id))
    db.flush()


def create_item(db: Session, *, merchant_id: str, category_id: str, name: str, price: Decimal | float,
                description: str = "", sort_order: int = 0, translations: dict | None = None) -> MenuItem:
    _require_category(db, category_id, merchant_id)
    item = MenuItem(category_id=category_id, name=name, price=money(price),
                    description=description, sort_order=sort_order, is_available=True,
                    translations=translations)
    db.add(item)
    db.flush()
    return item


def update_item(db: Session, *, merchant_id: str, item_id: str, name=None, price=None,
                description=None, is_available=None, sort_order=None, translations=None) -> MenuItem:
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
    if translations is not None:
        item.translations = translations or None
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
