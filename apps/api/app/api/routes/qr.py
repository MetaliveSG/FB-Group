"""Public QR resolution -> dining context + outlet menu (no auth, no app download)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.tenancy import Brand, DiningTable, Merchant, Outlet
from app.schemas.catalog import MenuOut
from app.schemas.qr import QrContextOut, StallRef
from app.services import catalog as catalog_service
from app.services import qr as qr_service

router = APIRouter(prefix="/qr", tags=["qr"])


@router.get("/{token}", response_model=QrContextOut)
def resolve_qr(token: str, db: Session = Depends(get_db)):
    qr = qr_service.resolve_token(db, token)
    merchant = db.get(Merchant, qr.merchant_id)
    outlet = db.get(Outlet, qr.outlet_id)
    brand = db.get(Brand, outlet.brand_id)
    table = db.get(DiningTable, qr.table_id)

    # An outlet may host many stalls (menus). One → restaurant (inline menu, backward
    # compat); many → foodcourt (stall directory, fetch a menu on tap).
    menus = catalog_service.list_outlet_menus(db, qr.outlet_id)
    is_foodcourt = len(menus) > 1
    stalls = [
        StallRef(
            menu_id=m.id,
            stall_name=m.stall_name or m.name,
            cuisine=m.cuisine,
            logo=m.logo,
            is_open=m.is_open,
            item_count=catalog_service.menu_item_count(db, m.id),
        )
        for m in menus
    ]
    inline_menu = None
    if not is_foodcourt and menus:
        inline_menu = MenuOut.model_validate(catalog_service.get_outlet_menu(db, qr.outlet_id, menus[0].id))

    return QrContextOut(
        qr_token=qr.token,
        merchant={"id": merchant.id, "name": merchant.name},
        brand={"id": brand.id, "name": brand.name},
        outlet={"id": outlet.id, "name": outlet.name, "address": outlet.address},
        table={"id": table.id, "label": table.label},
        is_foodcourt=is_foodcourt,
        stalls=stalls,
        menu=inline_menu,
    )


@router.get("/{token}/menu/{menu_id}", response_model=MenuOut)
def resolve_stall_menu(token: str, menu_id: str, db: Session = Depends(get_db)):
    """Full menu for one stall — validated to belong to the token's own outlet, so a QR
    code can never reach a menu at a different outlet."""
    qr = qr_service.resolve_token(db, token)
    menu = catalog_service.get_outlet_menu(db, qr.outlet_id, menu_id)
    return MenuOut.model_validate(menu)
