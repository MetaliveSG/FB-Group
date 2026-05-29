"""Org-structure admin: Brands -> Outlets -> Tables/QR (Module 1 self-service)."""
from __future__ import annotations

import re
import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError
from app.models.catalog import Menu
from app.models.tenancy import Brand, DiningTable, Outlet, QRCode


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")[:24] or "x"


# --- validators ---------------------------------------------------------
def _require_brand(db: Session, merchant_id: str, brand_id: str) -> Brand:
    b = db.get(Brand, brand_id)
    if not b or b.merchant_id != merchant_id:
        raise NotFoundError("Brand not found", code="brand_not_found")
    return b


def _require_outlet(db: Session, merchant_id: str, outlet_id: str) -> Outlet:
    o = db.get(Outlet, outlet_id)
    if not o or o.merchant_id != merchant_id:
        raise NotFoundError("Outlet not found", code="outlet_not_found")
    return o


# --- Brands -------------------------------------------------------------
def list_brands(db: Session, *, merchant_id: str) -> list[dict]:
    rows = []
    for b in db.scalars(select(Brand).where(Brand.merchant_id == merchant_id).order_by(Brand.name)).all():
        outlets = db.scalar(select(func.count(Outlet.id)).where(Outlet.brand_id == b.id)) or 0
        rows.append({"id": b.id, "name": b.name, "cuisine_type": b.cuisine_type,
                     "is_active": b.is_active, "outlets": int(outlets)})
    return rows


def create_brand(db: Session, *, merchant_id: str, name: str, cuisine_type: str | None = None) -> Brand:
    b = Brand(merchant_id=merchant_id, name=name, cuisine_type=cuisine_type)
    db.add(b)
    db.flush()
    return b


def update_brand(db: Session, *, merchant_id: str, brand_id: str, name=None, cuisine_type=None, is_active=None) -> Brand:
    b = _require_brand(db, merchant_id, brand_id)
    if name is not None:
        b.name = name
    if cuisine_type is not None:
        b.cuisine_type = cuisine_type
    if is_active is not None:
        b.is_active = is_active
    db.flush()
    return b


# --- Outlets ------------------------------------------------------------
def list_outlets(db: Session, *, merchant_id: str) -> list[dict]:
    rows = []
    for o in db.scalars(select(Outlet).where(Outlet.merchant_id == merchant_id).order_by(Outlet.name)).all():
        tables = db.scalar(select(func.count(DiningTable.id)).where(DiningTable.outlet_id == o.id)) or 0
        menu = db.scalar(select(Menu).where(Menu.outlet_id == o.id, Menu.is_active.is_(True)))
        brand = db.get(Brand, o.brand_id)
        rows.append({"id": o.id, "name": o.name, "address": o.address, "is_active": o.is_active,
                     "brand_id": o.brand_id, "brand_name": brand.name if brand else None,
                     "tables": int(tables), "menu_id": menu.id if menu else None})
    return rows


def create_outlet(db: Session, *, merchant_id: str, brand_id: str, name: str, address: str | None = None) -> Outlet:
    brand = _require_brand(db, merchant_id, brand_id)
    outlet = Outlet(merchant_id=merchant_id, brand_id=brand.id, name=name, address=address)
    db.add(outlet)
    db.flush()
    # Auto-create an active menu so the Menu Editor works immediately.
    db.add(Menu(merchant_id=merchant_id, outlet_id=outlet.id, name="Main Menu", is_active=True))
    db.flush()
    return outlet


def update_outlet(db: Session, *, merchant_id: str, outlet_id: str, name=None, address=None, is_active=None) -> Outlet:
    o = _require_outlet(db, merchant_id, outlet_id)
    if name is not None:
        o.name = name
    if address is not None:
        o.address = address
    if is_active is not None:
        o.is_active = is_active
    db.flush()
    return o


# --- Tables + QR --------------------------------------------------------
def _gen_token(db: Session, outlet: Outlet, label: str) -> str:
    base = f"{_slug(outlet.name.split('—')[-1].strip())}-{_slug(label)}"
    token = base
    while db.scalar(select(QRCode).where(QRCode.token == token)):
        token = f"{base}-{secrets.token_hex(2)}"
    return token


def list_tables(db: Session, *, merchant_id: str, outlet_id: str) -> list[dict]:
    _require_outlet(db, merchant_id, outlet_id)
    rows = []
    for t in db.scalars(select(DiningTable).where(DiningTable.outlet_id == outlet_id).order_by(DiningTable.label)).all():
        qr = db.scalar(select(QRCode).where(QRCode.table_id == t.id))
        rows.append({"id": t.id, "label": t.label, "seats": t.seats, "is_active": t.is_active,
                     "qr_token": qr.token if qr else None})
    return rows


def create_table(db: Session, *, merchant_id: str, outlet_id: str, label: str, seats: int = 4) -> dict:
    outlet = _require_outlet(db, merchant_id, outlet_id)
    if db.scalar(select(DiningTable).where(DiningTable.outlet_id == outlet_id, DiningTable.label == label)):
        raise ConflictError("Table label already exists at this outlet", code="table_label_exists")
    table = DiningTable(merchant_id=merchant_id, outlet_id=outlet_id, label=label, seats=seats)
    db.add(table)
    db.flush()
    token = _gen_token(db, outlet, label)
    db.add(QRCode(merchant_id=merchant_id, outlet_id=outlet_id, table_id=table.id, token=token))
    db.flush()
    return {"id": table.id, "label": table.label, "seats": table.seats, "is_active": True, "qr_token": token}


def delete_table(db: Session, *, merchant_id: str, table_id: str) -> None:
    t = db.get(DiningTable, table_id)
    if not t or t.merchant_id != merchant_id:
        raise NotFoundError("Table not found", code="table_not_found")
    db.delete(t)  # cascades to its QR code
    db.flush()
