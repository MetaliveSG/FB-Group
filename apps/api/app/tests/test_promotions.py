"""Point-multiplier promotions — create/list/deactivate + the engine honours the window."""
from datetime import date, datetime
from decimal import Decimal

from app.loyalty.engine import accrue_on_transaction
from app.models.identity import Customer
from app.services import promotions as promo_service
from app.tests.factories import make_world
from app.tests.helpers import H, staff_token


def _cust(db, name="Promo"):
    c = Customer(full_name=name)
    db.add(c); db.flush()
    return c


def test_active_multiplier_doubles_earned_points(db):
    w = make_world(db, earn_rate=1)  # 1pt/$ + welcome 50
    promo_service.create_promotion(db, merchant_id=w.merchant_id, label="Double Day",
                                   multiplier=2, starts_on=date(2026, 6, 1), ends_on=date(2026, 6, 30))
    c = _cust(db)
    # in-window order: (base 100 + welcome 50) * 2 = 300
    pts = accrue_on_transaction(db, customer=c, merchant_id=w.merchant_id,
                                amount=Decimal("100"), order_id=None, now=datetime(2026, 6, 15))
    assert pts == 300


def test_expired_multiplier_not_applied(db):
    w = make_world(db, earn_rate=1)
    promo_service.create_promotion(db, merchant_id=w.merchant_id, label="June Only",
                                   multiplier=2, starts_on=date(2026, 6, 1), ends_on=date(2026, 6, 30))
    c = _cust(db)
    # July order — promo window closed → no multiplier: base 100 + welcome 50 = 150
    pts = accrue_on_transaction(db, customer=c, merchant_id=w.merchant_id,
                                amount=Decimal("100"), order_id=None, now=datetime(2026, 7, 1))
    assert pts == 150


def test_deactivated_multiplier_not_applied(db):
    w = make_world(db, earn_rate=1)
    promo = promo_service.create_promotion(db, merchant_id=w.merchant_id, label="Off", multiplier=3,
                                           starts_on=None, ends_on=None)
    promo_service.deactivate_promotion(db, merchant_id=w.merchant_id, promo_id=promo["id"])
    c = _cust(db)
    pts = accrue_on_transaction(db, customer=c, merchant_id=w.merchant_id,
                                amount=Decimal("100"), order_id=None, now=datetime(2026, 6, 15))
    assert pts == 150  # multiplier inactive → no boost


# ---- API: RBAC + tenant isolation ----
def test_create_and_list_via_api(client, db):
    w = make_world(db)
    owner = staff_token(client, w.owner_email)
    r = client.post("/api/v1/promotions", headers=H(owner),
                    json={"label": "Weekend 2x", "multiplier": 2, "starts_on": "2026-06-01", "ends_on": "2026-06-30"})
    assert r.status_code == 201 and r.json()["multiplier"] == 2.0
    promos = client.get("/api/v1/promotions", headers=H(owner)).json()
    assert any(p["label"] == "Weekend 2x" for p in promos)


def test_staff_cannot_create_promotion(client, db):
    w = make_world(db)
    staff = staff_token(client, w.staff_email)  # lacks campaign.manage
    r = client.post("/api/v1/promotions", headers=H(staff), json={"label": "x", "multiplier": 2})
    assert r.status_code == 403


def test_cannot_deactivate_other_merchants_promotion(client, db):
    a = make_world(db, name="PromoA", token_suffix="PA")
    b = make_world(db, name="PromoB", token_suffix="PB")
    promo_b = promo_service.create_promotion(db, merchant_id=b.merchant_id, label="B promo", multiplier=2,
                                             starts_on=None, ends_on=None)
    db.commit()
    owner_a = staff_token(client, a.owner_email)
    # A tries to deactivate B's promo (targeting B's merchant) → 403 at the scope guard
    r = client.delete(f"/api/v1/promotions/{promo_b['id']}?merchant_id={b.merchant_id}", headers=H(owner_a))
    assert r.status_code == 403
    # …and via A's own scope the promo isn't found (belongs to B) → 404
    r2 = client.delete(f"/api/v1/promotions/{promo_b['id']}", headers=H(owner_a))
    assert r2.status_code == 404
