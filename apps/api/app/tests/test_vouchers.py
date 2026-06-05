"""Voucher core: cashier redeems a voucher (scan/enter code) → marks it used + applies the $ value to
the order; single-use; right-tenant; expiry; min-spend; per-period cap; preview is non-mutating."""
from datetime import timedelta

from sqlalchemy import select

from app.db.base import utcnow
from app.models.loyalty import RewardRedemption
from app.models.org import PATH_SEP, OrgNode
from app.models.tenancy import Merchant
from app.services import vouchers
from app.tests.factories import make_world
from app.tests.helpers import H, place_order, register_customer, staff_token


def _issue(db, customer_id, mid, **kw):
    kw.setdefault("name", "$1 off")
    kw.setdefault("value", 1)
    return vouchers.issue_vouchers(db, customer_id=customer_id, merchant_id=mid, **kw)


def _redeem(client, otok, code, **body):
    return client.post(f"/api/v1/vouchers/{code}/redeem", json=body, headers=H(otok))


def test_redeem_applies_discount_and_marks_used(client, db):
    w = make_world(db)
    cust = register_customer(client, email="v1@b.sg", phone="+6590000401")
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    code = _issue(db, cust["customer"]["id"], w.merchant_id, value=1)[0].voucher_code
    db.commit()
    otok = staff_token(client, w.owner_email)

    r = _redeem(client, otok, code, order_id=order["id"])
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["status"] == "redeemed" and float(b["discount_amount"]) == 1.0
    assert round(float(b["order_total"]), 2) == round(order["total"] - 1.0, 2)
    # single-use: second redeem blocked
    r2 = _redeem(client, otok, code, order_id=order["id"])
    assert r2.status_code == 409 and r2.json()["error"]["code"] == "voucher_used"


def test_wrong_merchant_not_found(client, db):
    w1 = make_world(db, name="M1", token_suffix="1")
    w2 = make_world(db, name="M2", token_suffix="2")
    cust = register_customer(client, email="v2@b.sg", phone="+6590000402")
    code = _issue(db, cust["customer"]["id"], w1.merchant_id)[0].voucher_code
    db.commit()
    r = _redeem(client, staff_token(client, w2.owner_email), code, merchant_id=w2.merchant_id)
    assert r.status_code == 404 and r.json()["error"]["code"] == "voucher_not_found"


def test_expired_voucher_blocked(client, db):
    w = make_world(db)
    cust = register_customer(client, email="v3@b.sg", phone="+6590000403")
    code = _issue(db, cust["customer"]["id"], w.merchant_id, valid_until=utcnow() - timedelta(days=1))[0].voucher_code
    db.commit()
    r = _redeem(client, staff_token(client, w.owner_email), code, merchant_id=w.merchant_id)
    assert r.status_code == 409 and r.json()["error"]["code"] == "voucher_expired"


