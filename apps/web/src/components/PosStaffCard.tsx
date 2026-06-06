"use client";

import { useEffect, useMemo, useState } from "react";
import {
  orgTree,
  listPosStaff,
  createPosStaff,
  resetPosStaffPin,
  deletePosStaff,
} from "@/lib/api";
import { getStaffToken } from "@/lib/auth";
import type { OrgTreeNode, PosStaffMember, PosStaffSecret } from "@fbgroup/api-client";

const ROLES = ["cashier", "manager", "staff", "finance"];

/**
 * "Staff & PINs (POS)" — merchant-owner self-serve for POS till operators.
 * POS users are PIN-only (kind="pos"): they sign in at /pos with a 4–6 digit PIN and CANNOT log into
 * the web dashboard. PINs are bcrypt-hashed (one-way), unique **per storefront**, and revealed exactly
 * ONCE — at generation or reset (a fresh server-generated PIN). New storefronts auto-get a 5-person
 * team (1 manager + 4 cashiers). Uses the scope-aware /org/nodes/{id}/pos-staff endpoints.
 */
export default function PosStaffCard({ base, merchantId }: { base: string; merchantId?: string }) {
  const [nodes, setNodes] = useState<OrgTreeNode[] | null>(null);
  const [nodeId, setNodeId] = useState<string>("");
  const [staff, setStaff] = useState<PosStaffMember[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [reveal, setReveal] = useState<PosStaffSecret[] | null>(null);   // show-once PIN panel

  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [role, setRole] = useState("cashier");

  const tok = () => getStaffToken() || "";

  // Scope to the in-scope merchant's subtree (operators get the whole forest from /org/tree).
  const scoped = useMemo(() => {
    const all = nodes || [];
    if (!merchantId) return all;
    const keep = new Set<string>([merchantId]);
    let grew = true;
    while (grew) {
      grew = false;
      for (const n of all) if (n.parent_id && keep.has(n.parent_id) && !keep.has(n.id)) { keep.add(n.id); grew = true; }
    }
    return all.filter((n) => keep.has(n.id));
  }, [nodes, merchantId]);

  // POS runs at a storefront (the sellable leaf) — only those have a till.
  const storefronts = useMemo(
    () => scoped.filter((n) => n.can_manage && n.is_active && n.sells),
    [scoped],
  );

  useEffect(() => {
    let live = true;
    orgTree(base, tok())
      .then((t) => { if (live) setNodes(t.nodes); })
      .catch(() => { if (live) setNodes([]); });
    return () => { live = false; };
  }, [base]);

  useEffect(() => {
    if (nodeId || storefronts.length === 0) return;
    setNodeId(storefronts[0].id);
  }, [storefronts, nodeId]);

  function reload(id = nodeId) {
    if (!id) return;
    setStaff(null);
    listPosStaff(base, tok(), id).then(setStaff).catch(() => setStaff([]));
  }
  useEffect(() => { if (nodeId) reload(nodeId); /* eslint-disable-next-line */ }, [nodeId]);

  function fail(e: unknown) {
    const m = e instanceof Error ? e.message : "Something went wrong";
    setErr(m.includes("403") ? "You don't have permission to manage staff here." : m);
  }

  async function run(fn: () => Promise<unknown>, after: (r: unknown) => void) {
    setBusy(true); setErr(null);
    try { after(await fn()); }
    catch (e) { fail(e); }
    finally { setBusy(false); }
  }

  function addStaff() {
    run(
      () => createPosStaff(base, tok(), nodeId, { full_name: name.trim(), role }),
      (r) => { setName(""); setRole("cashier"); setOpen(false); setReveal([r as PosStaffSecret]); reload(); },
    );
  }
  function resetPin(m: PosStaffMember) {
    run(
      () => resetPosStaffPin(base, tok(), nodeId, m.user_id),
      (r) => { setReveal([r as PosStaffSecret]); reload(); },
    );
  }
  function remove(m: PosStaffMember) {
    if (!window.confirm(`Remove ${m.full_name || "this operator"} from the till?`)) return;
    run(() => deletePosStaff(base, tok(), nodeId, m.user_id), () => reload());
  }

  if (nodes === null) {
    return (
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ fontWeight: 600 }}>Staff &amp; PINs (POS)</div>
        <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginTop: 6 }}>Loading…</div>
      </div>
    );
  }
  if (storefronts.length === 0) return null; // no till to manage → hide

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div style={{ fontWeight: 600 }}>Staff &amp; PINs (POS)</div>
      <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 12 }}>
        Till operators sign in at <code>/pos</code> with a 4–6 digit PIN (no email/password — they can't
        use the dashboard). PINs are unique per storefront and shown only once; lost a PIN → reset it.
      </div>

      <label style={{ fontSize: 13, display: "block", marginBottom: 12 }}>
        Storefront
        <select value={nodeId} disabled={busy} onChange={(e) => { setNodeId(e.target.value); setReveal(null); }}
                style={{ display: "block", marginTop: 2, minWidth: 280 }}>
          {storefronts.map((n) => <option key={n.id} value={n.id}>{n.name || "(unnamed)"}</option>)}
        </select>
      </label>

      {/* Show-once reveal panel */}
      {reveal && reveal.length > 0 && (
        <div style={{ border: "1px solid #bbf7d0", background: "#f0fdf4", borderRadius: 8, padding: 12, marginBottom: 12 }}>
          <div style={{ fontWeight: 600, fontSize: 13, color: "#166534" }}>
            New PIN{reveal.length > 1 ? "s" : ""} — note {reveal.length > 1 ? "them" : "it"} now, won't be shown again
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 8 }}>
            {reveal.map((m) => (
              <div key={m.user_id} style={{ background: "#fff", border: "1px solid #d1fae5", borderRadius: 6, padding: "6px 10px" }}>
                <span style={{ fontSize: 12, color: "var(--color-text-muted)", textTransform: "capitalize" }}>{m.role} · {m.full_name}</span>
                <div style={{ fontFamily: "monospace", fontSize: 20, fontWeight: 700, letterSpacing: 3 }}>{m.pin}</div>
              </div>
            ))}
          </div>
          <button className="btn btn-secondary btn-sm" style={{ marginTop: 10 }} onClick={() => setReveal(null)}>Done</button>
        </div>
      )}

      {/* Operators at this storefront */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {staff === null ? (
          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Loading staff…</span>
        ) : staff.length === 0 ? (
          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>No till operators yet — add one below.</span>
        ) : (
          staff.map((m) => (
            <div key={m.user_id} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, borderBottom: "1px solid var(--color-border,#eef0f3)", paddingBottom: 8 }}>
              <span style={{ flex: 1, fontWeight: 500 }}>{m.full_name || "(unnamed)"}</span>
              <span className="badge" style={{ background: "#eef2ff", color: "#3730a3", fontSize: 10, textTransform: "capitalize" }}>{m.role}</span>
              <span style={{ fontSize: 11, color: m.pin_set ? "#166534" : "#9ca3af" }}>{m.pin_set ? "PIN set" : "no PIN"}</span>
              <button disabled={busy} onClick={() => resetPin(m)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#2563eb", fontSize: 12, fontWeight: 600 }}>Reset PIN</button>
              <button aria-label="Remove" title="Remove operator" disabled={busy} onClick={() => remove(m)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#b91c1c", fontSize: 16 }}>×</button>
            </div>
          ))
        )}
      </div>

      {/* Add operator */}
      {!open ? (
        <button className="btn btn-secondary btn-sm" style={{ marginTop: 12 }} disabled={busy} onClick={() => setOpen(true)}>
          + Add operator
        </button>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: 12, marginTop: 12, border: "1px dashed var(--color-border,#e5e7eb)", borderRadius: 8, maxWidth: 420 }}>
          <input placeholder="Full name" value={name} onChange={(e) => setName(e.target.value)} />
          <label style={{ fontSize: 12 }}>Role
            <select value={role} onChange={(e) => setRole(e.target.value)} style={{ display: "block", width: "100%", textTransform: "capitalize" }}>
              {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
            </select>
          </label>
          <div style={{ display: "flex", gap: 8, marginTop: 2 }}>
            <button className="btn btn-primary btn-sm" disabled={busy || !name.trim()} onClick={addStaff}>Add &amp; generate PIN</button>
            <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => { setOpen(false); setErr(null); }}>Cancel</button>
          </div>
        </div>
      )}

      {err && <div style={{ color: "#b91c1c", fontSize: 12, marginTop: 10 }}>{err}</div>}
    </div>
  );
}
