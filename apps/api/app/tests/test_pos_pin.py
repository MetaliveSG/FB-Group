"""POS staff PIN: set/reset at the console (manager) → PIN-login at the till; unique per merchant;
suspend-aware; settable at account creation."""
from sqlalchemy import select

from app.models.identity import User
from app.models.tenancy import Merchant
from app.seed_breadtalk import build_breadtalk
from app.tests.factories import super_admin
from app.tests.helpers import H, staff_token


def _uid(db, email):
    return db.scalar(select(User).where(User.email == email)).id


def _set_pin(client, t, node_id, user_id, pin):
    return client.post(f"/api/v1/org/nodes/{node_id}/accounts/{user_id}/pin", json={"pin": pin}, headers=H(t))


def _pin_login(client, merchant_id, pin):
    return client.post("/api/v1/auth/staff/pin-login", json={"merchant_id": merchant_id, "pin": pin})


def test_set_pin_then_pin_login(client, db):
    build_breadtalk(db); super_admin(db)
    t = staff_token(client, "root@platform.sg")
    uid = _uid(db, "cashier.ion@breadtalk.sg")
    assert _set_pin(client, t, "o_bt_ion", uid, "1234").status_code == 204
    r = _pin_login(client, "m1", "1234")
    assert r.status_code == 200 and r.json()["user"]["email"] == "cashier.ion@breadtalk.sg"
    assert _pin_login(client, "m1", "9999").status_code == 401   # wrong PIN


def test_pin_unique_per_merchant(client, db):
    build_breadtalk(db); super_admin(db)
    t = staff_token(client, "root@platform.sg")
    assert _set_pin(client, t, "o_bt_ion", _uid(db, "cashier.ion@breadtalk.sg"), "4321").status_code == 204
    r = _set_pin(client, t, "b_tb", _uid(db, "mgr.toastbox@breadtalk.sg"), "4321")   # same merchant m1
    assert r.status_code == 409 and r.json()["error"]["code"] == "pin_taken"


def test_pin_login_blocked_when_suspended(client, db):
    build_breadtalk(db); super_admin(db)
    t = staff_token(client, "root@platform.sg")
    _set_pin(client, t, "o_bt_ion", _uid(db, "cashier.ion@breadtalk.sg"), "5678")
    db.get(Merchant, "m1").is_active = False; db.commit()
    r = _pin_login(client, "m1", "5678")
    assert r.status_code == 403 and r.json()["error"]["code"] == "account_suspended"


def test_create_node_account_with_pin(client, db):
    build_breadtalk(db); super_admin(db)
    t = staff_token(client, "root@platform.sg")
    r = client.post("/api/v1/org/nodes/o_bt_ion/accounts",
                    json={"email": "newcashier@bt.sg", "password": "Password123!", "full_name": "New",
                          "role": "cashier", "pin": "2468"}, headers=H(t))
    assert r.status_code == 201 and r.json()["pin_set"] is True
    assert _pin_login(client, "m1", "2468").status_code == 200


def test_bad_pin_rejected(client, db):
    build_breadtalk(db); super_admin(db)
    t = staff_token(client, "root@platform.sg")
    uid = _uid(db, "cashier.ion@breadtalk.sg")
    assert _set_pin(client, t, "o_bt_ion", uid, "12").status_code == 422        # too short (schema)
    assert _set_pin(client, t, "o_bt_ion", uid, "abcd").status_code == 422       # non-digit
