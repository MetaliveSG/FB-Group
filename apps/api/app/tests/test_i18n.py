"""i18n foundation — locale resolution, content localisation (fallback-to-canonical), currency carry."""
from app.services import i18n
from app.tests.factories import make_world


# --- Unit: locale normalisation + resolution chain ---------------------------------------------
def test_normalize_locale_is_tolerant_and_clamps():
    assert i18n.normalize_locale("EN") == "en"
    assert i18n.normalize_locale("en-US") == "en"          # region stripped to primary
    assert i18n.normalize_locale("zh_CN") == "zh"          # underscore + region
    assert i18n.normalize_locale("en-SG") == "en-SG"       # Singlish preserved (exact supported)
    assert i18n.normalize_locale("fr") == "en"             # unsupported → default
    assert i18n.normalize_locale(None) == "en"
    assert i18n.normalize_locale("") == "en"


def test_resolve_locale_priority_chain():
    # override beats everything
    assert i18n.resolve_locale(override="zh", customer_locale="ms", tenant_default="th") == "zh"
    # then the diner's saved locale
    assert i18n.resolve_locale(customer_locale="ms", tenant_default="th") == "ms"
    # then tenant default
    assert i18n.resolve_locale(tenant_default="th", accept_language="vi") == "th"
    # then Accept-Language
    assert i18n.resolve_locale(accept_language="vi,en;q=0.8") == "vi"
    # nothing → default
    assert i18n.resolve_locale() == "en"


def test_pick_falls_back_to_canonical():
    tr = {"zh": {"name": "汉堡"}, "ms": {"name": ""}}   # ms blank → must NOT win
    assert i18n.pick(tr, "zh", "name", "Burger") == "汉堡"
    assert i18n.pick(tr, "ms", "name", "Burger") == "Burger"     # blank → canonical
    assert i18n.pick(tr, "th", "name", "Burger") == "Burger"     # missing locale → canonical
    assert i18n.pick(tr, "zh", "description", "Tasty") == "Tasty"  # missing field → canonical
    assert i18n.pick(None, "zh", "name", "Burger") == "Burger"   # no translations at all


def test_en_sg_overlay_falls_back_to_en():
    tr = {"en": {"name": "Add to cart"}}
    # en-SG with no entry should fall through its chain to en
    assert i18n.pick(tr, "en-SG", "name", "CANON") == "Add to cart"


# --- Integration: localised QR menu read + currency carry --------------------------------------
def test_qr_localises_menu_with_fallback(client, db):
    w = make_world(db)
    w.burger.translations = {"zh": {"name": "汉堡", "description": "美味"}}
    db.commit()

    body = client.get(f"/api/v1/qr/{w.qr_token}?lang=zh").json()
    items = {i["name"]: i for cat in body["menu"]["categories"] for i in cat["items"]}
    assert "汉堡" in items                 # translated item localised
    assert "Drink" in items               # untranslated item → canonical, never blank
    assert body["locale"] == "zh"


def test_qr_default_locale_uses_canonical(client, db):
    w = make_world(db)
    w.burger.translations = {"zh": {"name": "汉堡"}}
    db.commit()
    body = client.get(f"/api/v1/qr/{w.qr_token}").json()   # no lang → en
    names = [i["name"] for cat in body["menu"]["categories"] for i in cat["items"]]
    assert "Burger" in names and "汉堡" not in names
    assert body["locale"] == "en"


def test_qr_carries_currency_default_sgd(client, db):
    w = make_world(db)
    body = client.get(f"/api/v1/qr/{w.qr_token}").json()
    assert body["currency"] == "SGD"      # money is a settlement fact, defaulted SG-first


def test_qr_tenant_default_locale_applies(client, db):
    w = make_world(db)
    w.merchant.settings = {"locale": "ms"}
    w.burger.translations = {"ms": {"name": "Burger Sedap"}}
    db.commit()
    body = client.get(f"/api/v1/qr/{w.qr_token}").json()   # no override, no header → tenant default ms
    names = [i["name"] for cat in body["menu"]["categories"] for i in cat["items"]]
    assert "Burger Sedap" in names
    assert body["locale"] == "ms"
