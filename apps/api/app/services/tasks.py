"""CRM tasks/activities service (Salesforce-style follow-ups)."""
from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.db.base import utcnow
from app.models.engagement import CrmTask
from app.models.enums import TaskPriority, TaskStatus


def create_task(
    db: Session,
    *,
    merchant_id: str,
    customer_id: str,
    title: str,
    description: str = "",
    due_date: date | None = None,
    priority: str = TaskPriority.NORMAL.value,
    assignee_user_id: str | None = None,
    created_by_user_id: str | None = None,
) -> CrmTask:
    task = CrmTask(
        merchant_id=merchant_id, customer_id=customer_id, title=title, description=description,
        due_date=due_date, priority=priority, assignee_user_id=assignee_user_id,
        created_by_user_id=created_by_user_id,
    )
    db.add(task)
    db.flush()
    return task


def list_for_customer(db: Session, *, merchant_id: str, customer_id: str) -> list[CrmTask]:
    return list(db.scalars(
        select(CrmTask).where(CrmTask.merchant_id == merchant_id, CrmTask.customer_id == customer_id)
        .order_by(CrmTask.status, CrmTask.due_date.is_(None), CrmTask.due_date, CrmTask.created_at.desc())
    ).all())


def list_open_for_user(db: Session, *, merchant_id: str, user_id: str) -> list[CrmTask]:
    return list(db.scalars(
        select(CrmTask).where(
            CrmTask.merchant_id == merchant_id,
            CrmTask.assignee_user_id == user_id,
            CrmTask.status == TaskStatus.OPEN.value,
        ).order_by(CrmTask.due_date.is_(None), CrmTask.due_date)
    ).all())


def open_counts_by_customer(db: Session, *, merchant_id: str) -> dict[str, int]:
    rows = db.execute(
        select(CrmTask.customer_id, func.count())
        .where(CrmTask.merchant_id == merchant_id, CrmTask.status == TaskStatus.OPEN.value)
        .group_by(CrmTask.customer_id)
    ).all()
    return {cid: n for cid, n in rows}


def complete_task(db: Session, *, merchant_id: str, task_id: str) -> CrmTask:
    task = db.get(CrmTask, task_id)
    if not task or task.merchant_id != merchant_id:
        raise NotFoundError("Task not found", code="task_not_found")
    task.status = TaskStatus.DONE.value
    task.completed_at = utcnow()
    db.flush()
    return task
