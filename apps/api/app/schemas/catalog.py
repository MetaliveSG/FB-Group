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
    is_available: bool
    modifiers: list[ModifierOut] = []


class MenuCategoryOut(ORMModel):
    id: str
    name: str
    sort_order: int
    items: list[MenuItemOut] = []


class MenuOut(ORMModel):
    id: str
    name: str
    categories: list[MenuCategoryOut] = []


# --- Admin (CRUD) inputs ---
class CategoryCreateIn(BaseModel):
    menu_id: str
    name: str = Field(min_length=1, max_length=120)
    sort_order: int = 0


class CategoryUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    sort_order: int | None = None


class ItemCreateIn(BaseModel):
    category_id: str
    name: str = Field(min_length=1, max_length=160)
    price: float = Field(ge=0)
    description: str = Field(default="", max_length=400)
    sort_order: int = 0


class ItemUpdateIn(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    price: float | None = Field(default=None, ge=0)
    description: str | None = Field(default=None, max_length=400)
    is_available: bool | None = None
    sort_order: int | None = None


class ModifierCreateIn(BaseModel):
    item_id: str
    name: str = Field(min_length=1, max_length=120)
    price_delta: float = 0
