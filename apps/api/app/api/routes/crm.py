"""Merchant CRM routes — customer list/profile, segments, tags, notes. Tenant-isolated."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_scope, require, resolve_merchant
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.schemas.crm import (
    ActivityCreateIn,
    ActivityOut,
    BulkOwnerIn,
    BulkResult,
    BulkTagIn,
    BulkTaskIn,
    CustomerMetricsOut,
    CustomerProfileOut,
    CustomerSummaryOut,
    NoteCreate,
    NoteOut,
    OpportunityCreateIn,
    OpportunityOut,
    OpportunityPatchIn,
    OwnerAssignIn,
    PipelineOut,
    TagCreate,
    TaskCreateIn,
    TaskOut,
    TaskPatchIn,
    TimelineEvent,
    WinbackLaunchIn,
    WinbackResult,
)
from app.services import activities as activities_service
from app.services import crm as crm_service
from app.services import opportunities as opp_service
from app.services import tasks as tasks_service
from app.services import winback as winback_service
from app.services.audit import record as audit_record

router = APIRouter(prefix="/crm", tags=["crm"])


@router.get("/customers", response_model=list[CustomerSummaryOut])
def list_customers(
    merchant_id: str | None = Query(default=None),
    segment: str | None = Query(default=None),
    search: str | None = Query(default=None),
    outlet_id: str | None = Query(default=None),
    scope=Depends(get_scope),
    db: Session = Depends(get_db),
):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.view", mid)
    items = crm_service.list_customers(
        db, merchant_id=mid, scope=scope, segment=segment, search=search, outlet_id=outlet_id
    )
    return [
        CustomerSummaryOut(
            id=it.customer.id, full_name=it.customer.full_name,
            email=it.customer.email, phone=it.customer.phone,
            tier=it.metrics.tier, lifecycle_stage=it.metrics.lifecycle_stage,
            total_spend=it.metrics.total_spend, avg_spend=it.metrics.avg_spend,
            visit_count=it.metrics.visit_count, points_balance=it.metrics.points_balance,
            last_visit_at=it.metrics.last_visit_at,
            days_since_last_visit=it.metrics.days_since_last_visit,
            churn_risk=it.metrics.churn_risk, churn_label=it.metrics.churn_label,
            segments=it.metrics.segments, tags=it.tags,
            owner_user_id=it.owner_user_id, owner_name=it.owner_name, open_tasks=it.open_tasks,
        )
        for it in items
    ]


@router.get("/segments", response_model=dict)
def segment_summary(
    merchant_id: str | None = Query(default=None),
    scope=Depends(get_scope),
    db: Session = Depends(get_db),
):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.view", mid)
    return crm_service.segment_summary(db, merchant_id=mid, scope=scope)


@router.get("/customers/{customer_id}", response_model=CustomerProfileOut)
def customer_profile(
    customer_id: str,
    merchant_id: str | None = Query(default=None),
    scope=Depends(get_scope),
    db: Session = Depends(get_db),
):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.view", mid)
    data = crm_service.get_profile(db, merchant_id=mid, customer_id=customer_id, scope=scope)
    return CustomerProfileOut(
        customer=data["customer"],
        metrics=CustomerMetricsOut.model_validate(data["metrics"]),
        orders=data["orders"],
        transactions=data["transactions"],
        rewards=data["rewards"],
        tags=data["tags"],
        notes=[NoteOut.model_validate(n) for n in data["notes"]],
        owner_user_id=data["owner_user_id"],
        owner_name=data["owner_name"],
        tasks=[TaskOut.model_validate(t) for t in data["tasks"]],
    )


@router.post("/customers/{customer_id}/tags", status_code=201)
def add_tag(
    customer_id: str, body: TagCreate,
    merchant_id: str | None = Query(default=None),
    scope=Depends(get_scope), db: Session = Depends(get_db),
):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.manage", mid)
    crm_service.add_tag(db, merchant_id=mid, customer_id=customer_id, tag=body.tag)
    audit_record(db, action="crm.tag_add", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="customer", entity_id=customer_id, meta={"tag": body.tag})
    db.commit()
    return {"message": "tag added"}


@router.post("/customers/{customer_id}/notes", response_model=NoteOut, status_code=201)
def add_note(
    customer_id: str, body: NoteCreate,
    merchant_id: str | None = Query(default=None),
    scope=Depends(get_scope), db: Session = Depends(get_db),
):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.manage", mid)
    note = crm_service.add_note(db, merchant_id=mid, customer_id=customer_id,
                                author_user_id=scope.user_id, body=body.body)
    db.commit()
    db.refresh(note)
    return NoteOut.model_validate(note)


# --- Activity timeline -------------------------------------------------
@router.get("/customers/{customer_id}/timeline", response_model=list[TimelineEvent])
def customer_timeline(customer_id: str, merchant_id: str | None = Query(default=None),
                      scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.view", mid)
    return crm_service.build_timeline(db, merchant_id=mid, customer_id=customer_id, scope=scope)


# --- Tasks / activities ------------------------------------------------
@router.get("/customers/{customer_id}/tasks", response_model=list[TaskOut])
def list_customer_tasks(customer_id: str, merchant_id: str | None = Query(default=None),
                        scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.view", mid)
    return [TaskOut.model_validate(t) for t in
            tasks_service.list_for_customer(db, merchant_id=mid, customer_id=customer_id)]


@router.post("/customers/{customer_id}/tasks", response_model=TaskOut, status_code=201)
def create_customer_task(customer_id: str, body: TaskCreateIn,
                         merchant_id: str | None = Query(default=None),
                         scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.manage", mid)
    if not crm_service._merchant_account(db, mid, customer_id):
        raise NotFoundError("Customer not found for this merchant", code="customer_not_found")
    task = tasks_service.create_task(
        db, merchant_id=mid, customer_id=customer_id, title=body.title, description=body.description,
        due_date=body.due_date, priority=body.priority,
        assignee_user_id=body.assignee_user_id or scope.user_id, created_by_user_id=scope.user_id)
    audit_record(db, action="crm.task_create", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="task", entity_id=task.id)
    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)


@router.patch("/tasks/{task_id}", response_model=TaskOut)
def update_task(task_id: str, body: TaskPatchIn, merchant_id: str | None = Query(default=None),
                scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.manage", mid)
    if body.status == "done":
        task = tasks_service.complete_task(db, merchant_id=mid, task_id=task_id)
    else:
        task = tasks_service.complete_task(db, merchant_id=mid, task_id=task_id)
        task.status = "open"
        task.completed_at = None
        db.flush()
    db.commit()
    db.refresh(task)
    return TaskOut.model_validate(task)


@router.get("/tasks", response_model=list[TaskOut])
def my_open_tasks(merchant_id: str | None = Query(default=None),
                  scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.view", mid)
    return [TaskOut.model_validate(t) for t in
            tasks_service.list_open_for_user(db, merchant_id=mid, user_id=scope.user_id)]


# --- Record owner ------------------------------------------------------
@router.put("/customers/{customer_id}/owner", status_code=200)
def assign_owner(customer_id: str, body: OwnerAssignIn, merchant_id: str | None = Query(default=None),
                 scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.manage", mid)
    crm_service.assign_owner(db, merchant_id=mid, customer_id=customer_id, owner_user_id=body.owner_user_id)
    audit_record(db, action="crm.owner_assign", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="customer", entity_id=customer_id, meta={"owner": body.owner_user_id})
    db.commit()
    return {"message": "owner assigned"}


# --- Opportunities / pipeline ------------------------------------------
@router.get("/pipeline", response_model=PipelineOut)
def pipeline(merchant_id: str | None = Query(default=None),
             pipeline_type: str = Query(default="sales", pattern="^(sales|winback)$"),
             scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.view", mid)
    return opp_service.pipeline(db, merchant_id=mid, pipeline_type=pipeline_type)


@router.get("/opportunities", response_model=list[OpportunityOut])
def list_opportunities(merchant_id: str | None = Query(default=None),
                       pipeline_type: str | None = Query(default=None),
                       scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.view", mid)
    return [OpportunityOut.model_validate(o)
            for o in opp_service.list_opportunities(db, merchant_id=mid, pipeline_type=pipeline_type)]


@router.get("/customers/{customer_id}/opportunities", response_model=list[OpportunityOut])
def customer_opportunities(customer_id: str, merchant_id: str | None = Query(default=None),
                           scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.view", mid)
    return [OpportunityOut.model_validate(o) for o in
            opp_service.list_for_customer(db, merchant_id=mid, customer_id=customer_id)]


@router.post("/customers/{customer_id}/opportunities", response_model=OpportunityOut, status_code=201)
def create_opportunity(customer_id: str, body: OpportunityCreateIn,
                       merchant_id: str | None = Query(default=None),
                       scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.manage", mid)
    if not crm_service._merchant_account(db, mid, customer_id):
        raise NotFoundError("Customer not found for this merchant", code="customer_not_found")
    opp = opp_service.create_opportunity(
        db, merchant_id=mid, customer_id=customer_id, name=body.name, amount=body.amount,
        pipeline_type=body.pipeline_type, stage=body.stage, expected_close_date=body.expected_close_date,
        owner_user_id=scope.user_id, created_by_user_id=scope.user_id)
    audit_record(db, action="crm.opportunity_create", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="opportunity", entity_id=opp.id)
    db.commit()
    db.refresh(opp)
    return OpportunityOut.model_validate(opp)


@router.patch("/opportunities/{opp_id}", response_model=OpportunityOut)
def update_opportunity(opp_id: str, body: OpportunityPatchIn,
                       merchant_id: str | None = Query(default=None),
                       scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.manage", mid)
    opp = opp_service.update_opportunity(db, merchant_id=mid, opp_id=opp_id, stage=body.stage, amount=body.amount)
    db.commit()
    db.refresh(opp)
    return OpportunityOut.model_validate(opp)


# --- Activity logging --------------------------------------------------
@router.get("/customers/{customer_id}/activities", response_model=list[ActivityOut])
def list_activities(customer_id: str, merchant_id: str | None = Query(default=None),
                    scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.view", mid)
    return [ActivityOut.model_validate(a) for a in
            activities_service.list_for_customer(db, merchant_id=mid, customer_id=customer_id)]


@router.post("/customers/{customer_id}/activities", response_model=ActivityOut, status_code=201)
def log_activity(customer_id: str, body: ActivityCreateIn,
                 merchant_id: str | None = Query(default=None),
                 scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.manage", mid)
    if not crm_service._merchant_account(db, mid, customer_id):
        raise NotFoundError("Customer not found for this merchant", code="customer_not_found")
    act = activities_service.log_activity(
        db, merchant_id=mid, customer_id=customer_id, activity_type=body.activity_type,
        subject=body.subject, body=body.body, occurred_at=body.occurred_at, logged_by_user_id=scope.user_id)
    db.commit()
    db.refresh(act)
    return ActivityOut.model_validate(act)


# --- Bulk actions ------------------------------------------------------
@router.post("/bulk/tag", response_model=BulkResult)
def bulk_tag(body: BulkTagIn, merchant_id: str | None = Query(default=None),
             scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.manage", mid)
    n = crm_service.bulk_add_tag(db, merchant_id=mid, scope=scope, tag=body.tag,
                                 customer_ids=body.customer_ids, segment=body.segment)
    audit_record(db, action="crm.bulk_tag", actor_id=scope.user_id, merchant_id=mid,
                 meta={"tag": body.tag, "count": n})
    db.commit()
    return BulkResult(affected=n)


@router.post("/bulk/owner", response_model=BulkResult)
def bulk_owner(body: BulkOwnerIn, merchant_id: str | None = Query(default=None),
               scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.manage", mid)
    n = crm_service.bulk_assign_owner(db, merchant_id=mid, scope=scope, owner_user_id=body.owner_user_id,
                                      customer_ids=body.customer_ids, segment=body.segment)
    audit_record(db, action="crm.bulk_owner", actor_id=scope.user_id, merchant_id=mid, meta={"count": n})
    db.commit()
    return BulkResult(affected=n)


@router.post("/bulk/task", response_model=BulkResult)
def bulk_task(body: BulkTaskIn, merchant_id: str | None = Query(default=None),
              scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.manage", mid)
    n = crm_service.bulk_create_task(db, merchant_id=mid, scope=scope, title=body.title, priority=body.priority,
                                     assignee_user_id=scope.user_id,
                                     customer_ids=body.customer_ids, segment=body.segment)
    audit_record(db, action="crm.bulk_task", actor_id=scope.user_id, merchant_id=mid,
                 meta={"title": body.title, "count": n})
    db.commit()
    return BulkResult(affected=n)


# --- Win-back launcher (RFM -> win-back pipeline -> campaign) -----------
@router.post("/winback", response_model=WinbackResult)
def launch_winback(body: WinbackLaunchIn, merchant_id: str | None = Query(default=None),
                   scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "crm.manage", mid)
    result = winback_service.launch(
        db, merchant_id=mid, owner_user_id=scope.user_id,
        customer_ids=body.customer_ids, rfm_segments=body.rfm_segments,
        create_campaign=body.create_campaign, message_template=body.message_template)
    audit_record(db, action="crm.winback_launch", actor_id=scope.user_id, merchant_id=mid, meta=result)
    db.commit()
    return WinbackResult(**result)
