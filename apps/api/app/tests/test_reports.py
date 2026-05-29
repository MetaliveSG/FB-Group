"""Module 9 — Sales Reports, Forecasts & Graph APIs."""
from app.tests.factories import add_outlet, make_world
from app.tests.helpers import H, checkout, place_order, register_customer, staff_token


def _paid_order(client, qr_token, item_id, email, qty=1):
    tok = register_customer(client, email=email)["access_token"]
    order = place_order(client, tok, qr_token, [{"menu_item_id": item_id, "quantity": qty}])
    res = checkout(client, tok, order["id"])
    return res["payment"]["amount"]


def test_sales_summary_values_correct(client, db):
    w = make_world(db)
    a1 = _paid_order(client, w.qr_token, w.burger_id, "r1@b.sg")
    a2 = _paid_order(client, w.qr_token, w.burger_id, "r2@b.sg", qty=2)
    otok = staff_token(client, w.owner_email)

    summary = client.get("/api/v1/reports/summary", headers=H(otok)).json()
    assert summary["orders"] == 2
    assert summary["unique_customers"] == 2
    assert round(summary["revenue"], 2) == round(a1 + a2, 2)


def test_sales_timeseries_is_graph_ready(client, db):
    w = make_world(db)
    _paid_order(client, w.qr_token, w.burger_id, "g1@b.sg")
    otok = staff_token(client, w.owner_email)
    series = client.get("/api/v1/reports/sales?granularity=day", headers=H(otok)).json()
    assert isinstance(series, list) and series
    assert set(series[0].keys()) == {"period", "revenue", "orders"}


def test_top_items_and_peak_hours(client, db):
    w = make_world(db)
    _paid_order(client, w.qr_token, w.burger_id, "t1@b.sg")
    otok = staff_token(client, w.owner_email)
    top = client.get("/api/v1/reports/top-items", headers=H(otok)).json()
    assert any(i["name"] == "Burger" for i in top)
    peak = client.get("/api/v1/reports/peak-hours", headers=H(otok)).json()
    assert len(peak) == 24


def test_forecast_endpoint_works(client, db):
    w = make_world(db)
    _paid_order(client, w.qr_token, w.burger_id, "f1@b.sg")
    otok = staff_token(client, w.owner_email)
    fc = client.get("/api/v1/reports/forecast?horizon=7", headers=H(otok)).json()
    assert fc["method"] == "moving_average"
    assert len(fc["forecast"]) == 7
    assert "limitations" in fc


def test_report_outlet_permission_respected(client, db):
    w = make_world(db)
    o2 = add_outlet(db, w, "2")
    # Revenue happens only at outlet B.
    _paid_order(client, o2.qr_token, o2.item_id, "ob@b.sg")

    mgr = staff_token(client, w.outlet_mgr_email)   # outlet A only
    owner = staff_token(client, w.owner_email)
    assert client.get("/api/v1/reports/summary", headers=H(mgr)).json()["revenue"] == 0.0
    assert client.get("/api/v1/reports/summary", headers=H(owner)).json()["revenue"] > 0
