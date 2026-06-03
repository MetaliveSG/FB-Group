"""Operator console routes — gated by platform-tier operator permissions (roles)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import get_scope, require_platform
from app.auth.permissions import P, WILDCARD
from app.db.session import get_db
from app.schemas.platform import (
    CoalitionCreateIn,
    CoalitionMemberIn,
    CoalitionOut,
    CoalitionUpdateIn,
    MerchantActiveIn,
    MerchantCreateIn,
    MerchantCreateOut,
    MerchantKpiOut,
    MerchantUpdateIn,
    OperatorCreateIn,
    OperatorCreateOut,
    OperatorOut,
    OverviewOut,
    PlatformCapabilitiesOut,
)
from app.services import platform as platform_service
from app.services.audit import record as audit_record

router = APIRouter(prefix="/platform", tags=["operator"])

_PLATFORM_PERMS = sorted(k for k in P if k.startswith("platform."))


@router.get("/permissions", response_model=PlatformCapabilitiesOut)
def my_platform_permissions(scope=Depends(get_scope)):
    """The operator's platform capabilities — drives which console sections/actions render.
    Any platform-tier user may read their own; non-operators get an empty set."""
    if scope.is_super_admin:
        return PlatformCapabilitiesOut(permissions=_PLATFORM_PERMS, is_owner=True)
    perms = sorted(p for p in scope.platform_perms if p in P and p != WILDCARD)
    return PlatformCapabilitiesOut(
        permissions=perms, is_owner="platform.operators.manage" in scope.platform_perms)


@router.get("/overview", response_model=OverviewOut)
def overview(scope=Depends(require_platform("platform.overview.view")), db: Session = Depends(get_db)):
    return platform_service.overview(db)


@router.get("/merchants", response_model=list[MerchantKpiOut])
def merchants(scope=Depends(require_platform("platform.merchants.view")), db: Session = Depends(get_db)):
    return platform_service.list_merchants(db)


@router.get("/coalitions", response_model=list[CoalitionOut])
def coalitions(scope=Depends(require_platform("platform.merchants.view")), db: Session = Depends(get_db)):
    return platform_service.list_coalitions(db)


@router.post("/merchants", response_model=MerchantCreateOut, status_code=201)
def create_merchant(body: MerchantCreateIn,
                    scope=Depends(require_platform("platform.merchants.onboard")),
                    db: Session = Depends(get_db)):
    result = platform_service.create_merchant(
        db, name=body.name, owner_email=body.owner_email,
        owner_password=body.owner_password, owner_name=body.owner_name,
        kind=body.kind, subscription_fee=body.subscription_fee)
    audit_record(db, action="platform.merchant_create", actor_id=scope.user_id,
                 merchant_id=result["merchant_id"], entity_type="merchant",
                 entity_id=result["merchant_id"], meta={"owner": body.owner_email, "kind": body.kind})
    db.commit()
    return result


@router.patch("/merchants/{merchant_id}", response_model=MerchantKpiOut)
def set_merchant_active(merchant_id: str, body: MerchantActiveIn,
                        scope=Depends(require_platform("platform.merchants.suspend")),
                        db: Session = Depends(get_db)):
    platform_service.set_merchant_active(db, merchant_id=merchant_id, is_active=body.is_active)
    audit_record(db, action="platform.merchant_active", actor_id=scope.user_id,
                 merchant_id=merchant_id, entity_type="merchant", entity_id=merchant_id,
                 meta={"is_active": body.is_active})
    db.commit()
    return _merchant_row(db, merchant_id)


def _merchant_row(db: Session, merchant_id: str):
    """Refreshed KPI row for a single merchant (used by mutating endpoints)."""
    return next((m for m in platform_service.list_merchants(db) if m["id"] == merchant_id), None)


@router.put("/merchants/{merchant_id}", response_model=MerchantKpiOut)
def update_merchant(merchant_id: str, body: MerchantUpdateIn,
                    scope=Depends(require_platform("platform.merchants.onboard")),
                    db: Session = Depends(get_db)):
    platform_service.update_merchant(db, merchant_id=merchant_id, name=body.name,
                                     module_flags=body.module_flags)
    audit_record(db, action="platform.merchant_update", actor_id=scope.user_id,
                 merchant_id=merchant_id, entity_type="merchant", entity_id=merchant_id,
                 meta={"name": body.name, "module_flags": body.module_flags})
    db.commit()
    return _merchant_row(db, merchant_id)


# ─── Platform operators (managing operators is Owner-only) ──────────────────
@router.get("/operators", response_model=list[OperatorOut])
def list_operators(scope=Depends(require_platform("platform.operators.manage")),
                   db: Session = Depends(get_db)):
    return platform_service.list_operators(db, current_user_id=scope.user_id)


@router.post("/operators", response_model=OperatorCreateOut, status_code=201)
def invite_operator(body: OperatorCreateIn,
                    scope=Depends(require_platform("platform.operators.manage")),
                    db: Session = Depends(get_db)):
    user = platform_service.invite_operator(db, email=body.email, password=body.password,
                                            full_name=body.full_name, role=body.role)
    audit_record(db, action="platform.operator_invite", actor_id=scope.user_id,
                 entity_type="user", entity_id=user.id, meta={"email": body.email, "role": body.role})
    db.commit()
    db.refresh(user)
    return OperatorCreateOut(id=user.id, email=user.email, full_name=user.full_name, role=body.role)


@router.delete("/operators/{operator_id}", status_code=204)
def revoke_operator(operator_id: str,
                    scope=Depends(require_platform("platform.operators.manage")),
                    db: Session = Depends(get_db)):
    platform_service.revoke_operator(db, operator_id=operator_id, current_user_id=scope.user_id)
    audit_record(db, action="platform.operator_revoke", actor_id=scope.user_id,
                 entity_type="user", entity_id=operator_id)
    db.commit()


# ─── Coalitions ─────────────────────────────────────────────────────────────
def _coalition_row(db: Session, coalition_id: str):
    return next((c for c in platform_service.list_coalitions(db) if c["id"] == coalition_id), None)


@router.post("/coalitions", response_model=CoalitionOut, status_code=201)
def create_coalition(body: CoalitionCreateIn,
                     scope=Depends(require_platform("platform.coalitions.manage")),
                     db: Session = Depends(get_db)):
    c = platform_service.create_coalition(db, name=body.name)
    audit_record(db, action="platform.coalition_create", actor_id=scope.user_id,
                 entity_type="coalition", entity_id=c.id, meta={"name": body.name})
    db.commit()
    return _coalition_row(db, c.id)


@router.patch("/coalitions/{coalition_id}", response_model=CoalitionOut)
def update_coalition(coalition_id: str, body: CoalitionUpdateIn,
                     scope=Depends(require_platform("platform.coalitions.manage")),
                     db: Session = Depends(get_db)):
    platform_service.update_coalition(db, coalition_id=coalition_id, name=body.name, is_active=body.is_active)
    audit_record(db, action="platform.coalition_update", actor_id=scope.user_id,
                 entity_type="coalition", entity_id=coalition_id,
                 meta={"name": body.name, "is_active": body.is_active})
    db.commit()
    return _coalition_row(db, coalition_id)


@router.post("/coalitions/{coalition_id}/members", response_model=CoalitionOut, status_code=201)
def add_coalition_member(coalition_id: str, body: CoalitionMemberIn,
                         scope=Depends(require_platform("platform.coalitions.manage")),
                         db: Session = Depends(get_db)):
    platform_service.add_coalition_member(db, coalition_id=coalition_id, merchant_id=body.merchant_id)
    audit_record(db, action="platform.coalition_member_add", actor_id=scope.user_id,
                 merchant_id=body.merchant_id, entity_type="coalition", entity_id=coalition_id,
                 meta={"merchant_id": body.merchant_id})
    db.commit()
    return _coalition_row(db, coalition_id)


@router.delete("/coalitions/{coalition_id}/members/{merchant_id}", response_model=CoalitionOut)
def remove_coalition_member(coalition_id: str, merchant_id: str,
                            scope=Depends(require_platform("platform.coalitions.manage")),
                            db: Session = Depends(get_db)):
    platform_service.remove_coalition_member(db, coalition_id=coalition_id, merchant_id=merchant_id)
    audit_record(db, action="platform.coalition_member_remove", actor_id=scope.user_id,
                 merchant_id=merchant_id, entity_type="coalition", entity_id=coalition_id,
                 meta={"merchant_id": merchant_id})
    db.commit()
    return _coalition_row(db, coalition_id)