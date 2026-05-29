"""CRM service — tenant-isolated customer list/profile, histories, tags, notes.

Isolation invariant: every query is filtered by `merchant_id` and (when the user
is outlet/brand-scoped) restricted to customers who transacted at allowed outlets.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.crm import CustomerMetrics, compute_metrics
from app.auth.access import ALL_OUTLETS, Scope
from app.core.errors import ConflictError, NotFoundError
from app.db.base import utcnow
from app.models.crm import CustomerNote, CustomerTag
from app.models.engagement import CrmTask, CustomerActivity, Opportunity
from app.models.enums import RewardScope
from app.models.identity import Customer, User
from app.models.loyalty import LoyaltyAccount, RewardTransaction
from app.models.orders import Order
from app.models.payments import Transaction
from app.services import tasks as tasks_service


@dataclass
class CustomerListItem:
    customer: Customer
    metrics: CustomerMetrics
    tags: list[str]
    owner_user_id: str | None = None
    owner_name: str | None = None
    open_tasks: int = 0


def _merchant_account(db: Session, merchant_id: str, customer_id: str) -> LoyaltyAccount | None:
    return db.scalar(
        select(LoyaltyAccount).where(
            LoyaltyAccount.scope_type == RewardScope.MERCHANT.value,
            LoyaltyAccount.scope_id == merchant_id,
            LoyaltyAccount.customer_id == customer_id,
        )
    )


def _allowed_outlets(scope: Scope, merchant_id: str, outlet_id: str | None):
    """Return None (no restriction) or a set of outlet ids to restrict to."""
    limit = scope.outlet_limit(merchant_id)
    base = None if limit is ALL_OUTLETS else set(limit)  # type: ignore[arg-type]
    if outlet_id:
        base = {outlet_id} if base is None else (base & {outlet_id})
    return base


def _customer_outlets(db: Session, merchant_id: str, customer_id: str) -> set[str]:
    rows = db.scalars(
        select(Transaction.outlet_id).where(
            Transaction.merchant_id == merchant_id, Transaction.customer_id == customer_id
        )
    ).all()
    return set(rows)


def list_customers(
    db: Session,
    *,
    merchant_id: str,
    scope: Scope,
    segment: str | None = None,
    search: str | None = None,
    outlet_id: str | None = None,
) -> list[CustomerListItem]:
    allowed = _allowed_outlets(scope, merchant_id, outlet_id)
    accounts = db.scalars(
        select(LoyaltyAccount).where(
            LoyaltyAccount.scope_type == RewardScope.MERCHANT.value,
            LoyaltyAccount.scope_id == merchant_id,
        )
    ).all()

    now = utcnow()
    open_counts = tasks_service.open_counts_by_customer(db, merchant_id=merchant_id)
    owner_ids = {a.owner_user_id for a in accounts if a.owner_user_id}
    owner_names: dict[str, str] = {}
    if owner_ids:
        for u in db.scalars(select(User).where(User.id.in_(owner_ids))).all():
            owner_names[u.id] = u.full_name or u.email

    items: list[CustomerListItem] = []
    for acct in accounts:
        customer = db.get(Customer, acct.customer_id)
        if not customer:
            continue
        if allowed is not None:
            if not (_customer_outlets(db, merchant_id, customer.id) & allowed):
                continue
        metrics = compute_metrics(acct, customer, now)
        if segment and segment not in metrics.segments and segment != "all":
            continue
        if search:
            hay = f"{customer.full_name} {customer.email or ''} {customer.phone or ''}".lower()
            if search.lower() not in hay:
                continue
        tags = db.scalars(
            select(CustomerTag.tag).where(
                CustomerTag.merchant_id == merchant_id, CustomerTag.customer_id == customer.id
            )
        ).all()
        items.append(CustomerListItem(
            customer=customer, metrics=metrics, tags=list(tags),
            owner_user_id=acct.owner_user_id,
            owner_name=owner_names.get(acct.owner_user_id) if acct.owner_user_id else None,
            open_tasks=open_counts.get(customer.id, 0),
        ))

    items.sort(key=lambda i: i.metrics.total_spend, reverse=True)
    return items


def segment_summary(db: Session, *, merchant_id: str, scope: Scope) -> dict[str, int]:
    items = list_customers(db, merchant_id=merchant_id, scope=scope)
    counts: dict[str, int] = {"total": len(items)}
    for it in items:
        for seg in it.metrics.segments:
            counts[seg] = counts.get(seg, 0) + 1
    return counts


def get_profile(db: Session, *, merchant_id: str, customer_id: str, scope: Scope) -> dict:
    acct = _merchant_account(db, merchant_id, customer_id)
    customer = db.get(Customer, customer_id)
    if not acct or not customer:
        raise NotFoundError("Customer not found for this merchant", code="customer_not_found")

    allowed = _allowed_outlets(scope, merchant_id, None)
    if allowed is not None and not (_customer_outlets(db, merchant_id, customer_id) & allowed):
        raise NotFoundError("Customer not in your outlet scope", code="customer_not_found")

    metrics = compute_metrics(acct, customer, utcnow())

    orders = db.scalars(
        select(Order).where(Order.merchant_id == merchant_id, Order.customer_id == customer_id)
        .order_by(Order.created_at.desc()).limit(50)
    ).all()
    txns = db.scalars(
        select(Transaction).where(
            Transaction.merchant_id == merchant_id, Transaction.customer_id == customer_id
        ).order_by(Transaction.created_at.desc()).limit(50)
    ).all()
    # method/status live on the linked Payment, not the ledger Transaction.
    txn_history = [
        {
            "id": t.id,
            "amount": float(t.amount),
            "method": t.payment.method if t.payment else "",
            "status": t.payment.status if t.payment else "",
            "points_earned": t.points_earned,
            "created_at": t.created_at,
        }
        for t in txns
    ]
    rewards = db.scalars(
        select(RewardTransaction).where(RewardTransaction.account_id == acct.id)
        .order_by(RewardTransaction.created_at.desc()).limit(50)
    ).all()
    tags = db.scalars(
        select(CustomerTag.tag).where(
            CustomerTag.merchant_id == merchant_id, CustomerTag.customer_id == customer_id
        )
    ).all()
    notes = db.scalars(
        select(CustomerNote).where(
            CustomerNote.merchant_id == merchant_id, CustomerNote.customer_id == customer_id
        ).order_by(CustomerNote.created_at.desc())
    ).all()

    owner_name = None
    if acct.owner_user_id:
        owner = db.get(User, acct.owner_user_id)
        owner_name = (owner.full_name or owner.email) if owner else None
    crm_tasks = tasks_service.list_for_customer(db, merchant_id=merchant_id, customer_id=customer_id)

    return {
        "customer": customer,
        "metrics": metrics,
        "orders": orders,
        "transactions": txn_history,
        "rewards": rewards,
        "tags": list(tags),
        "notes": notes,
        "owner_user_id": acct.owner_user_id,
        "owner_name": owner_name,
        "tasks": crm_tasks,
    }


def assign_owner(db: Session, *, merchant_id: str, customer_id: str, owner_user_id: str | None) -> None:
    acct = _merchant_account(db, merchant_id, customer_id)
    if not acct:
        raise NotFoundError("Customer not found for this merchant", code="customer_not_found")
    acct.owner_user_id = owner_user_id
    db.flush()


def build_timeline(db: Session, *, merchant_id: str, customer_id: str, scope: Scope) -> list[dict]:
    """Unified, chronological activity feed (Salesforce-style) for one customer."""
    acct = _merchant_account(db, merchant_id, customer_id)
    if not acct:
        raise NotFoundError("Customer not found for this merchant", code="customer_not_found")

    events: list[dict] = []

    for o in db.scalars(select(Order).where(
            Order.merchant_id == merchant_id, Order.customer_id == customer_id)).all():
        events.append({"ts": o.placed_at or o.created_at, "type": "order",
                       "title": "Order placed", "detail": f"${float(o.total):.2f} · {o.channel} · {o.status}"})
    for t in db.scalars(select(Transaction).where(
            Transaction.merchant_id == merchant_id, Transaction.customer_id == customer_id)).all():
        events.append({"ts": t.created_at, "type": "payment",
                       "title": "Payment", "detail": f"${float(t.amount):.2f} · +{t.points_earned} pts"})
    for r in db.scalars(select(RewardTransaction).where(RewardTransaction.account_id == acct.id)).all():
        events.append({"ts": r.created_at, "type": f"reward_{r.txn_type}",
                       "title": f"Points {r.txn_type}", "detail": f"{r.points:+d} · {r.reason}"})
    for n in db.scalars(select(CustomerNote).where(
            CustomerNote.merchant_id == merchant_id, CustomerNote.customer_id == customer_id)).all():
        events.append({"ts": n.created_at, "type": "note", "title": "Note", "detail": n.body})
    for tk in db.scalars(select(CrmTask).where(
            CrmTask.merchant_id == merchant_id, CrmTask.customer_id == customer_id)).all():
        events.append({"ts": tk.created_at, "type": "task",
                       "title": f"Task created: {tk.title}", "detail": f"priority {tk.priority} · {tk.status}"})
        if tk.completed_at:
            events.append({"ts": tk.completed_at, "type": "task_done",
                           "title": f"Task completed: {tk.title}", "detail": ""})
    for op in db.scalars(select(Opportunity).where(
            Opportunity.merchant_id == merchant_id, Opportunity.customer_id == customer_id)).all():
        events.append({"ts": op.created_at, "type": "opportunity",
                       "title": f"Opportunity: {op.name}",
                       "detail": f"${float(op.amount):.2f} · {op.stage}"})
    for ac in db.scalars(select(CustomerActivity).where(
            CustomerActivity.merchant_id == merchant_id, CustomerActivity.customer_id == customer_id)).all():
        events.append({"ts": ac.occurred_at or ac.created_at, "type": f"activity_{ac.activity_type}",
                       "title": f"{ac.activity_type.title()}: {ac.subject}", "detail": ac.body})

    events = [e for e in events if e["ts"] is not None]
    events.sort(key=lambda e: e["ts"], reverse=True)
    return events


# --- Bulk actions (mass tag / owner / task over ids or a segment) -------
def resolve_customer_ids(db: Session, *, merchant_id: str, scope: Scope,
                         customer_ids: list[str] | None = None, segment: str | None = None) -> list[str]:
    if segment:
        return [it.customer.id for it in list_customers(db, merchant_id=merchant_id, scope=scope, segment=segment)]
    ids = []
    for cid in (customer_ids or []):
        if _merchant_account(db, merchant_id, cid):
            ids.append(cid)
    return ids


def bulk_add_tag(db: Session, *, merchant_id: str, scope: Scope, tag: str,
                 customer_ids: list[str] | None = None, segment: str | None = None) -> int:
    n = 0
    for cid in resolve_customer_ids(db, merchant_id=merchant_id, scope=scope, customer_ids=customer_ids, segment=segment):
        exists = db.scalar(select(CustomerTag).where(
            CustomerTag.merchant_id == merchant_id, CustomerTag.customer_id == cid, CustomerTag.tag == tag))
        if not exists:
            db.add(CustomerTag(merchant_id=merchant_id, customer_id=cid, tag=tag))
            n += 1
    db.flush()
    return n


def bulk_assign_owner(db: Session, *, merchant_id: str, scope: Scope, owner_user_id: str | None,
                      customer_ids: list[str] | None = None, segment: str | None = None) -> int:
    n = 0
    for cid in resolve_customer_ids(db, merchant_id=merchant_id, scope=scope, customer_ids=customer_ids, segment=segment):
        acct = _merchant_account(db, merchant_id, cid)
        if acct:
            acct.owner_user_id = owner_user_id
            n += 1
    db.flush()
    return n


def bulk_create_task(db: Session, *, merchant_id: str, scope: Scope, title: str, priority: str = "normal",
                     assignee_user_id: str | None = None,
                     customer_ids: list[str] | None = None, segment: str | None = None) -> int:
    ids = resolve_customer_ids(db, merchant_id=merchant_id, scope=scope, customer_ids=customer_ids, segment=segment)
    for cid in ids:
        tasks_service.create_task(db, merchant_id=merchant_id, customer_id=cid, title=title,
                                  priority=priority, assignee_user_id=assignee_user_id,
                                  created_by_user_id=assignee_user_id)
    db.flush()
    return len(ids)


def add_tag(db: Session, *, merchant_id: str, customer_id: str, tag: str) -> None:
    if not _merchant_account(db, merchant_id, customer_id):
        raise NotFoundError("Customer not found for this merchant", code="customer_not_found")
    exists = db.scalar(
        select(CustomerTag).where(
            CustomerTag.merchant_id == merchant_id,
            CustomerTag.customer_id == customer_id,
            CustomerTag.tag == tag,
        )
    )
    if exists:
        raise ConflictError("Tag already exists", code="tag_exists")
    db.add(CustomerTag(merchant_id=merchant_id, customer_id=customer_id, tag=tag))
    db.flush()


def add_note(db: Session, *, merchant_id: str, customer_id: str, author_user_id: str, body: str) -> CustomerNote:
    if not _merchant_account(db, merchant_id, customer_id):
        raise NotFoundError("Customer not found for this merchant", code="customer_not_found")
    note = CustomerNote(merchant_id=merchant_id, customer_id=customer_id, author_user_id=author_user_id, body=body)
    db.add(note)
    db.flush()
    return note
