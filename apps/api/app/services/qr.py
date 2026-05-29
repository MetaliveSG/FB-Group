"""QR token resolution -> merchant/brand/outlet/table dining context."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.models.tenancy import QRCode


def resolve_token(db: Session, token: str) -> QRCode:
    qr = db.scalar(select(QRCode).where(QRCode.token == token))
    if not qr or not qr.is_active:
        raise NotFoundError("Invalid or inactive QR code", code="invalid_qr")
    return qr
