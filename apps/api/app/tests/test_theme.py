"""Brand theme — partial, cascade-MERGED (root→node, nearest wins per key). An enterprise sets a house
style; a brand/outlet overrides only the keys it sets. Drives the customer app's CSS-var overrides."""
from app.models.org import OrgNode
from app.seed_breadtalk import build_breadtalk
from app.services import boundaries
from app.tests.factories import make_world
from app.tests.helpers import H, staff_token


def test_theme_cascade_merges_partial(db):
    build_breadtalk(db)
    tenant = db.get(OrgNode, "m1")
    sf = db.get(OrgNode, "o_bt_ion")
    # enterprise/tenant house style
    boundaries.set_node_theme(db, tenant, {"primary": "#bd2d0c", "logo_url": "https://x/bt.png"})
    r = boundaries.resolve_theme(db, node=sf)
    assert r["primary"] == "#bd2d0c" and r["logo_url"] == "https://x/bt.png"   # storefront inherits
    # storefront overrides ONLY the colour → keeps the inherited logo (per-key merge)
    boundaries.set_node_theme(db, sf, {"primary": "#1d4ed8"})
    r2 = boundaries.resolve_theme(db, node=sf)
    assert r2["primary"] == "#1d4ed8" and r2["logo_url"] == "https://x/bt.png"
    # unknown keys are dropped; empty → inherit (clear)
    boundaries.set_node_theme(db, sf, {"primary": "#0a0", "evil": "x"})
    assert "evil" not in boundaries.resolve_theme(db, node=sf)
    boundaries.set_node_theme(db, sf, None)
    assert boundaries.resolve_theme(db, node=sf)["primary"] == "#bd2d0c"        # back to tenant's


def test_theme_endpoint_and_qr_context(client, db):
    build_breadtalk(db)
    ceo = H(staff_token(client, "ceo@breadtalk.sg"))
    g = client.get("/api/v1/org/nodes/m1/theme", headers=ceo).json()
    assert g["own"] is None and g["resolved"] == {}
    s = client.put("/api/v1/org/nodes/m1/theme", json={"theme": {"primary": "#e23a0f"}}, headers=ceo).json()
    assert s["own"] == {"primary": "#e23a0f"} and s["resolved"]["primary"] == "#e23a0f"

    # the resolved theme rides the public QR context (the customer app reads it)
    w = make_world(db)
    db.add(OrgNode(id=w.menu.id, parent_id=None, role="STOREFRONT", depth=0, path=w.menu.id, sells=True,
                   is_settlement_boundary=True, is_loyalty_domain=True, loyalty_domain_id=w.merchant_id,
                   settlement_account_id=w.merchant_id, mod_rewards=True, mod_qr_ordering=True, mod_pos=True,
                   theme={"primary": "#7c3aed"}))
    db.commit()
    ctx = client.get(f"/api/v1/qr/{w.qr_token}").json()
    assert ctx["theme"]["primary"] == "#7c3aed"
