"""Foodcourt: an outlet hosting many stalls (menus). QR resolve returns the stall
directory; single-stall outlets stay inline (backward compat); a token can only reach
menus at its own outlet."""
from app.seed import seed_foodhall
from app.tests.factories import make_world


def test_single_outlet_returns_one_stall_with_inline_menu(client, db):
    w = make_world(db)
    r = client.get(f"/api/v1/qr/{w.qr_token}").json()
    assert r["is_foodcourt"] is False
    assert len(r["stalls"]) == 1
    assert r["menu"] is not None and r["menu"]["categories"]   # full menu inline (no extra fetch)
    assert r.get("parent_group") is None                       # standalone storefront → no "up" control


def test_foodcourt_returns_stall_directory_and_null_menu(client, db):
    seed_foodhall(db)
    r = client.get("/api/v1/qr/foodhall-01").json()
    assert r["is_foodcourt"] is True
    assert len(r["stalls"]) == 3
    assert r["menu"] is None                                   # foodcourt → fetch a stall on tap
    names = {s["stall_name"] for s in r["stalls"]}
    assert "Ah Hock Noodle Bar" in names
    assert all(s["item_count"] > 0 for s in r["stalls"])       # each stall has items + a count


def test_stall_menu_fetch_and_cross_outlet_isolation(client, db):
    seed_foodhall(db)
    ctx = client.get("/api/v1/qr/foodhall-01").json()
    mid = ctx["stalls"][0]["menu_id"]
    ok = client.get(f"/api/v1/qr/foodhall-01/menu/{mid}")
    assert ok.status_code == 200 and ok.json()["categories"]

    # a menu from a DIFFERENT outlet must NOT be reachable via the foodhall token
    other = make_world(db, name="Other Co", token_suffix="OTH")
    other_menu_id = client.get(f"/api/v1/qr/{other.qr_token}").json()["menu"]["id"]
    bad = client.get(f"/api/v1/qr/foodhall-01/menu/{other_menu_id}")
    assert bad.status_code == 404 and bad.json()["error"]["code"] == "menu_not_found"
