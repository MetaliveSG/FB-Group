"""Point-multiplier promotions (time-bound CAMPAIGN_MULTIPLIER reward rules).

UI lives on the merchant Campaigns page; kept on its own `/promotions` path to avoid the
`/campaigns/{campaign_id}` catch-all. Gated by `campaign.manage` (owner / brand manager).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.deps import get_scope, require, resolve_merchant
from app.db.session import get_db
from app.schemas.promotions import PromotionCreateIn, PromotionOut
from app.services import promotions as promo_service
from app.services.audit import record as audit_record

router = APIRouter(prefix="/promotions", tags=["promotions"])


def _mid(scope, merchant_id):
    mid = resolve_merchant(scope, merchant_id)
    require(scope, "campaign.manage", mid)
    return mid


@router.get("", response_model=list[PromotionOut])
def list_promotions(merchant_id: str | None = Query(None), scope=Depends(get_scope),
                    db: Session = Depends(get_db)):
    return promo_service.list_promotions(db, merchant_id=_mid(scope, merchant_id))


@router.post("", response_model=PromotionOut, status_code=status.HTTP_201_CREATED)
def create_promotion(body: PromotionCreateIn, merchant_id: str | None = Query(None),
                     scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id)
    out = promo_service.create_promotion(
        db, merchant_id=mid, label=body.label, multiplier=body.multiplier,
        starts_on=body.starts_on, ends_on=body.ends_on,
    )
    audit_record(db, action="promotion.create", actor_id=scope.user_id, merchant_id=mid,
                 meta={"label": body.label, "multiplier": body.multiplier})
    db.commit()
    return out


@router.delete("/{promo_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_promotion(promo_id: str, merchant_id: str | None = Query(None),
                         scope=Depends(get_scope), db: Session = Depends(get_db)):
    mid = _mid(scope, merchant_id)
    promo_service.deactivate_promotion(db, merchant_id=mid, promo_id=promo_id)
    audit_record(db, action="promotion.deactivate", actor_id=scope.user_id, merchant_id=mid,
                 meta={"promo_id": promo_id})
    db.commit()
