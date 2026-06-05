"""POS receipt payload — company header (console-configured) + outlet/stall + lines + totals + payment."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.catalog import Menu
from app.models.orders import Order
from app.models.payments import Payment, Transaction
from app.models.tenancy import DiningTable, Merchant, Outlet


def build_receipt(db: Session, *, order: Order) -> dict:
    merchant = db.get(Merchant, order.merchant_id)
    outlet = db.get(Outlet, order.outlet_id)
    cfg = (merchant.settings or {}).get("receipt", {}) if merchant and isinstance(merchant.settings, dict) else {}
    menus = list(db.scalars(select(Menu).where(Menu.outlet_id == order.outlet_id)).all())
    stall = (menus[0].stall_name or menus[0].name) if len(menus) == 1 else None
    if stall and outlet and stall == outlet.name:
        stall = None   # single storefront: stall == outlet → don't print it twice
    table = db.get(DiningTable, order.table_id) if order.table_id else None
    pay = db.scalar(select(Payment).where(Payment.order_id == order.id).order_by(Payment.created_at.desc()))
    txn = db.scalar(select(Transaction).where(Transaction.order_id == order.id))
    return {
        "company": {
            "name": cfg.get("company_name") or (merchant.name if merchant else ""),
            "uen": cfg.get("uen", ""), "address": cfg.get("address", ""), "phone": cfg.get("phone", ""),
        },
        "outlet": {"name": outlet.name if outlet else "", "address": (outlet.address if outlet else "") or ""},
        "stall": stall,
        "order_id": order.id,
        "table_label": table.label if table else None,
        "created_at": order.placed_at or order.created_at,
        "items": [
            {"name": it.name_snapshot, "quantity": it.quantity, "line_total": float(it.line_total),
             "modifiers": [m.get("name", "") for m in (it.modifiers or [])]}
            for it in order.items
        ],
        "subtotal": float(order.subtotal), "service_charge": float(order.service_charge),
        "tax": float(order.tax), "discount": float(order.discount_amount or 0),
        "voucher_code": order.voucher_code, "total": float(order.total),
        "payment": ({"method": pay.method, "status": pay.status, "reference": pay.reference} if pay else None),
        "points_earned": (txn.points_earned if txn else None),
        "footer": cfg.get("footer") or "Thank you!",
    }
