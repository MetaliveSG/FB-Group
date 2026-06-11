"""Multi-tenant hierarchy: Merchant -> Brand -> Outlet -> Table -> QRCode.

`merchant_id` is denormalized onto descendant rows so tenant-isolation filters
are a single indexed predicate everywhere.
"""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKMixin, TimestampMixin


class Merchant(PKMixin, TimestampMixin, Base):
    __tablename__ = "merchants"

    name: Mapped[str] = mapped_column(String(160), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(2), default="SG")
    # The settlement currency for this tenant (a SETTLEMENT fact — money never crosses boundaries in MVP, so
    # one currency per merchant; FX deferred to the M2 coalition ring). ISO 4217 alpha-3. Display formatting
    # (incl. 0-decimal currencies like IDR/VND) is done at the edge via Intl.NumberFormat(locale,{currency}) —
    # backend stays Decimal and never hardcodes "$" or 2 dp. Default SGD (SG-first).
    currency: Mapped[str] = mapped_column(String(3), default="SGD", server_default="SGD", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # feature toggles + tenant defaults; `settings["locale"]` = the tenant's default UI language (menu
    # fallback when a diner has no locale), `settings["timezone"]` = report tz. See app/services/i18n.py.
    settings: Mapped[dict] = mapped_column(JSON, default=dict)

    brands: Mapped[list["Brand"]] = relationship(back_populates="merchant", cascade="all, delete-orphan")


class Brand(PKMixin, TimestampMixin, Base):
    __tablename__ = "brands"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    cuisine_type: Mapped[str | None] = mapped_column(String(80))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    merchant: Mapped["Merchant"] = relationship(back_populates="brands")
    outlets: Mapped[list["Outlet"]] = relationship(back_populates="brand", cascade="all, delete-orphan")


class Outlet(PKMixin, TimestampMixin, Base):
    __tablename__ = "outlets"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    brand_id: Mapped[str] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(40), default="Asia/Singapore")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    brand: Mapped["Brand"] = relationship(back_populates="outlets")
    tables: Mapped[list["DiningTable"]] = relationship(back_populates="outlet", cascade="all, delete-orphan")


class DiningTable(PKMixin, TimestampMixin, Base):
    __tablename__ = "tables"
    __table_args__ = (UniqueConstraint("outlet_id", "label", name="uq_table_outlet_label"),)

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    outlet_id: Mapped[str] = mapped_column(ForeignKey("outlets.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. "A12"
    seats: Mapped[int] = mapped_column(default=4)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    outlet: Mapped["Outlet"] = relationship(back_populates="tables")
    qr_code: Mapped["QRCode | None"] = relationship(back_populates="table", uselist=False, cascade="all, delete-orphan")


class QRCode(PKMixin, TimestampMixin, Base):
    __tablename__ = "qr_codes"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    outlet_id: Mapped[str] = mapped_column(ForeignKey("outlets.id", ondelete="CASCADE"), index=True)
    table_id: Mapped[str] = mapped_column(ForeignKey("tables.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(48), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    table: Mapped["DiningTable"] = relationship(back_populates="qr_code")
