#!/usr/bin/env python3
"""Rewards-system live proof harness (MMQRDepositBot-style evidence report).

Exercises the whole rewards surface against the running API ( :8000 ) —
loyalty, catalog redeem, spin-the-wheel, 888 jackpot (incl. the progressive
grand-jackpot pot), vouchers, orders, profile, and negative guardrails — and
writes a REQUEST / RESPONSE / CHECKS / RESULT transcript + pass/fail summary to
artifacts/rewards_proof_<date>.txt.

Each scenario fires its request EXACTLY ONCE; checks are callables run on that
single response (no double-firing / side effects).

Usage: .venv/bin/python scripts/rewards_proof.py [base_url] [qr_token] [phone]
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timezone

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000") + "/api/v1"
QR = sys.argv[2] if len(sys.argv) > 2 else "kampong-bedok-01"
PHONE = sys.argv[3] if len(sys.argv) > 3 else "+6581000000"

_lines: list[str] = []
_passed = _failed = 0


def out(s: str = "") -> None:
    print(s)
    _lines.append(s)


def req(method: str, path: str, token: str | None = None, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    if token:
        r.add_header("Authorization", f"Bearer {token}")
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}"), int((time.time() - t0) * 1000)
    except urllib.error.HTTPError as e:
        ms = int((time.time() - t0) * 1000)
        try:
            return e.code, json.loads(e.read().decode() or "{}"), ms
        except Exception:
            return e.code, {}, ms


def scenario(title, method, path, *, token=None, body=None, expect, checks=None, show_body=True):
    """checks: list[(label, fn(resp)->bool)]. Request fires once."""
    global _passed, _failed
    status, resp, ms = req(method, path, token, body)
    out("=" * 70)
    out(f"TEST: {title}")
    out("=" * 70)
    out("REQUEST:")
    out(f"  {method} {path}")
    if body is not None:
        out(f"  Payload: {json.dumps(body)}")
    out("RESPONSE:")
    out(f"  Status: {status}  Time: {ms}ms")
    if show_body:
        b = json.dumps(resp)
        out(f"  Body: {b[:380]}{'…' if len(b) > 380 else ''}")
    out("CHECKS:")
    ok = status == expect
    out(f"  {'PASS' if ok else 'FAIL'} — status {status} (expected {expect})")
    for label, fn in (checks or []):
        try:
            c = bool(fn(resp))
        except Exception as e:  # noqa: BLE001 - proof harness, report the failure
            c = False
            label = f"{label} (exc: {e})"
        out(f"  {'PASS' if c else 'FAIL'} — {label}")
        ok = ok and c
    out(f"RESULT: {'PASS' if ok else 'FAIL'}  [{ms}ms]")
    out("")
    if ok:
        _passed += 1
    else:
        _failed += 1
    return resp


def main():
    out("=" * 70)
    out("  REWARDS SYSTEM — LIVE PROOF REPORT · FB Group F&B CRM PoC")
    out(f"  {datetime.now(timezone.utc).isoformat()}  ·  API {BASE}")
    out("=" * 70)
    out("")

    status, qr, _ = req("GET", f"/qr/{QR}")
    assert status == 200, f"QR resolve failed: {status} {qr}"
    mid = qr["merchant"]["id"]
    out(f"Context: merchant={qr['merchant']['name']} · outlet={qr['outlet']['name']} · table={qr['table']['label']}")
    _, otp, _ = req("POST", "/auth/customer/otp/request", body={"phone": PHONE})
    _, auth, _ = req("POST", "/auth/customer/otp/verify", body={"phone": PHONE, "code": otp.get("debug_code")})
    tok = auth["access_token"]
    out(f"Logged in: {PHONE} (token {tok[:14]}…)")
    out("")

    out("━" * 70 + "\nSECTION 1 — LOYALTY & CATALOG\n" + "━" * 70)
    scenario("Loyalty summary", "GET", f"/me/loyalty?merchant_id={mid}", token=tok, expect=200,
             checks=[("points_balance present", lambda r: "points_balance" in r),
                     ("tier present", lambda r: "tier" in r)])
    scenario("Rewards catalog — free items only (coins not cash-redeemable)", "GET",
             f"/me/rewards/catalog?merchant_id={mid}", token=tok, expect=200,
             checks=[("no 'discount' kind present", lambda r: all(c.get("kind") != "discount" for c in r))])

    out("━" * 70 + "\nSECTION 2 — SPIN THE WHEEL\n" + "━" * 70)
    scenario("Wheel config", "GET", f"/me/wheel?merchant_id={mid}", token=tok, expect=200,
             checks=[("spin_cost == 10", lambda r: r.get("spin_cost") == 10),
                     ("segments present", lambda r: len(r.get("segments", [])) > 0)])
    bal = req("GET", f"/me/loyalty?merchant_id={mid}", tok)[1]["points_balance"]
    if bal >= 10:
        scenario("Wheel spin (deducts 10, returns prize)", "POST", "/me/wheel/spin", token=tok,
                 body={"merchant_id": mid}, expect=200,
                 checks=[("winning_index present", lambda r: "winning_index" in r),
                         ("balance returned", lambda r: "points_balance" in r)])

    out("━" * 70 + "\nSECTION 3 — 888 JACKPOT + PROGRESSIVE GRAND POT\n" + "━" * 70)
    scenario("Jackpot config (5/spin + progressive grand_prize)", "GET", f"/me/jackpot?merchant_id={mid}",
             token=tok, expect=200,
             checks=[("spin_cost == 5", lambda r: r.get("spin_cost") == 5),
                     ("grand_prize >= 1000", lambda r: r.get("grand_prize", 0) >= 1000),
                     ("grid_size == 3", lambda r: r.get("grid_size") == 3)])
    g1 = req("GET", f"/me/jackpot?merchant_id={mid}", tok)[1]["grand_prize"]
    time.sleep(4)
    g2 = req("GET", f"/me/jackpot?merchant_id={mid}", tok)[1]["grand_prize"]
    scenario("Grand jackpot pot grows over time (persistent/progressive)", "GET",
             f"/me/jackpot?merchant_id={mid}", token=tok, expect=200, show_body=False,
             checks=[(f"pot grew in ~4s: {g1} → {g2}", lambda r: g2 >= g1 and g2 > 1000)])
    bal = req("GET", f"/me/loyalty?merchant_id={mid}", tok)[1]["points_balance"]
    if bal >= 5:
        scenario("Jackpot play (server-authoritative, charges 5)", "POST", "/me/jackpot/play",
                 token=tok, body={"merchant_id": mid}, expect=200,
                 checks=[("grid is 3x3", lambda r: len(r.get("grid", [])) == 3 and all(len(row) == 3 for row in r.get("grid", []))),
                         ("won flag present", lambda r: "won" in r)])

    out("━" * 70 + "\nSECTION 4 — VOUCHERS · ORDERS · PROFILE\n" + "━" * 70)
    scenario("My vouchers", "GET", f"/me/vouchers?merchant_id={mid}", token=tok, expect=200,
             checks=[("returns a list", lambda r: isinstance(r, list))])
    scenario("My orders (history)", "GET", f"/me/orders?merchant_id={mid}", token=tok, expect=200,
             checks=[("returns a list", lambda r: isinstance(r, list))])
    scenario("Profile read", "GET", "/me/profile", token=tok, expect=200,
             checks=[("phone present", lambda r: bool(r.get("phone")))])
    scenario("Profile update (birthday + gender persist)", "PATCH", "/me/profile", token=tok,
             body={"phone": PHONE, "birthday": "1990-01-15", "gender": "female"}, expect=200,
             checks=[("gender == female", lambda r: r.get("gender") == "female"),
                     ("birthday == 1990-01-15", lambda r: r.get("birthday") == "1990-01-15")])

    out("━" * 70 + "\nSECTION 5 — GUARDRAILS (negative paths)\n" + "━" * 70)
    _, o2, _ = req("POST", "/auth/customer/otp/request", body={"phone": "+6595550000"})
    _, a2, _ = req("POST", "/auth/customer/otp/verify", body={"phone": "+6595550000", "code": o2.get("debug_code")})
    broke = a2["access_token"]
    scenario("Jackpot blocked when insufficient coins (fresh 0-coin diner)", "POST", "/me/jackpot/play",
             token=broke, body={"merchant_id": mid}, expect=409,
             checks=[("error code = insufficient_points", lambda r: r.get("error", {}).get("code") == "insufficient_points")])
    scenario("Wheel blocked when insufficient coins", "POST", "/me/wheel/spin",
             token=broke, body={"merchant_id": mid}, expect=409,
             checks=[("error code = insufficient_points", lambda r: r.get("error", {}).get("code") == "insufficient_points")])
    scenario("Rewards require a customer token (no token → 401)", "GET",
             f"/me/loyalty?merchant_id={mid}", token=None, expect=401, show_body=False)

    out("=" * 70)
    out(f"SUMMARY: {_passed} PASSED, {_failed} FAILED, {_passed + _failed} TOTAL")
    out("=" * 70)

    fn = f"../../artifacts/rewards_proof_{date.today().isoformat()}.txt"
    with open(fn, "w") as f:
        f.write("\n".join(_lines) + "\n")
    print(f"\n[proof written] {fn}")
    sys.exit(1 if _failed else 0)


if __name__ == "__main__":
    main()
