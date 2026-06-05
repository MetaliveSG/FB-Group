"""Campaign schemas."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, UtcDatetime

CampaignTypeLit = Literal[
    "whatsapp_promo", "birthday", "winback", "weekday_boost", "new_customer_return", "vip_reward",
    "voucher",
]


class VoucherConfigIn(BaseModel):
    """Vouchers a campaign issues to its audience (the granted-voucher issuer)."""
    value: float = Field(ge=0)                    # $ off per voucher
    count: int = Field(default=1, ge=1, le=100)   # vouchers per customer
    per_period: Literal["day", "week", "month"] | None = None
    valid_days: int | None = Field(default=None, ge=1, le=3650)
    name: str | None = Field(default=None, max_length=120)


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
    scope_node_id: str | None = None        # member-tree node this campaign reaches (subtree); None = tenant-wide
    voucher: VoucherConfigIn | None = None  # if set, the campaign can issue these vouchers to its audience
    starts_at: UtcDatetime | None = None
    ends_at: UtcDatetime | None = None


class CampaignOut(ORMModel):
    id: str
    name: str
    campaign_type: str
    segment_key: str | None = None
    message_template: str
    reward_points: int
    scope_node_id: str | None = None
    is_active: bool
    starts_at: UtcDatetime | None = None
    ends_at: UtcDatetime | None = None
    created_at: UtcDatetime


class CampaignListItemOut(BaseModel):
    id: str
    name: str
    campaign_type: str
    segment_key: str | None = None
    is_active: bool
    created_at: UtcDatetime
    metrics: CampaignMetricsOut


class MessageOut(ORMModel):
    id: str
    customer_id: str
    to_address: str
    body: str
    status: str
    provider_ref: str | None = None
    attempts: int
    created_at: UtcDatetime


class CampaignDetailOut(BaseModel):
    campaign: CampaignOut
    metrics: CampaignMetricsOut
    messages: list[MessageOut] = []


class AudienceResult(BaseModel):
    audience_size: int


class VoucherIssueResult(BaseModel):
    issued: int


class SendResultOut(BaseModel):
    delivered: int
    failed: int
    audience: int


class RedemptionIn(BaseModel):
    customer_id: str
    revenue: float = Field(default=0, ge=0)
    order_id: str | None = None
