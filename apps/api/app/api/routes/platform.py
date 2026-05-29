"""Operator console routes — platform super admin only."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.deps import require_super_admin
from app.db.session import get_db
from app.schemas.platform import (
    CoalitionOut,
    MerchantActiveIn,
    MerchantCreateIn,
    MerchantCreateOut,
    MerchantKpiOut,
    OverviewOut,
)
from app.services import platform as platform_service
from app.services.audit import record as audit_record

router = APIRouter(prefix="/platform", tags=["operator"])


@router.get("/overview", response_model=OverviewOut)
def overview(scope=Depends(require_super_admin), db: Session = Depends(get_db)):
    return platform_service.overview(db)


@router.get("/merchants", response_model=list[MerchantKpiOut])
def merchants(scope=Depends(require_super_admin), db: Session = Depends(get_db)):
    return platform_service.list_merchants(db)


@router.get("/coalitions", response_model=list[CoalitionOut])
def coalitions(scope=Depends(require_super_admin), db: Session = Depends(get_db)):
    return platform_service.list_coalitions(db)


@router.post("/merchants", response_model=MerchantCreateOut, status_code=201)
def create_merchant(body: MerchantCreateIn, scope=Depends(require_super_admin), db: Session = Depends(get_db)):
    result = platform_service.create_merchant(
        db, name=body.name, owner_email=body.owner_email,
        owner_password=body.owner_password, owner_name=body.owner_name)
    audit_record(db, action="platform.merchant_create", actor_id=scope.user_id,
                 merchant_id=result["merchant_id"], entity_type="merchant",
                 entity_id=result["merchant_id"], meta={"owner": body.owner_email})
    db.commit()
    return result


@router.patch("/merchants/{merchant_id}", response_model=MerchantKpiOut)
def set_merchant_active(merchant_id: str, body: MerchantActiveIn,
                        scope=Depends(require_super_admin), db: Session = Depends(get_db)):
    platform_service.set_merchant_active(db, merchant_id=merchant_id, is_active=body.is_active)
    audit_record(db, action="platform.merchant_active", actor_id=scope.user_id,
                 merchant_id=merchant_id, entity_type="merchant", entity_id=merchant_id,
                 meta={"is_active": body.is_active})
    db.commit()
    # Return refreshed KPI row for this merchant.
    row = next((m for m in platform_service.list_merchants(db) if m["id"] == merchant_id), None)
    return row