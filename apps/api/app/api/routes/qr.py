"""Public QR resolution -> dining context + outlet menu (no auth, no app download)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.tenancy import Brand, DiningTable, Merchant, Outlet
from app.schemas.catalog import MenuOut
from app.schemas.qr import QrContextOut
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
    menu = catalog_service.get_active_menu(db, qr.outlet_id)
    return QrContextOut(
        qr_token=qr.token,
        merchant={"id": merchant.id, "name": merchant.name},
        brand={"id": brand.id, "name": brand.name},
        outlet={"id": outlet.id, "name": outlet.name, "address": outlet.address},
        table={"id": table.id, "label": table.label},
        menu=MenuOut.model_validate(menu),
    )
