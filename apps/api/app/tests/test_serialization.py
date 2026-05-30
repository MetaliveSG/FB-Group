"""All datetime fields serialize as unambiguous UTC ISO-8601 with a 'Z' suffix
(multi-region correctness — a bare timestamp is read as local time by clients)."""
from datetime import datetime, timezone

from pydantic import BaseModel

from app.schemas.common import UtcDatetime, _to_utc_z


class _M(BaseModel):
    ts: UtcDatetime
    opt: UtcDatetime | None = None


def test_naive_utc_serializes_with_z():
    assert _M(ts=datetime(2026, 5, 30, 5, 11, 30)).model_dump_json() == \
        '{"ts":"2026-05-30T05:11:30Z","opt":null}'


def test_tzaware_is_converted_to_utc_z():
    # +08:00 05:00 == 21:00 UTC the day before
    dt = datetime(2026, 5, 30, 5, 0, 0, tzinfo=timezone(__import__("datetime").timedelta(hours=8)))
    assert _to_utc_z(dt) == "2026-05-29T21:00:00Z"


def test_api_response_datetimes_carry_z(client, db):
    """A real endpoint's datetime field must end in Z over the wire."""
    from app.tests.factories import make_world
    from app.tests.helpers import H, register_customer, place_order, checkout
    w = make_world(db)
    cust = register_customer(client, email="z@b.sg", phone="+6590000900")
    item_id = client.get(f"/api/v1/qr/{w.qr_token}").json()["menu"]["categories"][0]["items"][0]["id"]
    order = place_order(client, cust["access_token"], w.qr_token, [{"menu_item_id": item_id, "quantity": 1}])
    checkout(client, cust["access_token"], order["id"])
    r = client.get(f"/api/v1/me/orders?merchant_id={w.merchant_id}", headers=H(cust["access_token"]))
    assert r.status_code == 200, r.text
    assert r.json()[0]["created_at"].endswith("Z")