def test_min_spend_blocked(client, db):
    w = make_world(db)
    cust = register_customer(client, email="v4@b.sg", phone="+6590000404")
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    code = _issue(db, cust["customer"]["id"], w.merchant_id, min_spend=1000)[0].voucher_code
    db.commit()
    r = _redeem(client, staff_token(client, w.owner_email), code, order_id=order["id"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "voucher_min_spend"


def test_per_period_cap_one_per_day(client, db):
    w = make_world(db)
    cust = register_customer(client, email="v5@b.sg", phone="+6590000405")
    vs = vouchers.issue_vouchers(db, customer_id=cust["customer"]["id"], merchant_id=w.merchant_id,
                                 name="$1 welcome", value=1, count=3, per_period="day", campaign_id="welcome10")
    db.commit()
    otok = staff_token(client, w.owner_email)
    assert _redeem(client, otok, vs[0].voucher_code, merchant_id=w.merchant_id).status_code == 200
    r2 = _redeem(client, otok, vs[1].voucher_code, merchant_id=w.merchant_id)
    assert r2.status_code == 409 and r2.json()["error"]["code"] == "voucher_period_limit"


def test_welcome_pack_issued_on_registration(client, db):
    """The user scenario: 10× $1 vouchers granted on signup, one usable per day (a welcome CAMPAIGN)."""
    w = make_world(db)
    m = db.get(Merchant, w.merchant_id)
    m.settings = {**(m.settings or {}), "welcome_voucher": {
        "enabled": True, "count": 10, "value": 1, "per_period": "day", "valid_days": 30, "name": "$1 Welcome"}}
    db.commit()
    r = client.post("/api/v1/auth/customer/register", json={
        "email": "wp@b.sg", "password": "secret123", "accepted_terms": True, "consent_merchant_id": w.merchant_id})
    assert r.status_code == 201, r.text
    vs = db.scalars(select(RewardRedemption).where(
        RewardRedemption.campaign_id == f"welcome:{w.merchant_id}")).all()
    assert len(vs) == 10
    assert all(float(v.value) == 1.0 and v.per_period == "day" and v.status == "issued" for v in vs)


def test_no_welcome_pack_when_unconfigured(client, db):
    w = make_world(db)   # no welcome_voucher setting
    r = client.post("/api/v1/auth/customer/register", json={
        "email": "nowp@b.sg", "password": "secret123", "accepted_terms": True, "consent_merchant_id": w.merchant_id})
    assert r.status_code == 201
    vs = db.scalars(select(RewardRedemption).where(RewardRedemption.merchant_id == w.merchant_id)).all()
    assert vs == []


def _node(db, nid, parent, path, mid, *, sells):
    db.add(OrgNode(id=nid, parent_id=parent, role="STOREFRONT" if sells else "CHAIN", name=nid,
                   depth=path.count(PATH_SEP), path=path, sells=sells, chain_stopped=False,
                   is_settlement_boundary=(parent is None), is_loyalty_domain=(parent is None),
                   settlement_account_id=mid, loyalty_domain_id=mid, is_active=True))


def test_scope_subtree_redemption(client, db):
    """A voucher scoped to one node is redeemable only within that node's subtree (1 leaf vs parent)."""
    w = make_world(db)
    mid, sf1 = w.merchant_id, w.menu.id
    _node(db, mid, None, mid, mid, sells=False)                              # tenant
    _node(db, sf1, mid, f"{mid}{PATH_SEP}{sf1}", mid, sells=True)            # the order's storefront
    _node(db, "s2node", mid, f"{mid}{PATH_SEP}s2node", mid, sells=True)      # a sibling storefront
    db.commit()
    cust = register_customer(client, email="sc@b.sg", phone="+6590000501")
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    otok = staff_token(client, w.owner_email)
    cid = cust["customer"]["id"]

    bad = vouchers.issue_vouchers(db, customer_id=cid, merchant_id=mid, name="$1", value=1, scope_node_id="s2node")[0]
    db.commit()
    r = _redeem(client, otok, bad.voucher_code, order_id=order["id"])
    assert r.status_code == 409 and r.json()["error"]["code"] == "voucher_wrong_store"   # scoped to sibling

    for scope in (mid, sf1):  # tenant-wide and leaf-exact both valid at this storefront
        v = vouchers.issue_vouchers(db, customer_id=cid, merchant_id=mid, name="$1", value=1, scope_node_id=scope)[0]
        db.commit()
        # fresh order each time (an order takes only one voucher)
        o = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
        assert _redeem(client, otok, v.voucher_code, order_id=o["id"]).status_code == 200, scope


def test_settings_welcome_voucher_roundtrip(client, db):
    """The welcome pack is configurable via the Settings API (not just the DB)."""
    w = make_world(db)
    otok = staff_token(client, w.owner_email)
    r = client.patch("/api/v1/org/settings", json={"welcome_voucher": {
        "enabled": True, "count": 5, "value": 1, "per_period": "day", "valid_days": 30, "name": "$1 Welcome"}},
        headers=H(otok))
    assert r.status_code == 200, r.text
    assert r.json()["welcome_voucher"]["enabled"] is True and r.json()["welcome_voucher"]["count"] == 5
    g = client.get("/api/v1/org/settings", headers=H(otok)).json()
    assert g["welcome_voucher"]["value"] == 1.0 and g["welcome_voucher"]["per_period"] == "day"


def test_campaign_id_column_fits_welcome_synthetic():
    """Regression (Postgres VARCHAR vs SQLite): campaign_id must hold "welcome:{32-hex merchant id}"."""
    assert RewardRedemption.__table__.c.campaign_id.type.length >= len("welcome:") + 32


def test_preview_does_not_consume(client, db):
    w = make_world(db)
    cust = register_customer(client, email="v6@b.sg", phone="+6590000406")
    v = _issue(db, cust["customer"]["id"], w.merchant_id, value=2)[0]
    db.commit()
    otok = staff_token(client, w.owner_email)
    r = client.get(f"/api/v1/vouchers/{v.voucher_code}?merchant_id={w.merchant_id}", headers=H(otok))
    assert r.status_code == 200 and r.json()["valid"] is True and float(r.json()["value"]) == 2.0
    db.expire_all()
    assert db.get(RewardRedemption, v.id).status == "issued"   # dry-run never consumes
