"""Kitchen Display (KDS) — station-authed endpoints. A kitchen tablet authenticates with its private
per-outlet STATION TOKEN (`X-KDS-Token` header), NOT a web/email login (the locked KDS auth model). The
token scopes it to ONE outlet: see that outlet's open tickets + advance ticket status, nothing else."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.errors import AuthError, ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models.kds import KdsStation
from app.models.orders import Order
from app.models.tenancy import Outlet
from app.schemas.orders import FulfilmentStatusUpdate, KitchenOrderOut
from app.services import boundaries, kds_station
from app.services import orders as orders_service

router = APIRouter(prefix="/kds", tags=["kds"])


def get_kds_station(
    x_kds_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> KdsStation:
    """Resolve + authorise the calling kitchen station from its bearer token. 401 if unknown/revoked;
    403 if the outlet's Table-QR (ordering) module is off (no ordering ⇒ no kitchen)."""
    station = kds_station.resolve_active(db, token=x_kds_token or "")
    if station is None:
        raise AuthError("Invalid or revoked kitchen token", code="kds_token_invalid")
    if not boundaries.resolve_modules_for_outlet(
            db, outlet_id=station.outlet_id, merchant_id=station.merchant_id)["qr_ordering_enabled"]:
        raise ForbiddenError("Ordering is disabled for this outlet", code="ordering_disabled")
    return station


@router.get("/context")
def kds_context(station: KdsStation = Depends(get_kds_station), db: Session = Depends(get_db)):
    """Minimal bind info for the tablet header — which outlet this station serves."""
    outlet = db.get(Outlet, station.outlet_id)
    return {"outlet_id": station.outlet_id, "outlet_name": outlet.name if outlet else "—", "label": station.label}


@router.get("/queue", response_model=list[KitchenOrderOut])
def kds_queue(station: KdsStation = Depends(get_kds_station), db: Session = Depends(get_db)):
    """The station's outlet queue: paid, not-yet-collected orders, oldest-first."""
    return orders_service.list_kitchen_orders(db, outlet_id=station.outlet_id)


@router.patch("/orders/{order_id}/fulfilment", response_model=KitchenOrderOut)
def kds_advance(order_id: str, body: FulfilmentStatusUpdate,
                station: KdsStation = Depends(get_kds_station), db: Session = Depends(get_db)):
    """Advance a ticket (queued→preparing→ready→collected) — only for an order in THIS station's outlet."""
    order = db.get(Order, order_id)
    if not order or order.outlet_id != station.outlet_id:
        raise NotFoundError("Order not found", code="order_not_found")
    orders_service.advance_fulfilment(db, order, body.status)
    db.commit()
    db.refresh(order)
    return orders_service.kitchen_ticket(db, order)
