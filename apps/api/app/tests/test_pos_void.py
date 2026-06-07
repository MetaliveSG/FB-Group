"""POS void (supervisor `order.void`): reverse a paid sale — drop the transaction, void the payment,
claw back loyalty points, restore a redeemed voucher. Gated: cashier/staff cannot void."""
from sqlalchemy import func, select

from app.models.loyalty import RewardRedemption, RewardTransaction
from app.models.orders import Order
from app.models.payments import Payment, Transaction
from app.services import vouchers
from app.tests.factories import make_world
from app.tests.helpers import H, register_customer, staff_token


def _paid_order(client, t, w, phone=None):
    body = {"outlet_id": w.outlet_id, "items": [{"menu_item_id": w.burger_id, "quantity": 1}]}
    if phone:
        body["customer_phone"] = phone
    o = client.post("/api/v1/orders/manual", json=body, headers=H(t)).json()
    r = client.post(f"/api/v1/orders/{o['id']}/cashier-checkout", json={"method": "cash"}, headers=H(t))
    assert r.status_code == 200, r.text
    return o


def test_void_reverses_the_sale(client, db):
    w = make_world(db)
    t = staff_token(client, w.owner_email)        # owner holds order.void
    o = _paid_order(client, t, w)
    assert db.get(Order, o["id"]).status == "completed"
    r = client.post(f"/api/v1/orders/{o['id']}/void", json={"reason": "rang up wrong"}, headers=H(t))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "voided"
    # order voided · sales transaction gone (drops from reports) · payment marked voided
    assert db.get(Order, o["id"]).status == "voided"
    assert db.scalar(select(Transaction).where(Transaction.order_id == o["id"])) is None
    assert db.scalar(select(Payment.status).where(Payment.order_id == o["id"])) == "voided"


def test_void_is_idempotent_guarded(client, db):
    w = make_world(db)
    t = staff_token(client, w.owner_email)
    o = _paid_order(client, t, w)
    assert client.post(f"/api/v1/orders/{o['id']}/void", json={}, headers=H(t)).status_code == 200
    again = client.post(f"/api/v1/orders/{o['id']}/void", json={}, headers=H(t))
    assert again.status_code == 409 and again.json()["error"]["code"] == "already_voided"


def test_void_requires_order_void_permission(client, db):
    w = make_world(db)
    owner = staff_token(client, w.owner_email)
    o = _paid_order(client, owner, w)
    staff = staff_token(client, w.staff_email)    # STAFF role — no order.void
    r = client.post(f"/api/v1/orders/{o['id']}/void", json={}, headers=H(staff))
    assert r.status_code == 403
    assert db.get(Order, o["id"]).status == "completed"   # untouched


def test_void_claws_back_loyalty_points(client, db):
    w = make_world(db, earn_rate=10)
    t = staff_token(client, w.owner_email)
    register_customer(client, email="vl@b.sg", phone="+6590000801")
    o = _paid_order(client, t, w, phone="+6590000801")
    earned = db.scalar(select(func.sum(RewardTransaction.points)).where(RewardTransaction.order_id == o["id"]))
    assert earned and earned > 0
    r = client.post(f"/api/v1/orders/{o['id']}/void", json={}, headers=H(t))
    assert r.json()["points_reversed"] == earned
    net = db.scalar(select(func.sum(RewardTransaction.points)).where(RewardTransaction.order_id == o["id"]))
    assert net == 0          # earn fully cancelled by a reversing ADJUST


def test_void_restores_redeemed_voucher(client, db):
    w = make_world(db)
    t = staff_token(client, w.owner_email)
    cust = register_customer(client, email="vv@b.sg", phone="+6590000802")
    vouchers.issue_vouchers(db, customer_id=cust["customer"]["id"], merchant_id=w.merchant_id,
                            name="$1 off", value=1)
    db.commit()
    v = db.scalar(select(RewardRedemption).where(RewardRedemption.merchant_id == w.merchant_id))
    code = v.voucher_code
    o = client.post("/api/v1/orders/manual",
                    json={"outlet_id": w.outlet_id, "items": [{"menu_item_id": w.burger_id, "quantity": 1}],
                          "customer_phone": "+6590000802"}, headers=H(t)).json()
    vouchers.redeem_voucher(db, code=code, merchant_id=w.merchant_id, order=db.get(Order, o["id"]))
    db.commit()
    client.post(f"/api/v1/orders/{o['id']}/cashier-checkout", json={"method": "cash"}, headers=H(t))
    assert db.scalar(select(RewardRedemption.status).where(RewardRedemption.voucher_code == code)) == "redeemed"
    r = client.post(f"/api/v1/orders/{o['id']}/void", json={}, headers=H(t))
    assert r.json()["voucher_restored"] == code
    db.refresh(v)
    assert v.status == "issued" and v.order_id is None   # reusable again
