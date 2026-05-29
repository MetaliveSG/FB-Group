"""Menu management (CRUD) — staff `menu.manage`, tenant + outlet scoped."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_scope, require, resolve_merchant
from app.core.errors import ForbiddenError
from app.db.session import get_db
from app.models.catalog import Menu, MenuCategory
from app.schemas.catalog import (
    CategoryCreateIn,
    CategoryUpdateIn,
    ItemCreateIn,
    ItemUpdateIn,
    MenuCategoryOut,
    MenuItemOut,
    ModifierCreateIn,
    ModifierOut,
)
from app.services import catalog as catalog_service
from app.services.audit import record as audit_record

router = APIRouter(prefix="/menu-admin", tags=["menu-admin"])


def _ctx(scope, merchant_id):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "menu.manage", mid)
    return mid


def _check_outlet(db, scope, mid, outlet_id):
    if outlet_id and not scope.can_view_outlet(mid, outlet_id):
        raise ForbiddenError("Outside your outlet scope", code="outlet_scope")


@router.get("/outlets")
def list_outlets(merchant_id: str | None = Query(None), scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _ctx(scope, merchant_id)
    rows = catalog_service.list_outlets_with_menu(db, merchant_id=mid)
    return [r for r in rows if scope.can_view_outlet(mid, r["outlet_id"])]


@router.post("/categories", response_model=MenuCategoryOut, status_code=201)
def create_category(body: CategoryCreateIn, merchant_id: str | None = Query(None),
                    scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _ctx(scope, merchant_id)
    _check_outlet(db, scope, mid, catalog_service.outlet_of_menu(db, body.menu_id))
    cat = catalog_service.create_category(db, merchant_id=mid, menu_id=body.menu_id,
                                          name=body.name, sort_order=body.sort_order)
    audit_record(db, action="menu.category_create", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="menu_category", entity_id=cat.id)
    db.commit()
    db.refresh(cat)
    return MenuCategoryOut.model_validate(cat)


@router.patch("/categories/{category_id}", response_model=MenuCategoryOut)
def update_category(category_id: str, body: CategoryUpdateIn, merchant_id: str | None = Query(None),
                    scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _ctx(scope, merchant_id)
    cat = catalog_service.update_category(db, merchant_id=mid, category_id=category_id,
                                          name=body.name, sort_order=body.sort_order)
    db.commit()
    db.refresh(cat)
    return MenuCategoryOut.model_validate(cat)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(category_id: str, merchant_id: str | None = Query(None),
                    scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _ctx(scope, merchant_id)
    catalog_service.delete_category(db, merchant_id=mid, category_id=category_id)
    db.commit()


def _outlet_of_category(db, category_id):
    cat = db.get(MenuCategory, category_id)
    menu = db.get(Menu, cat.menu_id) if cat else None
    return menu.outlet_id if menu else None


@router.post("/items", response_model=MenuItemOut, status_code=201)
def create_item(body: ItemCreateIn, merchant_id: str | None = Query(None),
                scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _ctx(scope, merchant_id)
    _check_outlet(db, scope, mid, _outlet_of_category(db, body.category_id))
    item = catalog_service.create_item(db, merchant_id=mid, category_id=body.category_id, name=body.name,
                                       price=body.price, description=body.description, sort_order=body.sort_order)
    audit_record(db, action="menu.item_create", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="menu_item", entity_id=item.id)
    db.commit()
    db.refresh(item)
    return MenuItemOut.model_validate(item)


@router.patch("/items/{item_id}", response_model=MenuItemOut)
def update_item(item_id: str, body: ItemUpdateIn, merchant_id: str | None = Query(None),
                scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _ctx(scope, merchant_id)
    item = catalog_service.update_item(db, merchant_id=mid, item_id=item_id, name=body.name, price=body.price,
                                       description=body.description, is_available=body.is_available,
                                       sort_order=body.sort_order)
    db.commit()
    db.refresh(item)
    return MenuItemOut.model_validate(item)


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: str, merchant_id: str | None = Query(None),
                scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _ctx(scope, merchant_id)
    catalog_service.delete_item(db, merchant_id=mid, item_id=item_id)
    db.commit()


@router.post("/modifiers", response_model=ModifierOut, status_code=201)
def create_modifier(body: ModifierCreateIn, merchant_id: str | None = Query(None),
                    scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _ctx(scope, merchant_id)
    mod = catalog_service.create_modifier(db, merchant_id=mid, item_id=body.item_id,
                                          name=body.name, price_delta=body.price_delta)
    db.commit()
    db.refresh(mod)
    return ModifierOut.model_validate(mod)


@router.delete("/modifiers/{modifier_id}", status_code=204)
def delete_modifier(modifier_id: str, merchant_id: str | None = Query(None),
                    scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _ctx(scope, merchant_id)
    catalog_service.delete_modifier(db, merchant_id=mid, modifier_id=modifier_id)
    db.commit()
