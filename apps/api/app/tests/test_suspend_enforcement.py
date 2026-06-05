"""Suspend enforcement: a suspended merchant/chain/storefront blocks ORDERS (any channel) and LOGIN
for its staff; suspend CASCADES down the tree; operators are never blocked; un-suspend restores."""
from app.models.org import OrgNode
from app.models.tenancy import Merchant
from app.seed_breadtalk import build_breadtalk
from app.services import org_tree
from app.tests.factories import make_world, super_admin
from app.tests.helpers import H, register_customer, staff_token

ITEMS = lambda w: [{"menu_item_id": w.burger_id, "quantity": 1}]  # noqa: E731


def _order(client, ctok, w):
    return client.post("/api/v1/orders", json={"qr_token": w.qr_token, "items": ITEMS(w)}, headers=H(ctok))


def _suspend(db, mid):
    db.get(Merchant, mid).is_active = False
    db.commit()


def test_order_blocked_when_tenant_suspended(client, db):
    w = make_world(db)
    ctok = register_customer(client, email="s1@b.sg", phone="+6590000301")["access_token"]
    assert _order(client, ctok, w).status_code == 201           # works before suspend
    _suspend(db, w.merchant_id)
    r = _order(client, ctok, w)
    assert r.status_code == 409 and r.json()["error"]["code"] == "store_suspended"


def test_unsuspend_restores_ordering(client, db):
    w = make_world(db)
    ctok = register_customer(client, email="s2@b.sg", phone="+6590000302")["access_token"]
    _suspend(db, w.merchant_id)
    assert _order(client, ctok, w).status_code == 409
    db.get(Merchant, w.merchant_id).is_active = True
    db.commit()
    assert _order(client, ctok, w).status_code == 201


def test_login_blocked_when_merchant_suspended(client, db):
    w = make_world(db)
    assert staff_token(client, w.owner_email)                    # works before
    _suspend(db, w.merchant_id)
    r = client.post("/api/v1/auth/staff/login", json={"email": w.owner_email, "password": "Password123!"})
    assert r.status_code == 403 and r.json()["error"]["code"] == "account_suspended"


def test_operator_login_not_blocked_by_suspend(client, db):
    w = make_world(db)
    super_admin(db)
    _suspend(db, w.merchant_id)
    r = client.post("/api/v1/auth/staff/login", json={"email": "root@platform.sg", "password": "Password123!"})
    assert r.status_code == 200   # operators manage/un-suspend — never locked out


def test_qr_ordering_disabled_when_tenant_suspended(client, db):
    w = make_world(db)
    assert client.get(f"/api/v1/qr/{w.qr_token}").json()["ordering_enabled"] is True
    _suspend(db, w.merchant_id)
    assert client.get(f"/api/v1/qr/{w.qr_token}").json()["ordering_enabled"] is False


def test_suspend_cascades_to_descendants(client, db):
    build_breadtalk(db)
    assert org_tree.is_live(db, db.get(OrgNode, "o_tb_tamp")) is True
    db.get(OrgNode, "b_tb").is_active = False   # suspend a CHAIN
    db.commit()
    db.expire_all()
    assert org_tree.is_live(db, db.get(OrgNode, "o_tb_tamp")) is False   # storefront beneath it → suspended
    assert org_tree.is_live(db, db.get(OrgNode, "o_dtf_para")) is True   # a different branch → unaffected
