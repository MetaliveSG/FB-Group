"""Org-structure admin routes: brands / outlets / tables + QR (Module 1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_scope, require, resolve_merchant
from app.db.session import get_db
from app.schemas.org import (
    BrandCreateIn,
    BrandOut,
    BrandUpdateIn,
    LoyaltyProgramOut,
    LoyaltyProgramUpdateIn,
    NavFlagsOut,
    OutletCreateIn,
    OutletOut,
    OutletUpdateIn,
    SettingsOut,
    SettingsUpdateIn,
    TableCreateIn,
    TableOut,
)
from app.services import loyalty_admin, merchant_settings, org_admin
from app.services.audit import record as audit_record

router = APIRouter(prefix="/org", tags=["org"])


def _mid(scope, merchant_id, perm):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, perm, mid)
    return mid


# --- Merchant settings (feature toggles) ---
# Nav flags: the non-sensitive boolean subset (no spin costs / earn rates) every staff
# member may read to render navigation. `order.view` is the universal floor (staff, outlet
# manager, brand manager, owner all hold it). Full /settings + /loyalty are owner-only below,
# so a downline manager cannot read merchant-level economic config — only what nav needs.
@router.get("/nav-flags", response_model=NavFlagsOut)
def get_nav_flags(merchant_id: str | None = Query(None), scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "order.view")
    flags = merchant_settings.get_nav_flags(db, merchant_id=mid)
    # Capability for client nav-gating: whether the caller may manage merchant-level config
    # (true for the owner + an operator drilled into the merchant). Lets the UI hide
    # owner-only nav without exposing the settings themselves.
    return {**flags, "can_manage_merchant": scope.can("merchant.manage", mid)}


@router.get("/settings", response_model=SettingsOut)
def get_settings(merchant_id: str | None = Query(None), scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "merchant.manage")  # owner-only — hard upline isolation
    return merchant_settings.get_settings(db, merchant_id=mid)


@router.patch("/settings", response_model=SettingsOut)
def update_settings(body: SettingsUpdateIn, merchant_id: str | None = Query(None),
                    scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "merchant.manage")
    out = merchant_settings.update_settings(db, merchant_id=mid, changes=body.model_dump(exclude_none=True))
    audit_record(db, action="merchant.settings_update", actor_id=scope.user_id, merchant_id=mid,
                 meta=body.model_dump(exclude_none=True))
    db.commit()
    return out


# --- Loyalty program (standing earn rules: earn rate / welcome / birthday) ---
@router.get("/loyalty", response_model=LoyaltyProgramOut)
def get_loyalty_program(merchant_id: str | None = Query(None), scope=Depends(get_scope),
                        db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "merchant.manage")  # owner-only — earn rates are upline config
    return loyalty_admin.get_program(db, merchant_id=mid)


@router.put("/loyalty", response_model=LoyaltyProgramOut)
def update_loyalty_program(body: LoyaltyProgramUpdateIn, merchant_id: str | None = Query(None),
                           scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "merchant.manage")
    out = loyalty_admin.update_program(
        db, merchant_id=mid, points_per_dollar=body.points_per_dollar,
        welcome_bonus=body.welcome_bonus, birthday_bonus=body.birthday_bonus,
    )
    audit_record(db, action="merchant.loyalty_update", actor_id=scope.user_id, merchant_id=mid,
                 meta=body.model_dump())
    db.commit()
    return out


# --- Brands ---
@router.get("/brands", response_model=list[BrandOut])
def list_brands(merchant_id: str | None = Query(None), scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "outlet.manage")
    return org_admin.list_brands(db, merchant_id=mid)


@router.post("/brands", response_model=BrandOut, status_code=201)
def create_brand(body: BrandCreateIn, merchant_id: str | None = Query(None),
                 scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "brand.manage")
    b = org_admin.create_brand(db, merchant_id=mid, name=body.name, cuisine_type=body.cuisine_type)
    audit_record(db, action="org.brand_create", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="brand", entity_id=b.id)
    db.commit()
    return BrandOut(id=b.id, name=b.name, cuisine_type=b.cuisine_type, is_active=b.is_active, outlets=0)


@router.patch("/brands/{brand_id}", response_model=BrandOut)
def update_brand(brand_id: str, body: BrandUpdateIn, merchant_id: str | None = Query(None),
                 scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "brand.manage")
    org_admin.update_brand(db, merchant_id=mid, brand_id=brand_id, name=body.name,
                           cuisine_type=body.cuisine_type, is_active=body.is_active)
    db.commit()
    return next(b for b in org_admin.list_brands(db, merchant_id=mid) if b["id"] == brand_id)


# --- Outlets ---
@router.get("/outlets", response_model=list[OutletOut])
def list_outlets(merchant_id: str | None = Query(None), scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "outlet.manage")
    return org_admin.list_outlets(db, merchant_id=mid)


@router.post("/outlets", response_model=OutletOut, status_code=201)
def create_outlet(body: OutletCreateIn, merchant_id: str | None = Query(None),
                  scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "outlet.manage")
    o = org_admin.create_outlet(db, merchant_id=mid, brand_id=body.brand_id, name=body.name, address=body.address)
    audit_record(db, action="org.outlet_create", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="outlet", entity_id=o.id)
    db.commit()
    return next(x for x in org_admin.list_outlets(db, merchant_id=mid) if x["id"] == o.id)


@router.patch("/outlets/{outlet_id}", response_model=OutletOut)
def update_outlet(outlet_id: str, body: OutletUpdateIn, merchant_id: str | None = Query(None),
                  scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "outlet.manage")
    org_admin.update_outlet(db, merchant_id=mid, outlet_id=outlet_id, name=body.name,
                            address=body.address, is_active=body.is_active)
    db.commit()
    return next(x for x in org_admin.list_outlets(db, merchant_id=mid) if x["id"] == outlet_id)


# --- Tables + QR ---
@router.get("/outlets/{outlet_id}/tables", response_model=list[TableOut])
def list_tables(outlet_id: str, merchant_id: str | None = Query(None),
                scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "outlet.manage")
    return org_admin.list_tables(db, merchant_id=mid, outlet_id=outlet_id)


@router.post("/outlets/{outlet_id}/tables", response_model=TableOut, status_code=201)
def create_table(outlet_id: str, body: TableCreateIn, merchant_id: str | None = Query(None),
                 scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "outlet.manage")
    row = org_admin.create_table(db, merchant_id=mid, outlet_id=outlet_id, label=body.label, seats=body.seats)
    audit_record(db, action="org.table_create", actor_id=scope.user_id, merchant_id=mid,
                 entity_type="table", entity_id=row["id"])
    db.commit()
    return TableOut(**row)


@router.delete("/tables/{table_id}", status_code=204)
def delete_table(table_id: str, merchant_id: str | None = Query(None),
                 scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id, "outlet.manage")
    org_admin.delete_table(db, merchant_id=mid, table_id=table_id)
    db.commit()
