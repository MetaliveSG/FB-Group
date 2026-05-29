"""Customer rewards center + spin-the-wheel (customer-authenticated)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.deps import get_current_customer
from app.db.session import get_db
from app.models.identity import Customer
from app.schemas.rewards import (
    CatalogItemOut,
    JackpotConfigOut,
    JackpotPlayOut,
    LoyaltySummaryOut,
    MyOrderOut,
    MyProfileOut,
    MyVoucherOut,
    ProfileUpdate,
    RedeemRequest,
    RedeemResponse,
    SpinRequest,
    SpinResponse,
    WheelConfigOut,
)
from app.services import jackpot as jackpot_service
from app.services import rewards as rewards_service

router = APIRouter(prefix="/me", tags=["rewards"])


@router.get("/loyalty", response_model=LoyaltySummaryOut)
def my_loyalty(merchant_id: str = Query(...), customer: Customer = Depends(get_current_customer),
               db: Session = Depends(get_db)):
    return rewards_service.loyalty_summary(db, customer_id=customer.id, merchant_id=merchant_id)


@router.get("/profile", response_model=MyProfileOut)
def get_profile(customer: Customer = Depends(get_current_customer), db: Session = Depends(get_db)):
    return rewards_service.my_profile(db, customer=customer)


@router.patch("/profile", response_model=MyProfileOut)
def update_profile(body: ProfileUpdate, customer: Customer = Depends(get_current_customer),
                   db: Session = Depends(get_db)):
    result = rewards_service.update_my_profile(
        db, customer=customer, phone=body.phone, birthday=body.birthday,
        gender=body.gender, full_name=body.full_name)
    db.commit()
    return result


@router.get("/orders", response_model=list[MyOrderOut])
def my_orders(merchant_id: str = Query(...), customer: Customer = Depends(get_current_customer),
              db: Session = Depends(get_db)):
    return rewards_service.my_orders(db, customer_id=customer.id, merchant_id=merchant_id)


@router.get("/vouchers", response_model=list[MyVoucherOut])
def my_vouchers(merchant_id: str = Query(...), customer: Customer = Depends(get_current_customer),
                db: Session = Depends(get_db)):
    return rewards_service.my_vouchers(db, customer_id=customer.id, merchant_id=merchant_id)


@router.get("/rewards/catalog", response_model=list[CatalogItemOut])
def reward_catalog(merchant_id: str = Query(...), customer: Customer = Depends(get_current_customer),
                   db: Session = Depends(get_db)):
    summary = rewards_service.loyalty_summary(db, customer_id=customer.id, merchant_id=merchant_id)
    return rewards_service.list_catalog(db, merchant_id=merchant_id, balance=summary["points_balance"])


@router.post("/rewards/redeem", response_model=RedeemResponse)
def redeem(body: RedeemRequest, customer: Customer = Depends(get_current_customer),
           db: Session = Depends(get_db)):
    result = rewards_service.redeem_catalog_item(
        db, customer_id=customer.id, merchant_id=body.merchant_id, item_id=body.item_id)
    db.commit()
    return result


@router.get("/wheel", response_model=WheelConfigOut)
def wheel(merchant_id: str = Query(...), customer: Customer = Depends(get_current_customer),
          db: Session = Depends(get_db)):
    return rewards_service.wheel_config(db, merchant_id=merchant_id)


@router.post("/wheel/spin", response_model=SpinResponse)
def spin(body: SpinRequest, customer: Customer = Depends(get_current_customer),
         db: Session = Depends(get_db)):
    result = rewards_service.spin_wheel(db, customer_id=customer.id, merchant_id=body.merchant_id)
    db.commit()
    return result


# --- 3x3 Jackpot --------------------------------------------------------
@router.get("/jackpot", response_model=JackpotConfigOut)
def jackpot(merchant_id: str = Query(...), customer: Customer = Depends(get_current_customer),
            db: Session = Depends(get_db)):
    return jackpot_service.jackpot_config(db, merchant_id=merchant_id)


@router.post("/jackpot/play", response_model=JackpotPlayOut)
def jackpot_play(body: SpinRequest, customer: Customer = Depends(get_current_customer),
                 db: Session = Depends(get_db)):
    result = jackpot_service.play_jackpot(
        db, customer_id=customer.id, merchant_id=body.merchant_id)
    db.commit()
    return result
