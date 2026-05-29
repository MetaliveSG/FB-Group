"""AI Insights advisor — exercises the deterministic heuristic path (no API key),
permission gating, and tenant isolation. The Claude path is config-gated and not
hit in tests, so results stay reproducible and free of network/cost."""
from app.tests.factories import make_world
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token

VALID_PRIORITIES = {"high", "medium", "low"}


def _paid_order(client, qr_token, item_id, email, qty=1):
    tok = register_customer(client, email=email)["access_token"]
    order = place_order(client, tok, qr_token, [{"menu_item_id": item_id, "quantity": qty}])
    checkout(client, tok, order["id"])


def test_ai_insights_heuristic_shape(client, db):
    w = make_world(db)
    _paid_order(client, w.qr_token, w.burger_id, "ai1@b.sg")
    _paid_order(client, w.qr_token, w.burger_id, "ai2@b.sg", qty=3)
    otok = staff_token(client, w.owner_email)

    r = client.get("/api/v1/reports/ai-insights", headers=H(otok))
    assert r.status_code == 200, r.text
    data = r.json()

    # Deterministic provider in the PoC.
    assert data["generated_by"] == "heuristic"
    assert data["model"] is None

    # Summary + highlights + ranked recommendations.
    assert isinstance(data["summary"], str) and data["summary"]
    assert data["highlights"]
    assert data["recommendations"]
    for rec in data["recommendations"]:
        assert rec["title"] and rec["action"] and rec["rationale"]
        assert rec["priority"] in VALID_PRIORITIES
    priorities = [{"high": 0, "medium": 1, "low": 2}[r["priority"]] for r in data["recommendations"]]
    assert priorities == sorted(priorities)  # highest-impact first

    # Context the advice was derived from is exposed for transparency.
    assert {"sales", "customers", "rfm", "pipeline", "campaigns"} <= set(data["context"])
    assert data["context"]["sales"]["orders"] == 2


def test_ai_insights_requires_staff(client, db):
    w = make_world(db)
    diner = register_customer(client, email="diner-ai@b.sg")["access_token"]
    # A diner (customer actor) token must not reach the merchant advisor.
    assert client.get("/api/v1/reports/ai-insights", headers=H(diner)).status_code == 403


def test_ai_insights_tenant_isolation(client, db):
    make_world(db, name="M1", token_suffix="1")
    w2 = make_world(db, name="M2", token_suffix="2")
    o1 = staff_token(client, "owner@m1.sg")
    # M1 owner cannot pull M2's insights.
    r = client.get(f"/api/v1/reports/ai-insights?merchant_id={w2.merchant.id}", headers=H(o1))
    assert r.status_code == 403
