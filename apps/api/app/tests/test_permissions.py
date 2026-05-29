"""Module 10 — Admin, Roles & Permissions (matrix + isolation + audit)."""
from sqlalchemy import select

from app.models.audit import AuditLog
from app.tests.factories import add_outlet, make_world, super_admin
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token


def test_super_admin_sees_all_merchants(client, db):
    w1 = make_world(db, name="M1", token_suffix="1")
    w2 = make_world(db, name="M2", token_suffix="2")
    super_admin(db)
    rtok = staff_token(client, "root@platform.sg")
    # Super admin must specify which merchant.
    assert client.get("/api/v1/crm/customers", headers=H(rtok)).status_code == 400
    # ...but can target any merchant.
    assert client.get(f"/api/v1/crm/customers?merchant_id={w1.merchant_id}", headers=H(rtok)).status_code == 200
    assert client.get(f"/api/v1/crm/customers?merchant_id={w2.merchant_id}", headers=H(rtok)).status_code == 200


def test_merchant_owner_cannot_access_other_merchant(client, db):
    w1 = make_world(db, name="M1", token_suffix="1")
    w2 = make_world(db, name="M2", token_suffix="2")
    owner1 = staff_token(client, w1.owner_email)
    r = client.get(f"/api/v1/crm/customers?merchant_id={w2.merchant_id}", headers=H(owner1))
    assert r.status_code == 403


def test_outlet_manager_limited_to_assigned_outlet(client, db):
    w = make_world(db)             # outlet A + outlet_mgr scoped to A
    o2 = add_outlet(db, w, "2")    # outlet B (same merchant)

    # Customer transacts only at outlet B.
    cust = register_customer(client, email="bcust@b.sg")
    order = place_order(client, cust["access_token"], o2.qr_token, [{"menu_item_id": o2.item_id, "quantity": 1}])
    checkout(client, cust["access_token"], order["id"])

    mgr = staff_token(client, w.outlet_mgr_email)   # scoped to outlet A
    owner = staff_token(client, w.owner_email)
    # Outlet-A manager sees no outlet-B customers; owner sees the customer.
    assert client.get("/api/v1/crm/customers", headers=H(mgr)).json() == []
    assert len(client.get("/api/v1/crm/customers", headers=H(owner)).json()) == 1


def test_staff_lacks_crm_permission(client, db):
    w = make_world(db)
    stok = staff_token(client, w.staff_email)
    r = client.get("/api/v1/crm/customers", headers=H(stok))
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"


def test_audit_log_created_for_status_change(client, db):
    w = make_world(db)
    cust = register_customer(client, email="audit@b.sg")
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    stok = staff_token(client, w.staff_email)
    client.patch(f"/api/v1/orders/{order['id']}/status", json={"status": "accepted"}, headers=H(stok))

    logs = db.scalars(select(AuditLog).where(AuditLog.action == "order.status_change")).all()
    assert len(logs) >= 1 and logs[0].entity_id == order["id"]
