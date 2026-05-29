"""Audit logging helper for critical/privileged actions."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record(
    db: Session,
    *,
    action: str,
    actor_type: str = "user",
    actor_id: str | None = None,
    merchant_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    meta: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    log = AuditLog(
        action=action,
        actor_type=actor_type,
        actor_id=actor_id,
        merchant_id=merchant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        meta=meta or {},
        ip_address=ip_address,
    )
    db.add(log)
    db.flush()
    return log
