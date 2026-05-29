"""Drive the golden capture loop against a RUNNING server over HTTP (stdlib only).

Usage: python -m scripts.live_demo <base_url> <qr_token>
Proves the real uvicorn process serves the full flow end to end.
"""
from __future__ import annotations

import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8011"
QR = sys.argv[2] if len(sys.argv) > 2 else "ae0d3152-01"


def call(method, path, body=None, token=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode())


def main():
    print(f"BASE={BASE}  QR={QR}\n")
    print("0) GET /health ->", call("GET", "/health"))

    ctx = call("GET", f"/api/v1/qr/{QR}")
    item = ctx["menu"]["categories"][0]["items"][0]
    print(f"1) SCAN QR -> {ctx['merchant']['name']} / {ctx['outlet']['name']} / table {ctx['table']['label']}")
    print(f"   menu item: {item['name']} ${item['price']}")

    phone = "+6588887777"
    code = call("POST", "/api/v1/auth/customer/otp/request", {"phone": phone})["debug_code"]
    auth = call("POST", "/api/v1/auth/customer/otp/verify",
                {"phone": phone, "code": code, "full_name": "Live Demo Guest"})
    tok = auth["access_token"]
    cid = auth["customer"]["id"]
    print(f"2) OTP register/login -> customer {cid}")

    order = call("POST", "/api/v1/orders",
                 {"qr_token": QR, "items": [{"menu_item_id": item["id"], "quantity": 2}]}, token=tok)
    print(f"3) ORDER -> {order['id']} subtotal=${order['subtotal']} service=${order['service_charge']} "
          f"gst=${order['tax']} total=${order['total']} status={order['status']}")

    co = call("POST", f"/api/v1/orders/{order['id']}/checkout", {"method": "paynow"}, token=tok)
    print(f"4) CHECKOUT -> payment={co['payment']['status']} ref={co['payment']['reference']} txn={co['transaction_id']}")
    print(f"5) POINTS EARNED -> {co['points_earned']}")

    staff = call("POST", "/api/v1/auth/staff/login", {"email": "owner@makan.sg", "password": "Password123!"})
    stok = staff["access_token"]
    print("6) MERCHANT LOGIN -> owner@makan.sg")

    prof = call("GET", f"/api/v1/crm/customers/{cid}", token=stok)
    m = prof["metrics"]
    print(f"7) CRM PROFILE -> visits={m['visit_count']} spend=${m['total_spend']} points={m['points_balance']} "
          f"tier={m['tier']} stage={m['lifecycle_stage']} segments={m['segments']}")
    print(f"   transactions={len(prof['transactions'])} rewards={len(prof['rewards'])}")

    summary = call("GET", "/api/v1/reports/summary", token=stok)
    print(f"9) SALES DASHBOARD -> revenue=${summary['revenue']} orders={summary['orders']} customers={summary['unique_customers']}")
    fc = call("GET", "/api/v1/reports/forecast?horizon=7", token=stok)
    print(f"10) FORECAST -> method={fc['method']} next7d_avg=${fc['moving_average']} points={len(fc['forecast'])}")

    assert co["points_earned"] > 0 and co["transaction_id"] and m["visit_count"] >= 1
    print("\n✅ LIVE END-TO-END CAPTURE LOOP OK")


if __name__ == "__main__":
    main()
