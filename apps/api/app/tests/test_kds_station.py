"""KDS station token — the kitchen tablet authenticates with a private, revocable per-outlet bearer
token (`X-KDS-Token`), NOT a web login. Scoped to ONE outlet (its queue + advancing its tickets)."""
from app.models.org import OrgNode
from app.models.tenancy import Outlet
from app.services import kds_station
from app.tests.factories import make_world, super_admin
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token


def _paid_order(client, db, w, email):
    cust = register_customer(client, email=email)
    order = place_order(client, cust["access_token"], w.qr_token,
                        [{"menu_item_id": w.burger_id, "quantity": 1}])
    checkout(client, cust["access_token"], order["id"])   # → COMPLETED, fulfilment QUEUED
    return order


def _kh(token):
    return {"X-KDS-Token": token}


# --- the station-authed /kds endpoints (no merchant session) ------------------------------------
def test_station_token_serves_only_its_outlet(client, db):
    w = make_world(db, earn_rate=1)
    order = _paid_order(client, db, w, "ks1@b.sg")
    station = kds_station.issue_station(db, outlet=db.get(Outlet, w.outlet_id))
    db.commit()
    tok = station.token

    # context + queue resolve from the token alone (no login).
    ctx = client.get("/api/v1/kds/context", headers=_kh(tok))
    assert ctx.status_code == 200 and ctx.json()["outlet_id"] == w.outlet_id
    q = client.get("/api/v1/kds/queue", headers=_kh(tok)).json()
    assert len(q) == 1 and q[0]["id"] == order["id"] and q[0]["fulfilment_status"] == "queued"

    # advance a ticket via the token.
    r = client.patch(f"/api/v1/kds/orders/{order['id']}/fulfilment", json={"status": "preparing"}, headers=_kh(tok))
    assert r.status_code == 200 and r.json()["fulfilment_status"] == "preparing"


def test_invalid_and_revoked_token_rejected(client, db):
    w = make_world(db)
    station = kds_station.issue_station(db, outlet=db.get(Outlet, w.outlet_id))
    db.commit()
    # unknown token → 401
    assert client.get("/api/v1/kds/queue", headers=_kh("nope")).status_code == 401
    # no token → 401
    assert client.get("/api/v1/kds/queue").status_code == 401
    # revoke → the (previously valid) token stops working
    kds_station.revoke_station(db, outlet_id=w.outlet_id)
    db.commit()
    assert client.get("/api/v1/kds/queue", headers=_kh(station.token)).status_code == 401


def test_station_cannot_touch_another_outlets_order(client, db):
    w1 = make_world(db, name="A", token_suffix="A")
    w2 = make_world(db, name="B", token_suffix="B")
    other = _paid_order(client, db, w2, "ks2@b.sg")          # an order in outlet B
    st1 = kds_station.issue_station(db, outlet=db.get(Outlet, w1.outlet_id))  # station for outlet A
    db.commit()
    r = client.patch(f"/api/v1/kds/orders/{other['id']}/fulfilment", json={"status": "preparing"}, headers=_kh(st1.token))
    assert r.status_code == 404 and r.json()["error"]["code"] == "order_not_found"


# --- the console issue / reveal / rotate / revoke endpoints --------------------------------------
def _attach_sf(db, w):
    db.add(OrgNode(id=w.menu.id, parent_id=None, role="STOREFRONT", depth=0, path=w.menu.id,
                   sells=True, is_settlement_boundary=True, is_loyalty_domain=True,
                   loyalty_domain_id=w.merchant_id, settlement_account_id=w.merchant_id,
                   mod_rewards=True, mod_qr_ordering=True, mod_pos=True))
    db.commit()


def test_console_issue_reveal_rotate_revoke(client, db):
    w = make_world(db)
    _attach_sf(db, w)                # storefront node id == menu.id → resolves to the outlet
    super_admin(db)
    root = H(staff_token(client, "root@platform.sg"))
    nid = w.menu.id

    # none yet
    g = client.get(f"/api/v1/org/nodes/{nid}/kds-station", headers=root).json()
    assert g["token"] is None and g["is_active"] is False
    # issue
    a = client.post(f"/api/v1/org/nodes/{nid}/kds-station", headers=root).json()
    assert a["token"] and a["is_active"] is True and a["outlet_id"] == w.outlet_id
    # reveal returns the same token
    assert client.get(f"/api/v1/org/nodes/{nid}/kds-station", headers=root).json()["token"] == a["token"]
    # the issued token actually works on /kds
    assert client.get("/api/v1/kds/queue", headers=_kh(a["token"])).status_code == 200
    # rotate → new token; the old one stops working
    b = client.post(f"/api/v1/org/nodes/{nid}/kds-station", headers=root).json()
    assert b["token"] != a["token"]
    assert client.get("/api/v1/kds/queue", headers=_kh(a["token"])).status_code == 401
    assert client.get("/api/v1/kds/queue", headers=_kh(b["token"])).status_code == 200
    # revoke → 204, then the token is dead
    assert client.delete(f"/api/v1/org/nodes/{nid}/kds-station", headers=root).status_code == 204
    assert client.get("/api/v1/kds/queue", headers=_kh(b["token"])).status_code == 401
