"""Menu catalog: Menu -> MenuCategory -> MenuItem -> MenuModifier."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import JSON, Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, PKMixin, TimestampMixin


class Menu(PKMixin, TimestampMixin, Base):
    __tablename__ = "menus"

    merchant_id: Mapped[str] = mapped_column(ForeignKey("merchants.id", ondelete="CASCADE"), index=True)
    outlet_id: Mapped[str] = mapped_column(ForeignKey("outlets.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), default="Main Menu")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Foodcourt support: a Menu IS a stall. An outlet may have N active menus (stalls);
    # a single-stall outlet/restaurant just has one. These describe the stall in the
    # stall directory (null on plain single-menu outlets → they skip the directory).
    stall_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cuisine: Mapped[str | None] = mapped_column(String(80), nullable=True)
    logo: Mapped[str | None] = mapped_column(String(16), nullable=True)  # emoji
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_open: Mapped[bool] = mapped_column(Boolean, default=True)

    categories: Mapped[list["MenuCategory"]] = relationship(
        back_populates="menu", cascade="all, delete-orphan", order_by="MenuCategory.sort_order"
    )


class MenuCategory(PKMixin, TimestampMixin, Base):
    __tablename__ = "menu_categories"

    menu_id: Mapped[str] = mapped_column(ForeignKey("menus.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # i18n: `name` is the CANONICAL locale (source of truth). `translations` is an OPTIONAL override/cache
    # layer keyed by locale → {"name": ...} (Grab pattern: author once, present many, fall back to canonical
    # when a locale is missing). May hold merchant-entered overrides OR machine-translation cache. NULL = no
    # translations → always shows `name`. Localised at read by app/services/i18n.py.
    translations: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    menu: Mapped["Menu"] = relationship(back_populates="categories")
    items: Mapped[list["MenuItem"]] = relationship(
        back_populates="category", cascade="all, delete-orphan", order_by="MenuItem.sort_order"
    )


class MenuItem(PKMixin, TimestampMixin, Base):
    __tablename__ = "menu_items"

    category_id: Mapped[str] = mapped_column(ForeignKey("menu_categories.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(String(400), default="")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(400), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # i18n override/cache layer keyed by locale → {"name": ..., "description": ...}; canonical = `name`/
    # `description`. Missing locale or key → falls back to canonical. See MenuCategory.translations + i18n.py.
    translations: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    category: Mapped["MenuCategory"] = relationship(back_populates="items")
    modifiers: Mapped[list["MenuModifier"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class MenuModifier(PKMixin, Base):
    """Optional add-on/customization for an item (e.g. 'Extra cheese' +$1.00)."""

    __tablename__ = "menu_modifiers"

    item_id: Mapped[str] = mapped_column(ForeignKey("menu_items.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    price_delta: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))

    item: Mapped["MenuItem"] = relationship(back_populates="modifiers")
