"""POS staff (kind='pos') — SEGREGATED from web logins:
- a new Storefront auto-provisions a 5-person team (1 manager + 4 cashiers) with one-time PINs;
- PIN-login is scoped per storefront (the bound outlet) and suspend-aware;
- POS users cannot web-login; web users are not resolvable by PIN;
- reset mints a fresh PIN (revealed once) and invalidates the old one.
"""
from sqlalchemy import select

from app.models.identity import User
from app.models.tenancy import Merchant
from app.seed_breadtalk import build_breadtalk
from app.tests.factories import super_admin
from app.tests.helpers import H, staff_token


def _root(client, db):
    build_breadtalk(db); super_admin(db)
    return staff_token(client, "root@platform.sg")


def _create_sf(client, t, name="POS Test SF", parent="b_tb"):
    r = client.post("/api/v1/org/nodes",
                    json={"parent_id": parent, "role": "STOREFRONT", "name": name}, headers=H(t))
    assert r.status_code == 201, r.text
    return r.json()


def _pin_login(client, merchant_id, outlet_id, pin):
    return client.post("/api/v1/auth/staff/pin-login",
                       json={"merchant_id": merchant_id, "outlet_id": outlet_id, "pin": pin})


def test_storefront_autoprovisions_pos_team(client, db):
    t = _root(client, db)
    sf = _create_sf(client, t)
    team = sf["pos_team"]
    assert len(team) == 5
    assert sorted(m["role"] for m in team) == ["cashier", "cashier", "cashier", "cashier", "manager"]
    pins = [m["pin"] for m in team]
    assert all(len(p) == 6 and p.isdigit() for p in pins)
    assert len(set(pins)) == 5                       # unique within the storefront
    # PIN-login works with the bound outlet + a team PIN
    r = _pin_login(client, "m1", sf["outlet_id"], pins[0])
    assert r.status_code == 200 and r.json()["actor"] == "user"
    assert _pin_login(client, "m1", sf["outlet_id"], "000000").status_code in (401,)  # wrong PIN


def test_pin_is_scoped_per_storefront(client, db):
    t = _root(client, db)
    a = _create_sf(client, t, name="SF A")
    b = _create_sf(client, t, name="SF B")
    pin_a = a["pos_team"][0]["pin"]
    assert _pin_login(client, "m1", a["outlet_id"], pin_a).status_code == 200
    # the SAME pin string must NOT authenticate at a different storefront's till
    assert _pin_login(client, "m1", b["outlet_id"], pin_a).status_code == 401


def test_pos_user_cannot_web_login(client, db):
    """The kind='pos' gate blocks web login even if the account somehow had a valid password."""
    from app.auth import service as auth_service
    from app.core.security import hash_password

    t = _root(client, db)
    _create_sf(client, t)
    u = db.scalar(select(User).where(User.kind == "pos"))
    assert u is not None and u.email.endswith("@pos.local")
    u.password_hash = hash_password("Known123!"); db.commit()   # give it a real password…
    try:
        auth_service.login_user(db, email=u.email, password="Known123!")
        assert False, "POS account must never web-login"
    except Exception as e:                                       # …still rejected by the kind gate
        assert getattr(e, "code", "") == "invalid_credentials"


def test_web_user_cannot_pin_login(client, db):
    t = _root(client, db)
    sf = _create_sf(client, t)
    # a web node-account (kind='web') is never resolvable by PIN, even with a 6-digit guess
    client.post(f"/api/v1/org/nodes/{sf['id']}/accounts",
                json={"email": "web@bt.sg", "password": "Password123!", "full_name": "Web",
                      "role": "manager"}, headers=H(t))
    web = db.scalar(select(User).where(User.email == "web@bt.sg"))
    assert web.kind == "web" and web.pin_hash is None


def test_reset_pin_reveals_new_and_invalidates_old(client, db):
    t = _root(client, db)
    sf = _create_sf(client, t)
    m = sf["pos_team"][1]
    old = m["pin"]
    r = client.post(f"/api/v1/org/nodes/{sf['id']}/pos-staff/{m['user_id']}/reset-pin", headers=H(t))
    assert r.status_code == 200, r.text
    new = r.json()["pin"]
    assert new != old and len(new) == 6
    assert _pin_login(client, "m1", sf["outlet_id"], old).status_code == 401   # old killed
    assert _pin_login(client, "m1", sf["outlet_id"], new).status_code == 200   # new works


def test_add_and_delete_pos_staff(client, db):
    t = _root(client, db)
    sf = _create_sf(client, t)
    base = f"/api/v1/org/nodes/{sf['id']}/pos-staff"
    assert len(client.get(base, headers=H(t)).json()) == 5
    add = client.post(base, json={"full_name": "Extra Cashier", "role": "cashier"}, headers=H(t))
    assert add.status_code == 201
    new_pin, uid = add.json()["pin"], add.json()["user_id"]
    assert len(client.get(base, headers=H(t)).json()) == 6
    assert _pin_login(client, "m1", sf["outlet_id"], new_pin).status_code == 200
    assert client.delete(f"{base}/{uid}", headers=H(t)).status_code == 204
    assert len(client.get(base, headers=H(t)).json()) == 5
    assert _pin_login(client, "m1", sf["outlet_id"], new_pin).status_code == 401   # gone


def test_pin_login_blocked_when_suspended(client, db):
    t = _root(client, db)
    sf = _create_sf(client, t)
    pin = sf["pos_team"][0]["pin"]
    db.get(Merchant, "m1").is_active = False; db.commit()
    r = _pin_login(client, "m1", sf["outlet_id"], pin)
    assert r.status_code == 403 and r.json()["error"]["code"] == "account_suspended"
