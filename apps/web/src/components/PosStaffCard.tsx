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
import { Icons } from "@/components/ui";
import type { OrgTreeNode, PosStaffMember } from "@fbgroup/api-client";

// POS palette — Supervisor (on-floor lead) or Cashier. `store_manager`/older values map for display.
const ROLES = ["cashier", "supervisor"];
const ROLE_LABEL: Record<string, string> = { cashier: "Cashier", supervisor: "Supervisor" };
const roleLabel = (r: string) => ROLE_LABEL[r] ?? r.replace(/_/g, " ");
// Roles allowed to void/cancel a transaction (the Supervisor differentiator). Surfaced as a tag.
const CAN_VOID = new Set(["supervisor"]);

/**
 * "Staff & PINs (POS)" — merchant-owner self-serve for POS operators.
 * POS operators are PIN-only (kind="pos"): they sign in at /pos with a 4–6 digit PIN and CANNOT log
 * into the web dashboard. PINs are readable (owner choice): the eye reveals an operator's current PIN,
 * and the owner can change it to a chosen value or auto-generate one. New storefronts auto-get a
 * starter team (1 manager + 2 cashiers). Uses the scope-aware /org/nodes/{id}/pos-staff endpoints.
 */
export default function PosStaffCard({ base, merchantId }: { base: string; merchantId?: string }) {
  const [nodes, setNodes] = useState<OrgTreeNode[] | null>(null);
  const [nodeId, setNodeId] = useState<string>("");
  const [staff, setStaff] = useState<PosStaffMember[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [shown, setShown] = useState<Record<string, boolean>>({});   // which rows' PINs are revealed
  const [editing, setEditing] = useState<string | null>(null);       // user_id whose PIN is being changed
  const [editPin, setEditPin] = useState("");

  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [role, setRole] = useState("cashier");
  const [newPin, setNewPin] = useState("");
  const [newPinShown, setNewPinShown] = useState(false);

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

  // POS runs at a storefront (the sellable leaf).
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
    setStaff(null); setShown({}); setEditing(null);
    listPosStaff(base, tok(), id).then(setStaff).catch(() => setStaff([]));
  }
  useEffect(() => { if (nodeId) reload(nodeId); /* eslint-disable-next-line */ }, [nodeId]);

  function fail(e: unknown) {
    const m = e instanceof Error ? e.message : "Something went wrong";
    if (m.includes("pin_taken") || m.includes("409")) setErr("Another operator at this storefront already uses that PIN.");
    else setErr(m.includes("403") ? "You don't have permission to manage staff here." : m);
  }
  async function run(fn: () => Promise<unknown>, after: () => void) {
    setBusy(true); setErr(null);
    try { await fn(); after(); }
    catch (e) { fail(e); }
    finally { setBusy(false); }
  }

  function addStaff() {
    if (newPin && !/^\d{4,6}$/.test(newPin)) { setErr("PIN must be 4–6 digits."); return; }
    run(
      () => createPosStaff(base, tok(), nodeId, { full_name: name.trim(), role, pin: newPin || undefined }),
      () => { setName(""); setRole("cashier"); setNewPin(""); setNewPinShown(false); setOpen(false); reload(); },
    );
  }
  function saveEditPin(m: PosStaffMember) {
    if (!/^\d{4,6}$/.test(editPin)) { setErr("PIN must be 4–6 digits."); return; }
    run(() => resetPosStaffPin(base, tok(), nodeId, m.user_id, editPin), () => { setEditing(null); setEditPin(""); reload(); });
  }
  function randomize(m: PosStaffMember) {
    run(() => resetPosStaffPin(base, tok(), nodeId, m.user_id), () => { setEditing(null); reload(); });
  }
  function remove(m: PosStaffMember) {
    if (!window.confirm(`Remove ${m.full_name || "this operator"}?`)) return;
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
  if (storefronts.length === 0) return null;

  const eyeBtn = { background: "none", border: "none", cursor: "pointer", color: "#64748b", padding: 0, display: "inline-flex", alignItems: "center" } as const;

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div style={{ fontWeight: 600 }}>Staff &amp; PINs (POS)</div>
      <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 12 }}>
        Operators sign in at <code>/pos</code> with a 4–6 digit PIN (no email/password — they can't use the
        dashboard). Tap the eye to reveal a PIN; change it to any unused number or generate a new one.
      </div>

      <label style={{ fontSize: 13, display: "block", marginBottom: 12 }}>
        Storefront
        <select value={nodeId} disabled={busy} onChange={(e) => setNodeId(e.target.value)}
                style={{ display: "block", marginTop: 2, minWidth: 280 }}>
          {storefronts.map((n) => <option key={n.id} value={n.id}>{n.name || "(unnamed)"}</option>)}
        </select>
      </label>

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {staff === null ? (
          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Loading staff…</span>
        ) : staff.length === 0 ? (
          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>No operators yet — add one below.</span>
        ) : (
          staff.map((m) => (
            <div key={m.user_id} style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 13, borderBottom: "1px solid var(--color-border,#eef0f3)", paddingBottom: 8 }}>
              <span style={{ flex: 1, fontWeight: 500 }}>{m.full_name || "(unnamed)"}</span>
              {CAN_VOID.has(m.role) && (
                <span title="Can void/cancel a transaction" style={{ fontSize: 10, fontWeight: 600, color: "#166534", background: "#dcfce7", borderRadius: 4, padding: "1px 6px" }}>Allow void</span>
              )}
              <span className="badge" style={{ background: "#eef2ff", color: "#3730a3", fontSize: 10 }}>{roleLabel(m.role)}</span>
              {editing === m.user_id ? (
                <>
                  <input autoFocus inputMode="numeric" value={editPin} placeholder="4–6 digits"
                         onChange={(e) => setEditPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                         style={{ width: 90, fontFamily: "monospace" }} />
                  <button disabled={busy} onClick={() => saveEditPin(m)} style={{ background: "none", border: "none", cursor: "pointer", color: "#166534", fontWeight: 600, fontSize: 12 }}>Save</button>
                  <button disabled={busy} title="Generate random" onClick={() => randomize(m)} style={eyeBtn} aria-label="Generate random PIN"><Icons.RefreshCw size={15} /></button>
                  <button disabled={busy} onClick={() => { setEditing(null); setEditPin(""); }} style={{ background: "none", border: "none", cursor: "pointer", color: "#64748b", fontSize: 12 }}>Cancel</button>
                </>
              ) : (
                <>
                  <span style={{ fontFamily: "monospace", fontSize: 15, letterSpacing: 2, minWidth: 64, textAlign: "right" }}>
                    {shown[m.user_id] ? (m.pin || "—") : "••••••"}
                  </span>
                  <button title={shown[m.user_id] ? "Hide PIN" : "Reveal PIN"} disabled={busy}
                          onClick={() => setShown((s) => ({ ...s, [m.user_id]: !s[m.user_id] }))}
                          style={eyeBtn} aria-label={shown[m.user_id] ? "Hide PIN" : "Reveal PIN"}>
                    {shown[m.user_id] ? <Icons.EyeOff size={16} /> : <Icons.Eye size={16} />}
                  </button>
                  <button disabled={busy} onClick={() => { setEditing(m.user_id); setEditPin(""); }}
                          style={{ background: "none", border: "none", cursor: "pointer", color: "#2563eb", fontSize: 12, fontWeight: 600 }}>Change PIN</button>
                  <button aria-label="Remove operator" title="Remove operator" disabled={busy} onClick={() => remove(m)}
                          style={{ background: "none", border: "none", cursor: "pointer", color: "#b91c1c", fontSize: 16 }}>×</button>
                </>
              )}
            </div>
          ))
        )}
      </div>

      {!open ? (
        <button className="btn btn-secondary btn-sm" style={{ marginTop: 12 }} disabled={busy} onClick={() => setOpen(true)}>
          + Add operator
        </button>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, padding: 12, marginTop: 12, border: "1px dashed var(--color-border,#e5e7eb)", borderRadius: 8, maxWidth: 440 }}>
          <input placeholder="Full name" value={name} onChange={(e) => setName(e.target.value)} />
          <div style={{ display: "flex", gap: 8 }}>
            <label style={{ fontSize: 12, flex: 1 }}>Role
              <select value={role} onChange={(e) => setRole(e.target.value)} style={{ display: "block", width: "100%" }}>
                {ROLES.map((r) => <option key={r} value={r}>{roleLabel(r)}</option>)}
              </select>
            </label>
            <label style={{ fontSize: 12, flex: 1 }}>PIN (blank = auto)
              <span style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <input type={newPinShown ? "text" : "password"} inputMode="numeric" placeholder="4–6 digits" value={newPin}
                       onChange={(e) => setNewPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
                       style={{ width: "100%", fontFamily: "monospace" }} />
                <button type="button" onClick={() => setNewPinShown((v) => !v)} style={eyeBtn} aria-label={newPinShown ? "Hide PIN" : "Show PIN"}>
                  {newPinShown ? <Icons.EyeOff size={16} /> : <Icons.Eye size={16} />}
                </button>
              </span>
            </label>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 2 }}>
            <button className="btn btn-primary btn-sm" disabled={busy || !name.trim()} onClick={addStaff}>Add operator</button>
            <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => { setOpen(false); setErr(null); }}>Cancel</button>
          </div>
        </div>
      )}

      {err && <div style={{ color: "#b91c1c", fontSize: 12, marginTop: 10 }}>{err}</div>}
    </div>
  );
}
