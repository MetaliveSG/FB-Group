"""Phase 1c — RBAC cascades down the org subtree via the spine (P0: tenant isolation).

These are written BEFORE wiring the spine into resolve_scope, and must stay green: a role
scoped to a node reaches exactly its subtree's outlets — never a sibling brand's, never
another merchant's.
"""
from sqlalchemy import select

from app.models.enums import RoleName, ScopeType
from app.models.identity import User, UserRoleAssignment
from app.models.catalog import Menu, MenuCategory, MenuItem
from app.models.tenancy import Brand, DiningTable, Outlet, QRCode
from app.auth.permissions import seed_rbac
from app.core.security import hash_password
from app.services import org_tree
from app.tests.factories import make_world
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token

DEMO_PW = "Password123!"


def _second_brand_with_outlet(db, w, *, brand_name="Brand B", suffix="BB"):
    """Add a second brand + outlet (with QR + menu + item) under the SAME merchant."""
    brand = Brand(merchant_id=w.merchant_id, name=brand_name)
    db.add(brand)
    db.flush()
    outlet = Outlet(merchant_id=w.merchant_id, brand_id=brand.id, name=f"Outlet {suffix}")
    db.add(outlet)
    db.flush()
    table = DiningTable(merchant_id=w.merchant_id, outlet_id=outlet.id, label="T01")
    db.add(table)
    db.flush()
    qr = QRCode(merchant_id=w.merchant_id, outlet_id=outlet.id, table_id=table.id, token=f"QR-{suffix}")
    db.add(qr)
    db.flush()
    menu = Menu(merchant_id=w.merchant_id, outlet_id=outlet.id, name="Main")
    db.add(menu)
    db.flush()
    cat = MenuCategory(menu_id=menu.id, name="Mains", sort_order=0)
    db.add(cat)
    db.flush()
    item = MenuItem(category_id=cat.id, name="Satay", price=7.00, is_available=True)
    db.add(item)
    db.flush()
    db.commit()
    return brand, outlet, qr, item


def _brand_manager(db, email, brand_id):
    roles = seed_rbac(db)
    u = User(email=email, full_name=email, password_hash=hash_password(DEMO_PW))
    db.add(u)
    db.flush()
    db.add(UserRoleAssignment(user_id=u.id, role_id=roles[RoleName.BRAND_MANAGER.value].id,
                              scope_type=ScopeType.BRAND.value, scope_id=brand_id))
    db.commit()
    return u


# ---- unit: the cascade primitive is cross-tenant safe -----------------------
def test_outlet_ids_under_brand_is_only_that_brands_outlets(db):
    w = make_world(db)                                   # merchant, brand A, outlet A
    brand_b, outlet_b, _, _ = _second_brand_with_outlet(db, w)
    org_tree.sync_org_tree(db)

    brand_a_node = org_tree.node_for(db, w.brand_id)
    ids = org_tree.outlet_ids_under(db, brand_a_node)
    assert ids == {w.outlet_id}                          # only brand A's outlet
    assert outlet_b.id not in ids                        # never the sibling brand's outlet


def test_outlet_ids_under_merchant_excludes_other_merchant(db):
    a = make_world(db, name="Alpha", token_suffix="A")
    b = make_world(db, name="Beta", token_suffix="B")
    org_tree.sync_org_tree(db)

    a_merchant = org_tree.node_for(db, a.merchant_id)
    ids = org_tree.outlet_ids_under(db, a_merchant)
    assert a.outlet_id in ids and b.outlet_id not in ids  # never another tenant's outlet


# ---- e2e: a brand manager sees only their brand's data ----------------------
def test_brand_manager_limited_to_brand_outlets(client, db):
    w = make_world(db)
    brand_b, outlet_b, qr_b, item_b = _second_brand_with_outlet(db, w)
    org_tree.sync_org_tree(db)
    _brand_manager(db, "bm@brandb.sg", brand_b.id)

    # A customer transacts at brand B's outlet only.
    cust = register_customer(client, email="bb@cust.sg")
    order = place_order(client, cust["access_token"], qr_b.token, [{"menu_item_id": item_b.id, "quantity": 1}])
    checkout(client, cust["access_token"], order["id"])

    bm = staff_token(client, "bm@brandb.sg")        # scoped to brand B
    # Brand-B manager sees the brand-B customer...
    assert len(client.get("/api/v1/crm/customers", headers=H(bm)).json()) == 1
    # ...but the brand-A outlet manager (scoped to outlet A) sees none of brand B's customers.
    mgr_a = staff_token(client, w.outlet_mgr_email)
    assert client.get("/api/v1/crm/customers", headers=H(mgr_a)).json() == []
