"""CRM response/request schemas."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, UtcDatetime


class CustomerMetricsOut(ORMModel):
    visit_count: int
    total_spend: float
    avg_spend: float
    points_balance: int
    lifetime_points: int
    tier: str
    first_visit_at: UtcDatetime | None = None
    last_visit_at: UtcDatetime | None = None
    days_since_last_visit: int | None = None
    visits_per_month: float
    churn_risk: float
    churn_label: str
    lifecycle_stage: str
    segments: list[str] = []


class CustomerSummaryOut(BaseModel):
    id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    tier: str
    lifecycle_stage: str
    total_spend: float
    avg_spend: float
    visit_count: int
    points_balance: int
    last_visit_at: UtcDatetime | None = None
    days_since_last_visit: int | None = None
    churn_risk: float
    churn_label: str
    segments: list[str] = []
    tags: list[str] = []
    owner_user_id: str | None = None
    owner_name: str | None = None
    open_tasks: int = 0


class TaskOut(ORMModel):
    id: str
    customer_id: str
    title: str
    description: str
    due_date: date | None = None
    status: str
    priority: str
    assignee_user_id: str | None = None
    created_at: UtcDatetime
    completed_at: UtcDatetime | None = None


class TaskCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    due_date: date | None = None
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")
    assignee_user_id: str | None = None


class TaskPatchIn(BaseModel):
    status: str = Field(pattern="^(open|done)$")


class OwnerAssignIn(BaseModel):
    owner_user_id: str | None = None


class TimelineEvent(BaseModel):
    ts: UtcDatetime
    type: str
    title: str
    detail: str = ""


_STAGE_RE = "^(prospecting|qualified|proposal|negotiation|won|lost|at_risk|contacted|offer_sent|recovered|churned)$"


# --- Opportunities / pipeline ---
class OpportunityOut(ORMModel):
    id: str
    customer_id: str
    name: str
    pipeline_type: str
    stage: str
    amount: float
    expected_close_date: date | None = None
    owner_user_id: str | None = None
    closed_at: UtcDatetime | None = None
    created_at: UtcDatetime


class OpportunityCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    amount: float = Field(default=0, ge=0)
    pipeline_type: str = Field(default="sales", pattern="^(sales|winback)$")
    stage: str | None = Field(default=None, pattern=_STAGE_RE)
    expected_close_date: date | None = None


class OpportunityPatchIn(BaseModel):
    stage: str | None = Field(default=None, pattern=_STAGE_RE)
    amount: float | None = Field(default=None, ge=0)


class PipelineStageOut(BaseModel):
    stage: str
    count: int
    value: float
    is_open: bool = True
    is_won: bool = False
    is_lost: bool = False


class PipelineOut(BaseModel):
    pipeline_type: str
    stages: list[PipelineStageOut]
    open_value: float
    won_value: float
    open_count: int


# --- Activity logging ---
class ActivityOut(ORMModel):
    id: str
    activity_type: str
    subject: str
    body: str
    occurred_at: UtcDatetime | None = None
    logged_by_user_id: str | None = None
    created_at: UtcDatetime


class ActivityCreateIn(BaseModel):
    activity_type: str = Field(pattern="^(call|email|meeting|whatsapp|note)$")
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=1000)
    occurred_at: UtcDatetime | None = None


# --- Bulk actions ---
class BulkTagIn(BaseModel):
    tag: str = Field(min_length=1, max_length=48)
    customer_ids: list[str] | None = None
    segment: str | None = None


class BulkOwnerIn(BaseModel):
    owner_user_id: str | None = None
    customer_ids: list[str] | None = None
    segment: str | None = None


class BulkTaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")
    customer_ids: list[str] | None = None
    segment: str | None = None


class BulkResult(BaseModel):
    affected: int


# --- Win-back launcher (RFM -> pipeline -> campaign) ---
class WinbackLaunchIn(BaseModel):
    customer_ids: list[str] | None = None
    rfm_segments: list[str] | None = None
    create_campaign: bool = False
    message_template: str | None = None


class WinbackResult(BaseModel):
    targets: int
    opportunities_created: int
    campaign_id: str | None = None
    campaign_delivered: int = 0


class _CustomerCore(ORMModel):
    id: str
    full_name: str
    email: str | None = None
    phone: str | None = None
    birthday: date | None = None


class OrderItemOut(ORMModel):
    name_snapshot: str
    unit_price: float
    quantity: int
    line_total: float
    modifiers: list = []


class OrderHistoryItem(ORMModel):
    id: str
    outlet_id: str
    channel: str
    status: str
    subtotal: float = 0.0
    service_charge: float = 0.0
    tax: float = 0.0
    total: float
    items: list[OrderItemOut] = []
    created_at: UtcDatetime


class TransactionHistoryItem(ORMModel):
    id: str
    amount: float
    method: str = ""
    status: str = ""
    points_earned: int = 0
    created_at: UtcDatetime


class RewardHistoryItem(ORMModel):
    txn_type: str
    points: int
    reason: str
    rule_code: str | None = None
    created_at: UtcDatetime


class NoteOut(ORMModel):
    id: str
    body: str
    author_user_id: str | None = None
    created_at: UtcDatetime


class CustomerProfileOut(BaseModel):
    customer: _CustomerCore
    metrics: CustomerMetricsOut
    orders: list[OrderHistoryItem] = []
    transactions: list[TransactionHistoryItem] = []
    rewards: list[RewardHistoryItem] = []
    tags: list[str] = []
    notes: list[NoteOut] = []
    owner_user_id: str | None = None
    owner_name: str | None = None
    tasks: list[TaskOut] = []


class TagCreate(BaseModel):
    tag: str = Field(min_length=1, max_length=48)


class NoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=1000)
