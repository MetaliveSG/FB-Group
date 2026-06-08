"""POS staff (kind='pos') — SEGREGATED from web logins:
- a new Storefront auto-provisions a 3-person team (1 supervisor + 2 cashiers);
- PINs are READABLE (owner-viewable) and listed; the owner can set a chosen PIN or auto-generate;
- PIN-login is scoped per storefront (the bound outlet) and suspend-aware;
- POS users cannot web-login; web users are not resolvable by PIN.
"""
from sqlalchemy import select

from app.models.identity import User
from app.models.org import OrgNode
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
    assert len(team) == 3
    assert sorted(m["role"] for m in team) == ["cashier", "cashier", "supervisor"]
    pins = [m["pin"] for m in team]
    assert all(len(p) == 6 and p.isdigit() for p in pins)
    assert len(set(pins)) == 3                        # unique within the storefront
    r = _pin_login(client, "m1", sf["outlet_id"], pins[0])
    assert r.status_code == 200 and r.json()["actor"] == "user"
    assert _pin_login(client, "m1", sf["outlet_id"], "000000").status_code == 401  # wrong PIN


def test_pins_are_readable_in_list(client, db):
    """The owner can reveal each operator's current PIN — list returns it, and it logs in."""
    t = _root(client, db)
    sf = _create_sf(client, t)
    rows = client.get(f"/api/v1/org/nodes/{sf['id']}/pos-staff", headers=H(t)).json()
    assert len(rows) == 3 and all(r["pin"] and r["pin_set"] for r in rows)
    # the readable PIN actually authenticates
    assert _pin_login(client, "m1", sf["outlet_id"], rows[0]["pin"]).status_code == 200


def test_pin_encrypted_at_rest(client, db):
    """The PIN column holds Fernet ciphertext (not the plaintext), yet the API reveals it + it logs in."""
    t = _root(client, db)
    sf = _create_sf(client, t)
    shown = sf["pos_team"][0]["pin"]                       # plaintext the owner sees
    uid = sf["pos_team"][0]["user_id"]
    stored = db.scalar(select(User.pin).where(User.id == uid))   # what's actually in the DB
    assert stored and stored != shown and len(stored) > 20       # ciphertext, not the 6-digit PIN
    assert _pin_login(client, "m1", sf["outlet_id"], shown).status_code == 200


def test_owner_can_set_a_chosen_pin(client, db):
    t = _root(client, db)
    sf = _create_sf(client, t)
    base = f"/api/v1/org/nodes/{sf['id']}/pos-staff"
    uid = sf["pos_team"][0]["user_id"]
    # set a specific PIN
    r = client.post(f"{base}/{uid}/reset-pin", json={"pin": "246813"}, headers=H(t))
    assert r.status_code == 200 and r.json()["pin"] == "246813"
    assert _pin_login(client, "m1", sf["outlet_id"], "246813").status_code == 200
    # a duplicate PIN at the same storefront is rejected
    other = sf["pos_team"][1]["user_id"]
    dup = client.post(f"{base}/{other}/reset-pin", json={"pin": "246813"}, headers=H(t))
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "pin_taken"
    # add an operator with a chosen PIN
    add = client.post(base, json={"full_name": "Chosen", "role": "cashier", "pin": "135799"}, headers=H(t))
    assert add.status_code == 201 and add.json()["pin"] == "135799"
    assert _pin_login(client, "m1", sf["outlet_id"], "135799").status_code == 200


def test_pin_is_scoped_per_storefront(client, db):
    t = _root(client, db)
    a = _create_sf(client, t, name="SF A")
    b = _create_sf(client, t, name="SF B")
    pin_a = a["pos_team"][0]["pin"]
    assert _pin_login(client, "m1", a["outlet_id"], pin_a).status_code == 200
    assert _pin_login(client, "m1", b["outlet_id"], pin_a).status_code == 401   # not at another storefront


def test_pos_user_cannot_web_login(client, db):
    """The kind='pos' gate blocks web login even if the account somehow had a valid password."""
    from app.auth import service as auth_service
    from app.core.security import hash_password

    t = _root(client, db)
    _create_sf(client, t)
    u = db.scalar(select(User).where(User.kind == "pos"))
    assert u is not None and u.email.endswith("@pos.local")
    u.password_hash = hash_password("Known123!"); db.commit()
    try:
        auth_service.login_user(db, email=u.email, password="Known123!")
        assert False, "POS account must never web-login"
    except Exception as e:
        assert getattr(e, "code", "") == "invalid_credentials"


def test_web_user_cannot_pin_login(client, db):
    t = _root(client, db)
    sf = _create_sf(client, t)
    client.post(f"/api/v1/org/nodes/{sf['id']}/accounts",
                json={"email": "web@bt.sg", "password": "Password123!", "full_name": "Web",
                      "role": "manager"}, headers=H(t))
    web = db.scalar(select(User).where(User.email == "web@bt.sg"))
    assert web.kind == "web" and web.pin is None       # web users carry no POS PIN


