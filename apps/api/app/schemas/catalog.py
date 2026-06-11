"""Menu/catalog response + admin schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ModifierOut(ORMModel):
    id: str
    name: str
    price_delta: float


class MenuItemOut(ORMModel):
    id: str
    name: str
    description: str
    price: float
    image_url: str | None = None
    is_available: bool
    modifiers: list[ModifierOut] = []
    # Localisation override/cache {locale: {name, description}}. Present on the ADMIN/editor read (from
    # the ORM) so a merchant can edit per-locale; OMITTED on the customer read (the menu is already
    # localised server-side to one language → a lighter payload). See app/services/i18n.py.
    translations: dict | None = None


class MenuCategoryOut(ORMModel):
    id: str
    name: str
    sort_order: int
    items: list[MenuItemOut] = []
    translations: dict | None = None


class MenuOut(ORMModel):
    id: str
    name: str
    categories: list[MenuCategoryOut] = []


# --- Admin (CRUD) inputs ---
class CategoryCreateIn(BaseModel):
    menu_id: str
    name: str = Field(min_length=1, max_length=120)
    sort_order: int = 0
    translations: dict | None = None


class CategoryUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    sort_order: int | None = None
    translations: dict | None = None


class ItemCreateIn(BaseModel):
    category_id: str
    name: str = Field(min_length=1, max_length=160)
    price: float = Field(ge=0)
    description: str = Field(default="", max_length=400)
    sort_order: int = 0
    translations: dict | None = None


class ItemUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    price: float | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=400)
    is_available: bool | None = None
    sort_order: int | None = None
    translations: dict | None = None


class ModifierCreateIn(BaseModel):
    item_id: str
    name: str = Field(min_length=1, max_length=120)
    price_delta: float = 0
