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


class QrContextOut(BaseModel):
    qr_token: str
    merchant: _Ref
    brand: _Ref
    outlet: _OutletRef
    table: _TableRef
    menu: MenuOut
