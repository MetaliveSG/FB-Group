"""QR dining-context response."""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.catalog import MenuOut


class _Ref(BaseModel):
    id: str
    name: str


class _TableRef(BaseModel):
    id: str
    label: str


class _OutletRef(BaseModel):
    id: str
    name: str
    address: str | None = None


class StallRef(BaseModel):
    menu_id: str
    stall_name: str
    cuisine: str | None = None
    logo: str | None = None
    is_open: bool = True
    item_count: int = 0


class QrContextOut(BaseModel):
    qr_token: str
    merchant: _Ref
    brand: _Ref
    outlet: _OutletRef
    table: _TableRef
    # Foodcourt: an outlet may host many stalls (menus). `stalls` always lists them;
    # `is_foodcourt` = len(stalls) > 1. `menu` is the full single menu (single-stall /
    # restaurant — backward compat); null for a foodcourt (fetch one via /qr/{t}/menu/{id}).
    is_foodcourt: bool = False
    stalls: list[StallRef] = []
    menu: MenuOut | None = None
