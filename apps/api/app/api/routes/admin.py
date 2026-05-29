"""User management routes — staff `user.manage` (Module 10)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_scope, require, resolve_merchant
from app.db.session import get_db
from app.schemas.admin import AdminUserOut, InviteUserIn, InviteUserOut
from app.services import users_admin
from app.services.audit import record as audit_record

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[AdminUserOut])
def list_users(merchant_id: str | None = Query(default=None), scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "user.manage", mid)
    return users_admin.list_users(db, merchant_id=mid)


@router.post("/users", response_model=InviteUserOut, status_code=201)
def invite_user(body: InviteUserIn, merchant_id: str | None = Query(default=None),
                scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "user.manage", mid)
    user = users_admin.invite_user(
        db, merchant_id=mid, email=body.email, password=body.password, full_name=body.full_name,
        role=body.role, scope_type=body.scope_type, scope_id=body.scope_id or mid)
    audit_record(db, action="user.invite", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="user", entity_id=user.id, meta={"email": body.email, "role": body.role})
    db.commit()
    db.refresh(user)
    return InviteUserOut(id=user.id, email=user.email, full_name=user.full_name)


@router.delete("/users/assignments/{assignment_id}", status_code=204)
def revoke_assignment(assignment_id: str, merchant_id: str | None = Query(default=None),
                      scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "user.manage", mid)
    users_admin.revoke_assignment(db, merchant_id=mid, assignment_id=assignment_id)
    audit_record(db, action="user.revoke", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="assignment", entity_id=assignment_id)
    db.commit()
