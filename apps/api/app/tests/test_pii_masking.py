"""Field-level PII masking (PII governance P1).

Owner + operators-with-full-access see raw phone/email/birthday; brand/outlet managers and
read-only operators see masked values (but can still use the CRM). Masking is presentation-
only — the stored data is unchanged.
"""
from app.auth.permissions import seed_rbac
from app.core.security import hash_password
from app.models.enums import ScopeType
from app.models.identity import User, UserRoleAssignment
from app.tests.factories import make_world, super_admin
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token

RAW_EMAIL = "masktest@b.sg"
RAW_PHONE = "+6581234567"
RAW_BDAY = "1990-05-15"


def _capture(client, w):
    """Register a customer with known PII + run the capture loop so they land in the CRM."""
    tok = register_customer(client, email=RAW_EMAIL, phone=RAW_PHONE,
                            full_name="Mask Test", birthday=RAW_BDAY)["access_token"]
    order = place_order(client, tok, w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    checkout(client, tok, order["id"])


def _find(rows):
    return next(r for r in rows if r["full_name"] == "Mask Test")


def test_owner_sees_raw_pii(client, db):
    w = make_world(db)
    _capture(client, w)
    otok = staff_token(client, w.owner_email)
    row = _find(client.get("/api/v1/crm/customers", headers=H(otok)).json())
    assert row["email"] == RAW_EMAIL and row["phone"] == RAW_PHONE
    prof = client.get(f"/api/v1/crm/customers/{row['id']}", headers=H(otok)).json()
    assert prof["customer"]["birthday"] == RAW_BDAY
    assert prof["customer"]["email"] == RAW_EMAIL and prof["customer"]["phone"] == RAW_PHONE


def test_outlet_manager_sees_masked_pii(client, db):
    w = make_world(db)
    _capture(client, w)
    mtok = staff_token(client, w.outlet_mgr_email)  # has crm.view, NOT crm.pii.view
    row = _find(client.get("/api/v1/crm/customers", headers=H(mtok)).json())
    # Masked, not raw — but still identifiable by name + a tail.
    assert row["email"] == "m•••@b.sg" and row["email"] != RAW_EMAIL
    assert row["phone"] == "+65•••4567" and row["phone"] != RAW_PHONE
    assert row["full_name"] == "Mask Test"  # name stays visible
    prof = client.get(f"/api/v1/crm/customers/{row['id']}", headers=H(mtok)).json()
    assert prof["customer"]["birthday"] is None  # birthday hidden when masked
    assert prof["customer"]["email"] == "m•••@b.sg"


def test_operator_sees_raw_pii(client, db):
    w = make_world(db)
    _capture(client, w)
    super_admin(db)
    rtok = staff_token(client, "root@platform.sg")
    row = _find(client.get(f"/api/v1/crm/customers?merchant_id={w.merchant_id}", headers=H(rtok)).json())
    assert row["email"] == RAW_EMAIL and row["phone"] == RAW_PHONE


def test_readonly_operator_sees_masked_pii(client, db):
    """A Support operator drills in read-only → masked (crm.pii.view not in its read perms)."""
    w = make_world(db)
    _capture(client, w)
    roles = seed_rbac(db)
    u = User(email="sup@platform.sg", full_name="sup", password_hash=hash_password("Password123!"))
    db.add(u)
    db.flush()
    db.add(UserRoleAssignment(user_id=u.id, role_id=roles["platform_support"].id,
                              scope_type=ScopeType.PLATFORM.value, scope_id=None))
    db.commit()
    stok = staff_token(client, "sup@platform.sg")
    row = _find(client.get(f"/api/v1/crm/customers?merchant_id={w.merchant_id}", headers=H(stok)).json())
    assert row["email"] == "m•••@b.sg" and row["phone"] == "+65•••4567"
