#!/usr/bin/env python3
"""LIVE per-level login proof for the BreadTalk enterprise member-tree.

Logs in as every account from Enterprise (CEO) down to a single Stall operator against a RUNNING
API, then for each: pulls GET /org/tree (the caller's visible slice of the member-tree) and
GET /org/permissions, and asserts that a parent sees ALL of its children (brands/outlets/stalls)
with the right management capability — downline only, never a sibling or the upline.

Run against the Docker stack:  python3 login_proof.py http://localhost:8000
Writes proof.txt + login_proof.json next to this file.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000").rstrip("/")
API = f"{BASE}/api/v1"
PW = "Password123!"
HERE = Path(__file__).resolve().parent

# (email, tier label, expected role) — authority = position on the Chain/Storefront tree.
ACCOUNTS = [
    ("ceo@breadtalk.sg", "Group Chain · Manager (CEO)", "manager"),
    ("cfo@breadtalk.sg", "Group Chain · Finance (CFO, read-only)", "finance"),
    ("owner.m1@breadtalk.sg", "Tenant Chain · BreadTalk (F&B) GM", "manager"),
    ("mgr.toastbox@breadtalk.sg", "Chain · Toast Box Manager", "manager"),
    ("mgr.foodrepublic@breadtalk.sg", "Chain · Food Republic Manager (foodcourt)", "manager"),
    ("mgr.ion@breadtalk.sg", "Storefront · BreadTalk @ ION Manager", "manager"),
    ("cashier.ion@breadtalk.sg", "Storefront · BreadTalk @ ION Cashier", "cashier"),
    ("staff.chicken@breadtalk.sg", "Storefront · Chicken Rice Staff", "staff"),
    ("cashier.tampines@breadtalk.sg", "Storefront · Toast Box Tampines Cashier", "cashier"),
    ("mgr.dtf@breadtalk.sg", "Chain · Din Tai Fung Manager (Tenant 2)", "manager"),
]


def _post(path: str, body: dict, token: str | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{API}{path}", data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    return _send(req)


def _get(path: str, token: str) -> tuple[int, dict]:
    req = urllib.request.Request(f"{API}{path}", method="GET",
                                 headers={"Authorization": f"Bearer {token}"})
    return _send(req)


def _send(req) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}


def login(email: str) -> str | None:
    code, body = _post("/auth/staff/login", {"email": email, "password": PW})
    return body.get("access_token") if code == 200 else None


def summarize(nodes: list[dict]) -> dict:
    chains = [n.get("name") or n["id"] for n in nodes if n["role"] == "CHAIN"]
    storefronts = [n.get("name") or n["id"] for n in nodes if n["role"] == "STOREFRONT"]
    tenants = [n.get("name") or n["id"] for n in nodes if n.get("is_settlement_boundary")]
    return {
        "total": len(nodes),
        "chains": sorted(chains),
        "storefronts": sorted(storefronts),
        "tenants": sorted(tenants),
        "manageable": sum(1 for n in nodes if n["can_manage"]),
    }


def main() -> int:
    results = []
    for email, tier, role in ACCOUNTS:
        tok = login(email)
        rec: dict = {"email": email, "tier": tier, "role": role, "login": bool(tok)}
        if tok:
            tcode, tree = _get("/org/tree", tok)
            pcode, perms = _get("/org/permissions", tok)
            nodes = tree.get("nodes", []) if tcode == 200 else []
            rec["tree_http"] = tcode
            rec["can_manage_tree"] = tree.get("can_manage", False)
            rec["visible"] = summarize(nodes)
            rec["permissions"] = sorted(perms.get("permissions", [])) if pcode == 200 else []
            rec["perm_count"] = len(rec["permissions"])
        results.append(rec)

    # Cross-checks: a Manager at the top Chain sees EVERY storefront + both tenants.
    def acct(email: str) -> dict:
        return next(r for r in results if r["email"] == email)

    ceo = acct("ceo@breadtalk.sg")
    fr = acct("mgr.foodrepublic@breadtalk.sg")
    dtf = acct("mgr.dtf@breadtalk.sg")
    # DTF (a Chain manager under Tenant 2) sees only its own branch — never BreadTalk (Tenant 1).
    dtf_names = dtf["visible"]["storefronts"] + dtf["visible"]["chains"]
    dtf_clean = all(("Din Tai Fung" in n) for n in dtf_names)
    checks = {
        "ceo_sees_all_7_storefronts": len(ceo["visible"]["storefronts"]) == 7,
        "ceo_sees_both_tenants": len(ceo["visible"]["tenants"]) == 2,
        "ceo_sees_whole_tree_15_nodes": ceo["visible"]["total"] == 15,
        "ceo_can_manage_whole_tree": ceo["can_manage_tree"] is True,
        "cfo_read_only": acct("cfo@breadtalk.sg")["can_manage_tree"] is False,
        "foodcourt_mgr_sees_3_storefronts": len(fr["visible"]["storefronts"]) == 3,
        "toastbox_isolated_2_nodes": acct("mgr.toastbox@breadtalk.sg")["visible"]["total"] == 2,
        "storefront_staff_sees_only_its_storefront": acct("staff.chicken@breadtalk.sg")["visible"]["total"] == 1,
        "dtf_isolated_no_breadtalk": dtf["visible"]["total"] == 2 and dtf_clean,
        "every_account_logged_in": all(r["login"] for r in results),
    }

    (HERE / "login_proof.json").write_text(json.dumps({"base": BASE, "results": results, "checks": checks}, indent=2))
    render(results, checks)
    ok = all(checks.values())
    print("\nALL CHECKS PASSED" if ok else "\nSOME CHECKS FAILED")
    return 0 if ok else 1


def render(results: list[dict], checks: dict) -> None:
    lines = []
    lines.append("BreadTalk Group — LIVE per-level login proof (member-tree visibility + RBAC)")
    lines.append(f"API: {BASE}   ·   every login password: {PW}")
    lines.append("=" * 92)
    lines.append("Each row: a real staff login → GET /org/tree (their visible slice) + /org/permissions.")
    lines.append("A parent sees ALL of its children; a child never sees a sibling or its upline.")
    lines.append("")
    hdr = f"{'TIER / ROLE':<46}{'login':<7}{'nodes':<7}{'chain':<6}{'storefront':<11}{'tenant':<7}{'manage':<7}{'perms'}"
    lines.append(hdr)
    lines.append("-" * 92)
    for r in results:
        if not r["login"]:
            lines.append(f"{r['tier']:<46}{'FAIL':<7}")
            continue
        v = r["visible"]
        mng = "all" if r["can_manage_tree"] and v["manageable"] == v["total"] else (str(v["manageable"]) if r["can_manage_tree"] else "—")
        lines.append(
            f"{r['tier']:<46}{'OK':<7}{v['total']:<7}{len(v['chains']):<6}"
            f"{len(v['storefronts']):<11}{len(v['tenants']):<7}{mng:<7}{r['perm_count']}"
        )
    lines.append("-" * 92)
    lines.append("")
    lines.append("Parent → children visibility (the storefronts each tier can see):")
    for r in results:
        if not r["login"]:
            continue
        v = r["visible"]
        lines.append(f"  • {r['tier']}")
        if v["storefronts"]:
            lines.append(f"        storefronts: {', '.join(v['storefronts'])}")
        lines.append(f"        manage     : {'YES (' + str(v['manageable']) + ' nodes)' if r['can_manage_tree'] else 'view-only'}")
    lines.append("")
    lines.append("Cross-checks:")
    for k, val in checks.items():
        lines.append(f"  [{'PASS' if val else 'FAIL'}] {k}")
    (HERE / "proof.txt").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
