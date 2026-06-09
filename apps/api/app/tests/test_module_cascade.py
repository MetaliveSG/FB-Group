"""Per-node module flags — BINARY + parent-gated: a module is ON for a node only if the node AND
every ancestor have it ON (`effective = AND of own-flags up the path`). Turning a node OFF locks its
whole subtree OFF; a child can NOT override a parent's OFF back ON. node=None → Merchant.settings."""
from app.models.org import OrgNode
from app.seed_breadtalk import build_breadtalk
from app.services import boundaries
from app.tests.factories import make_world
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token


def _attach_node(db, w, **flags):
    """Give a make_world outlet a storefront OrgNode (id == menu.id) so per-node flags resolve.
    Defaults every module ON (an established storefront); pass mod_*=False to disable one."""
    mods = {"mod_rewards": True, "mod_qr_ordering": True, "mod_pos": True, **flags}
    n = OrgNode(id=w.menu.id, parent_id=None, role="STOREFRONT", depth=0, path=w.menu.id,
                sells=True, is_settlement_boundary=True, is_loyalty_domain=True,
                loyalty_domain_id=w.merchant_id, settlement_account_id=w.merchant_id, **mods)
    db.add(n)
    db.commit()
    return n


def test_resolve_modules_parent_gated(db):
    build_breadtalk(db)
    sf = db.get(OrgNode, "o_bt_ion")        # a storefront under tenant m1
    tenant = db.get(OrgNode, "m1")
    sib = db.get(OrgNode, "o_tb_tamp")      # another storefront under m1
    assert sf is not None and tenant is not None and "m1" in sf.path.split(".")

    # Seed builds an established merchant → rewards/qr/pos ON; wallet stays opt-in OFF.
    r = boundaries.resolve_modules(db, node=sf, merchant_id="m1")
    assert r == {"rewards_enabled": True, "qr_ordering_enabled": True, "pos_enabled": True,
                 "wallet_enabled": False}

    # Turn POS OFF at the tenant → every storefront in the subtree is locked OFF (parent-gated).
    tenant.mod_pos = False
    db.flush()
    assert boundaries.resolve_modules(db, node=sf, merchant_id="m1")["pos_enabled"] is False
    assert boundaries.resolve_modules(db, node=sib, merchant_id="m1")["pos_enabled"] is False

    # A storefront CANNOT override POS back ON while the parent is OFF (the key binary rule).
    sf.mod_pos = True
    db.flush()
    assert boundaries.resolve_modules(db, node=sf, merchant_id="m1")["pos_enabled"] is False

    # Other flags untouched by the POS gate.
    out = boundaries.resolve_modules(db, node=sf, merchant_id="m1")
    assert out["rewards_enabled"] is True and out["qr_ordering_enabled"] is True

    # node=None → pure legacy fallback (Merchant.settings → defaults: rewards/qr/pos ON, wallet OFF).
    assert boundaries.resolve_modules(db, node=None, merchant_id="m1") == {
        "rewards_enabled": True, "qr_ordering_enabled": True, "pos_enabled": True,
        "wallet_enabled": False}


# --- enforcement reads the node cascade (a node OFF disables that capability) --------------------
def test_node_off_disables_earn(client, db):
    w = make_world(db, earn_rate=1)
    _attach_node(db, w, mod_rewards=False)        # Intelligence OFF at the node (ordering/pos stay ON)
    cust = register_customer(client, email="ne1@b.sg")
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": w.burger_id, "quantity": 1}])
    res = checkout(client, cust["access_token"], order["id"])
    assert res["points_earned"] == 0              # node OFF → no accrual


def test_node_off_disables_qr_ordering(client, db):
    w = make_world(db)
    _attach_node(db, w, mod_qr_ordering=False)     # Table QR OFF at the node
    cust = register_customer(client, email="nq1@b.sg")
    r = client.post("/api/v1/orders",
                    json={"qr_token": w.qr_token, "items": [{"menu_item_id": w.burger_id, "quantity": 1}]},
                    headers=H(cust["access_token"]))
    assert r.status_code == 409 and r.json()["error"]["code"] == "ordering_disabled"


