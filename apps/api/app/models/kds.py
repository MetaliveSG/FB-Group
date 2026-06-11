"""Kitchen Display (KDS) station — a private, revocable per-outlet bearer token so a back-of-house
kitchen tablet runs `/kds` WITHOUT a web/email login or per-person password (the locked KDS auth model:
station binding, not a person). The token is SEPARATE from the public QR token (a diner's table QR can
never open the kitchen). Scoped to one outlet: view its open tickets + advance ticket status, nothing else.
Revoke = rotate (new token) or `is_active=False`."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, PKMixin, TimestampMixin


class KdsStation(PKMixin, TimestampMixin, Base):
    __tablename__ = "kds_stations"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    outlet_id: Mapped[str] = mapped_column(ForeignKey("outlets.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(48), unique=True, index=True, nullable=False)  # the bearer secret
    label: Mapped[str] = mapped_column(String(80), default="Kitchen")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column()  # touched on each authed request
