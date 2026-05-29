"""Campaign schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel

CampaignTypeLit = Literal[
    "whatsapp_promo", "birthday", "winback", "weekday_boost", "new_customer_return", "vip_reward"
]


class CampaignMetricsOut(BaseModel):
    audience: int
    sent: int
    delivered: int
    failed: int
    redeemed: int
    revenue_generated: float
    conversion_rate: float
    cost: float
    roi: float


class CampaignCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    campaign_type: CampaignTypeLit
    segment_key: str | None = None
    message_template: str = Field(default="", max_length=1000)
    reward_points: int = Field(default=0, ge=0)
    starts_at: datetime | None = None
    ends_at: datetime | None = None


class CampaignOut(ORMModel):
    id: str
    name: str
    campaign_type: str
    segment_key: str | None = None
    message_template: str
    reward_points: int
    is_active: bool
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    created_at: datetime


class CampaignListItemOut(BaseModel):
    id: str
    name: str
    campaign_type: str
    segment_key: str | None = None
    is_active: bool
    created_at: datetime
    metrics: CampaignMetricsOut


class MessageOut(ORMModel):
    id: str
    customer_id: str
    to_address: str
    body: str
    status: str
    provider_ref: str | None = None
    attempts: int
    created_at: datetime


class CampaignDetailOut(BaseModel):
    campaign: CampaignOut
    metrics: CampaignMetricsOut
    messages: list[MessageOut] = []


class AudienceResult(BaseModel):
    audience_size: int


class SendResultOut(BaseModel):
    delivered: int
    failed: int
    audience: int


class RedemptionIn(BaseModel):
    customer_id: str
    revenue: float = Field(default=0, ge=0)
    order_id: str | None = None