def test_reset_pin_autogenerate_invalidates_old(client, db):
    t = _root(client, db)
    sf = _create_sf(client, t)
    m = sf["pos_team"][1]
    old = m["pin"]
    r = client.post(f"/api/v1/org/nodes/{sf['id']}/pos-staff/{m['user_id']}/reset-pin", headers=H(t))
    assert r.status_code == 200
    new = r.json()["pin"]
    assert new != old and len(new) == 6
    assert _pin_login(client, "m1", sf["outlet_id"], old).status_code == 401
    assert _pin_login(client, "m1", sf["outlet_id"], new).status_code == 200


def test_add_and_delete_pos_staff(client, db):
    t = _root(client, db)
    sf = _create_sf(client, t)
    base = f"/api/v1/org/nodes/{sf['id']}/pos-staff"
    assert len(client.get(base, headers=H(t)).json()) == 3
    add = client.post(base, json={"full_name": "Extra Cashier", "role": "cashier"}, headers=H(t))
    assert add.status_code == 201
    new_pin, uid = add.json()["pin"], add.json()["user_id"]
    assert len(client.get(base, headers=H(t)).json()) == 4
    assert _pin_login(client, "m1", sf["outlet_id"], new_pin).status_code == 200
    assert client.delete(f"{base}/{uid}", headers=H(t)).status_code == 204
    assert len(client.get(base, headers=H(t)).json()) == 3
    assert _pin_login(client, "m1", sf["outlet_id"], new_pin).status_code == 401


def test_pos_module_off_blocks_pin_login(client, db):
    """The POS module toggle (mod_pos=off at the node) refuses PIN-login — the toggle really gates POS."""
    t = _root(client, db)
    sf = _create_sf(client, t)
    pin = sf["pos_team"][0]["pin"]
    assert _pin_login(client, "m1", sf["outlet_id"], pin).status_code == 200      # default ON
    node = db.get(OrgNode, sf["id"])
    node.mod_pos = False
    db.commit()
    r = _pin_login(client, "m1", sf["outlet_id"], pin)
    assert r.status_code == 403 and r.json()["error"]["code"] == "pos_disabled"   # toggled OFF


def test_node_account_listing_excludes_pos_operators(client, db):
    """The WEB Team listing shows only web-palette roles (manager/viewer/finance). It must skip POS
    operators (kind="pos", @pos.local) AND a POS-role assignment (cashier/supervisor) even on a
    web-kind user (the legacy onboarding anomaly)."""
    from app.core.security import hash_password
    from app.models.enums import RoleName, ScopeType
    from app.models.identity import Role, User, UserRoleAssignment

    t = _root(client, db)
    sf = _create_sf(client, t)                         # auto-provisions 3 POS staff (kind=pos) at this node
    # a web-kind user carrying a POS role (cashier) — must also be excluded from the web Team list
    cashier_role = db.scalar(select(Role).where(Role.name == RoleName.CASHIER.value))
    u = User(email="web.cashier@x.sg", full_name="Web Cashier", kind="web",
             password_hash=hash_password("Password123!"))
    db.add(u)
    db.flush()
    db.add(UserRoleAssignment(user_id=u.id, role_id=cashier_role.id,
                              scope_type=ScopeType.NODE.value, scope_id=sf["id"]))
    db.commit()

    for url in (f"/api/v1/org/nodes/{sf['id']}/accounts",            # node-only (Logins drawer)
                f"/api/v1/org/nodes/{sf['id']}/accounts?subtree=true"):  # subtree (Team page)
        r = client.get(url, headers=H(t))
        assert r.status_code == 200, r.text
        emails = [a["email"] for a in r.json()]
        assert all(not e.endswith("@pos.local") for e in emails)        # POS operators excluded
        assert "web.cashier@x.sg" not in emails                          # web user w/ POS role excluded
        assert all(a["role"] in {"manager", "viewer", "finance"} for a in r.json())


def test_node_scope_resolves_provisioned_outlet(client, db):
    """Regression: a node's RBAC outlet set must include its PROVISIONED outlet (menu.id==node.id,
    separate outlet uuid) — else node-scoped POS staff get 403 outlet_scope when ringing a sale."""
    from app.models.org import OrgNode
    from app.services import org_tree
    t = _root(client, db)
    sf = _create_sf(client, t)
    node = db.get(OrgNode, sf["id"])
    assert sf["outlet_id"] in org_tree.outlet_ids_under(db, node)


def test_pin_login_blocked_when_suspended(client, db):
    t = _root(client, db)
    sf = _create_sf(client, t)
    pin = sf["pos_team"][0]["pin"]
    db.get(Merchant, "m1").is_active = False; db.commit()
    r = _pin_login(client, "m1", sf["outlet_id"], pin)
    assert r.status_code == 403 and r.json()["error"]["code"] == "account_suspended"