# --- the per-node toggle endpoint (GET own on/off + resolved + parent_enabled; PUT to change) ----
def test_node_modules_endpoint(client, db):
    build_breadtalk(db)
    ceo = H(staff_token(client, "ceo@breadtalk.sg"))
    # default (seeded): own=on, resolved=on
    r = client.get("/api/v1/org/nodes/o_bt_ion/modules", headers=ceo)
    assert r.status_code == 200
    assert r.json()["pos"] is True and r.json()["resolved"]["pos_enabled"] is True
    assert r.json()["parent_enabled"]["pos_enabled"] is True
    assert r.json()["wallet"] is False and r.json()["resolved"]["wallet_enabled"] is False   # wallet opt-in
    # toggle POS off at the storefront
    s = client.put("/api/v1/org/nodes/o_bt_ion/modules", json={"pos": False}, headers=ceo)
    assert s.status_code == 200
    assert s.json()["pos"] is False and s.json()["resolved"]["pos_enabled"] is False
    # GET reflects the change; other modules untouched (still on)
    g = client.get("/api/v1/org/nodes/o_bt_ion/modules", headers=ceo).json()
    assert g["pos"] is False and g["rewards"] is True and g["resolved"]["rewards_enabled"] is True


def test_node_modules_endpoint_parent_gate(client, db):
    """A storefront shows pos OFF when the tenant turns POS off — and parent_enabled flags it locked."""
    build_breadtalk(db)
    ceo = H(staff_token(client, "ceo@breadtalk.sg"))
    client.put("/api/v1/org/nodes/m1/modules", json={"pos": False}, headers=ceo)   # tenant OFF
    g = client.get("/api/v1/org/nodes/o_bt_ion/modules", headers=ceo).json()
    assert g["pos"] is True                               # the storefront's OWN flag is still on…
    assert g["resolved"]["pos_enabled"] is False          # …but the effective value is gated OFF
    assert g["parent_enabled"]["pos_enabled"] is False    # parent is OFF → UI greys/locks it


# --- Wallet (4th module): opt-in (default off), parent-gated, AND additionally gated by Table QR ---
def test_wallet_module_gated_by_qr_and_parent(db):
    build_breadtalk(db)
    sf = db.get(OrgNode, "o_bt_ion")
    tenant = db.get(OrgNode, "m1")

    # Seed leaves wallet OFF everywhere (opt-in) even though qr/rewards/pos are ON.
    assert boundaries.resolve_modules(db, node=sf, merchant_id="m1")["wallet_enabled"] is False

    # Turn wallet ON along the whole path → resolved wallet ON (qr is ON from the seed).
    for nid in sf.path.split("."):
        db.get(OrgNode, nid).mod_wallet = True
    db.flush()
    assert boundaries.resolve_modules(db, node=sf, merchant_id="m1")["wallet_enabled"] is True

    # QR-gate: turn Table QR OFF at the storefront → wallet is forced OFF (money needs an ordering channel).
    sf.mod_qr_ordering = False
    db.flush()
    assert boundaries.resolve_modules(db, node=sf, merchant_id="m1")["wallet_enabled"] is False
    sf.mod_qr_ordering = True
    db.flush()

    # Parent-gate: tenant wallet OFF → storefront wallet OFF even though its own flag is ON.
    tenant.mod_wallet = False
    db.flush()
    assert boundaries.resolve_modules(db, node=sf, merchant_id="m1")["wallet_enabled"] is False


# --- nav-flags resolves the module set per scope node (drives the dashboard menu show/hide) -------
def test_nav_flags_resolves_per_node(client, db):
    build_breadtalk(db)
    ceo = H(staff_token(client, "ceo@breadtalk.sg"))
    client.put("/api/v1/org/nodes/o_bt_ion/modules", json={"pos": False, "qr_ordering": False}, headers=ceo)
    nf = client.get("/api/v1/org/nav-flags?merchant_id=m1&node_id=o_bt_ion", headers=ceo).json()
    assert nf["pos_enabled"] is False and nf["qr_ordering_enabled"] is False and nf["rewards_enabled"] is True
    # The tenant scope (no node_id) is unaffected by the storefront override.
    nf2 = client.get("/api/v1/org/nav-flags?merchant_id=m1", headers=ceo).json()
    assert nf2["pos_enabled"] is True and nf2["qr_ordering_enabled"] is True
