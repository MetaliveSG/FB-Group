"use client";

import { useEffect, useMemo, useState } from "react";
import {
  orgTree,
  listNodeAccounts,
  createNodeAccount,
  revokeNodeAccount,
  setStaffPin,
} from "@/lib/api";
import { getStaffToken } from "@/lib/auth";
import type { OrgTreeNode, OrgNodeAccount } from "@fbgroup/api-client";

const ROLES = ["cashier", "manager", "staff", "finance"];

/**
 * "Staff & PINs (POS)" — merchant-owner self-serve for POS logins.
 * POS staff sign in at /pos with a 4–6 digit PIN (unique per merchant). Here the owner picks the
 * storefront a cashier works at, adds their login, and sets/resets the PIN. Mirrors the operator's
 * Platform-Console node drawer, but lives in the merchant's own Settings. Uses the scope-aware
 * /org endpoints (the token's merchant context scopes the visible tree — no merchant_id needed).
 */
export default function PosStaffCard({ base, merchantId }: { base: string; merchantId?: string }) {
  const [nodes, setNodes] = useState<OrgTreeNode[] | null>(null);
  const [nodeId, setNodeId] = useState<string>("");
  const [accounts, setAccounts] = useState<OrgNodeAccount[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  // Add-staff form
  const [open, setOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [pass, setPass] = useState("");
  const [role, setRole] = useState("cashier");
  const [pin, setPin] = useState("");

  const tok = () => getStaffToken() || "";

  // Restrict to the in-scope merchant's subtree. A normal merchant login already gets only its own
  // tenant from /org/tree (visible_nodes is downline-only). But a super-admin operator gets the WHOLE
  // forest — so when the page is scoped to one merchant (operator drilled in via getOperatorMerchant),
  // walk parent_id from that tenant root and keep only its subtree. No merchantId → trust the server scope.
  const scoped = useMemo(() => {
    const all = nodes || [];
    if (!merchantId) return all;
    const keep = new Set<string>([merchantId]);
    let grew = true;
    while (grew) {
      grew = false;
      for (const n of all) {
        if (n.parent_id && keep.has(n.parent_id) && !keep.has(n.id)) { keep.add(n.id); grew = true; }
      }
    }
    return all.filter((n) => keep.has(n.id));
  }, [nodes, merchantId]);

  // Manageable nodes only (owner → their tenant tree). Sort sells-first so a storefront is the default.
  const manageable = useMemo(
    () => scoped.filter((n) => n.can_manage && n.is_active),
    [scoped],
  );

  useEffect(() => {
    let live = true;
    orgTree(base, tok())
      .then((t) => { if (live) setNodes(t.nodes); })
      .catch(() => { if (live) setNodes([]); });
    return () => { live = false; };
  }, [base]);

  // Default the picker to a storefront in scope (sells-first), once the scoped/manageable set is known.
  useEffect(() => {
    if (nodeId || manageable.length === 0) return;
    const pick = manageable.find((n) => n.sells) || manageable[0];
    setNodeId(pick.id);
  }, [manageable, nodeId]);

  function reloadAccounts(id = nodeId) {
    if (!id) return;
    setAccounts(null);
    listNodeAccounts(base, tok(), id).then(setAccounts).catch(() => setAccounts([]));
  }

  useEffect(() => { if (nodeId) reloadAccounts(nodeId); /* eslint-disable-next-line */ }, [nodeId]);

  function flash(m: string) { setOk(m); setErr(null); setTimeout(() => setOk(null), 2500); }
  function fail(e: unknown) {
    const m = e instanceof Error ? e.message : "Something went wrong";
    setErr(m.includes("403") ? "You don't have permission to manage staff here." : m);
  }

  async function run(fn: () => Promise<unknown>, after: () => void, okMsg: string) {
    setBusy(true); setErr(null); setOk(null);
    try { await fn(); after(); flash(okMsg); }
    catch (e) { fail(e); }
    finally { setBusy(false); }
  }

  function addStaff() {
    if (pin && !/^\d{4,6}$/.test(pin)) { setErr("PIN must be 4–6 digits."); return; }
    run(
      async () => {
        const acc = await createNodeAccount(base, tok(), nodeId, {
          email: email.trim(), full_name: name.trim(), password: pass, role,
        });
        if (pin) await setStaffPin(base, tok(), nodeId, acc.user_id, pin);
      },
      () => { setEmail(""); setName(""); setPass(""); setPin(""); setRole("cashier"); setOpen(false); reloadAccounts(); },
      "Staff added.",
    );
  }

  function resetPin(a: OrgNodeAccount) {
    const v = window.prompt(`Set POS PIN for ${a.email} (4–6 digits):`);
    if (v === null) return;
    if (!/^\d{4,6}$/.test(v)) { window.alert("PIN must be 4–6 digits"); return; }
    run(() => setStaffPin(base, tok(), nodeId, a.user_id, v), () => reloadAccounts(), "PIN updated.");
  }

  if (nodes === null) {
    return (
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontWeight: 600 }}>Staff &amp; PINs (POS)</div>
        <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginTop: 6 }}>Loading…</div>
      </div>
    );
  }
  if (manageable.length === 0) return null; // nothing this caller can manage → hide the card

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div style={{ fontWeight: 600 }}>Staff &amp; PINs (POS)</div>
      <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 12 }}>
        Add the people who run the till. They sign in at <code>/pos</code> with a 4–6 digit PIN
        (no email/password at the counter). PINs are unique within your business.
      </div>

      {/* Which storefront these staff belong to */}
      <label style={{ fontSize: 13, display: "block", marginBottom: 12 }}>
        Storefront / location
        <select value={nodeId} disabled={busy}
                onChange={(e) => setNodeId(e.target.value)}
                style={{ display: "block", marginTop: 2, minWidth: 280 }}>
          {manageable.map((n) => (
            <option key={n.id} value={n.id}>
              {"  ".repeat(Math.max(0, n.depth))}{n.name || "(unnamed)"}{n.sells ? "" : "  ·  group"}
            </option>
          ))}
        </select>
      </label>

      {/* Existing staff at the picked node */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {accounts === null ? (
          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Loading staff…</span>
        ) : accounts.length === 0 ? (
          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>No staff here yet — add one below.</span>
        ) : (
          accounts.map((a) => (
            <div key={a.assignment_id} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, borderBottom: "1px solid var(--color-border,#eef0f3)", paddingBottom: 8 }}>
              <div style={{ flex: 1, overflow: "hidden" }}>
                <div style={{ fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{a.full_name || a.email}</div>
                {a.full_name && <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>{a.email}</div>}
              </div>
              <span className="badge" style={{ background: "#eef2ff", color: "#3730a3", fontSize: 10, textTransform: "capitalize" }}>{a.role}</span>
              <button title={a.pin_set ? "PIN set — tap to reset" : "Set POS PIN"} disabled={busy}
                onClick={() => resetPin(a)}
                style={{ background: "none", border: "none", cursor: "pointer", color: a.pin_set ? "#166534" : "#6b7280", fontSize: 12, fontWeight: 600 }}>
                {a.pin_set ? "PIN ✓ reset" : "Set PIN"}
              </button>
              <button aria-label="Remove staff" title="Remove staff" disabled={busy}
                onClick={() => run(() => revokeNodeAccount(base, tok(), nodeId, a.assignment_id), () => reloadAccounts(), "Staff removed.")}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#b91c1c", fontSize: 16 }}>×</button>
            </div>
          ))
        )}
      </div>

      {/* Add staff */}
      {!open ? (
        <button className="btn btn-secondary btn-sm" style={{ marginTop: 12 }} disabled={busy} onClick={() => setOpen(true)}>
          + Add staff
        </button>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: 12, marginTop: 12, border: "1px dashed var(--color-border,#e5e7eb)", borderRadius: 8, maxWidth: 460 }}>
          <input placeholder="Email (their login)" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input placeholder="Full name" value={name} onChange={(e) => setName(e.target.value)} />
          <input placeholder="Temp password (min 8 chars)" type="text" value={pass} onChange={(e) => setPass(e.target.value)} />
          <div style={{ display: "flex", gap: 8 }}>
            <label style={{ fontSize: 12, flex: 1 }}>Role
              <select value={role} onChange={(e) => setRole(e.target.value)} style={{ display: "block", width: "100%", textTransform: "capitalize" }}>
                {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </label>
            <label style={{ fontSize: 12, flex: 1 }}>POS PIN (optional)
              <input placeholder="4–6 digits" inputMode="numeric" value={pin}
                     onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                     style={{ display: "block", width: "100%" }} />
            </label>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 2 }}>
            <button className="btn btn-primary btn-sm" disabled={busy || !email.trim() || pass.length < 8} onClick={addStaff}>
              Add staff
            </button>
            <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => { setOpen(false); setErr(null); }}>
              Cancel
            </button>
          </div>
        </div>
      )}

      {err && <div style={{ color: "#b91c1c", fontSize: 12, marginTop: 10 }}>{err}</div>}
      {ok && <div style={{ color: "#166534", fontSize: 12, marginTop: 10 }}>{ok}</div>}
    </div>
  );
}
