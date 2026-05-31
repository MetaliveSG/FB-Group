"""Point-multiplier promotion schemas (time-bound CAMPAIGN_MULTIPLIER rules)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class PromotionOut(BaseModel):
    id: str
    label: str
    multiplier: float
    starts_on: date | None = None
    ends_on: date | None = None
    is_active: bool


class PromotionCreateIn(BaseModel):
    label: str = Field(min_length=1, max_length=48)
    multiplier: float = Field(ge=1, le=10)   # 1 = no-op; cap keeps a typo from minting absurd points
    starts_on: date | None = None            # null = no start bound (active immediately)
    ends_on: date | None = None              # null = no end bound (runs until deactivated)
