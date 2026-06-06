"use client";

import { useEffect, useState } from "react";
import {
  updateOrgNode,
  createOrgNode,
  listNodeAccounts,
  createNodeAccount,
  revokeNodeAccount,
  listVenueLeases,
  createLease,
  updateLease,
  deleteLease,
  getApiBase,
} from "@/lib/api";
import { getStaffToken } from "@/lib/auth";
import { Toggle } from "@/components/ui";
import type { OrgTreeNode, OrgNodeAccount, MerchantKpi, Lease, OrgNodeCreated, PosStaffSecret } from "@fbgroup/api-client";

const ROLE_STYLE: Record<string, { bg: string; fg: string }> = {
  CHAIN: { bg: "#dbeafe", fg: "#1e40af" },
  STOREFRONT: { bg: "#fef3c7", fg: "#92400e" },
};
const KIND_LABEL: Record<string, string> = { CHAIN: "Chain", STOREFRONT: "Storefront" };
const ACCOUNT_ROLES = ["manager", "cashier", "staff", "finance"];

/**
 * Node Detail — the single management surface for a member-tree node (master–detail drawer).
 * Rename · status · subscription fee · structure (chain) · logins · enter (storefront).
 * Self-contained: loads/edits via the api-client; calls onChanged() so the parent reloads the tree.
 */
export default function NodeDetailDrawer({
  node, nodes, kpi, canManage, onClose, onChanged, onEnter, onOpen,
}: {
  node: OrgTreeNode;
  nodes: OrgTreeNode[];
  kpi?: MerchantKpi;
  canManage: boolean;
  onClose: () => void;
  onChanged: () => void;
  onEnter: (args: { merchantId: string; tenantName: string; nodeId: string; nodeName: string; outletId?: string | null; storefrontName?: string }) => void;
  onOpen: () => void;
}) {
  const base = getApiBase();
  const rs = ROLE_STYLE[node.role] ?? { bg: "#f1f5f9", fg: "#334155" };
  const isChain = !node.sells;

  const byId = new Map(nodes.map((n) => [n.id, n]));
  const childCount = nodes.filter((n) => n.parent_id === node.id).length;
  // Breadcrumb path (names of ancestors).
  const path: string[] = [];
  for (let cur: OrgTreeNode | undefined = node; cur; cur = cur.parent_id ? byId.get(cur.parent_id) : undefined) {
    path.unshift(cur.name || cur.id);
  }
  // The tenant a storefront belongs to (nearest settlement boundary).
  function tenantOf(n: OrgTreeNode): OrgTreeNode | undefined {
    let cur: OrgTreeNode | undefined = n;
    while (cur) {
      if (cur.is_settlement_boundary) return cur;
      cur = cur.parent_id ? byId.get(cur.parent_id) : undefined;
    }
    return undefined;
  }

  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [name, setName] = useState(node.name ?? "");
  const [fee, setFee] = useState(node.subscription_fee ?? "");
  const [addOpen, setAddOpen] = useState(false);
  const [addKind, setAddKind] = useState(node.chain_stopped ? "STOREFRONT" : "CHAIN");
  const [addName, setAddName] = useState("");
  const [addFee, setAddFee] = useState("");
  const [posReveal, setPosReveal] = useState<PosStaffSecret[] | null>(null);  // show-once team PINs on SF create

  const [accounts, setAccounts] = useState<OrgNodeAccount[] | null>(null);
  const [acOpen, setAcOpen] = useState(false);
  const [acEmail, setAcEmail] = useState("");
  const [acName, setAcName] = useState("");
  const [acPass, setAcPass] = useState("");
  const [acRole, setAcRole] = useState("manager");

  // Leases — stalls leased INTO this venue (chains only). rent_type is the foodcourt/coffeeshop switch.
  const [leases, setLeases] = useState<Lease[] | null>(null);
  const [lsOpen, setLsOpen] = useState(false);
  const [lsTenant, setLsTenant] = useState("");
  const [lsType, setLsType] = useState("FIXED");
  const [lsRate, setLsRate] = useState("");
  const [rateEdit, setRateEdit] = useState<Record<string, string>>({});

  // Reset when the selected node changes; (re)load its logins.
  useEffect(() => {
    setName(node.name ?? "");
    setFee(node.subscription_fee ?? "");
    setAddOpen(false);
    setAddKind(node.chain_stopped ? "STOREFRONT" : "CHAIN");
    setAcOpen(false);
    setErr(null);
    setAccounts(null);
    setLeases(null);
    setLsOpen(false);
    setLsTenant("");
    setLsType("FIXED");
    setLsRate("");
    const tok = getStaffToken();
    if (tok && canManage) {
      listNodeAccounts(base, tok, node.id).then(setAccounts).catch(() => setAccounts([]));
      if (!node.sells) {
        listVenueLeases(base, tok, node.id)
          .then((ls) => { setLeases(ls); setRateEdit(Object.fromEntries(ls.map((l) => [l.id, l.rate]))); })
          .catch(() => setLeases([]));
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [node.id]);

  async function run(fn: () => Promise<unknown>, after?: (result: unknown) => void) {
    const tok = getStaffToken();
    if (!tok) return;
    setBusy(true);
    setErr(null);
    try {
      const result = await fn();
      after?.(result);
      onChanged();
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }
  const tok = () => getStaffToken()!;
  const reloadAccounts = () => listNodeAccounts(base, tok(), node.id).then(setAccounts).catch(() => {});
  const reloadLeases = () => listVenueLeases(base, tok(), node.id)
    .then((ls) => { setLeases(ls); setRateEdit(Object.fromEntries(ls.map((l) => [l.id, l.rate]))); })
    .catch(() => {});

  // Candidate stalls to lease in: any Storefront not under THIS venue (those are house stalls,
  // no lease needed) and not already leased here.
  const leasedIds = new Set((leases ?? []).map((l) => l.tenant_node_id));
  const underVenue = (n: OrgTreeNode): boolean => {
    for (let c: OrgTreeNode | undefined = n; c; c = c.parent_id ? byId.get(c.parent_id) : undefined) {
      if (c.id === node.id) return true;
    }
    return false;
  };
  const leaseCandidates = nodes.filter((n) => n.sells && n.id !== node.id && !leasedIds.has(n.id) && !underVenue(n));
  const rentUnit = (t: string) => (t === "GTO" ? "%" : "S$/mo");

  // One label style across the drawer (Title Case, 13/600) — used for headers and the inline
  // left-column row labels so every field reads consistently.
  const label = (s: string) => (
    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--color-text)" }}>{s}</span>
  );
  const ROW_LABEL = { minWidth: 120, fontSize: 13, fontWeight: 600 } as const;

  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.25)", zIndex: 40 }} />
      <aside
        style={{
          position: "fixed", top: 0, right: 0, bottom: 0, width: "min(440px, 92vw)", zIndex: 41,
          background: "#fff", boxShadow: "-8px 0 28px rgba(0,0,0,0.12)", overflowY: "auto",
          borderTop: `4px solid ${rs.fg}`,
        }}
      >
        <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 18 }}>
          {/* Header */}
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span className="badge" style={{ background: rs.bg, color: rs.fg, fontSize: 11, fontWeight: 700 }}>{KIND_LABEL[node.role] ?? node.role}</span>
            {node.is_settlement_boundary && (
              <span className="badge" style={{ background: "#dcfce7", color: "#166534", fontSize: 10 }}>Tenant</span>
            )}
            {!node.is_active && (
              <span className="badge" style={{ background: "#fee2e2", color: "#991b1b", fontSize: 10 }}>Suspended</span>
            )}
            <button onClick={onClose} aria-label="Close" style={{ marginLeft: "auto", background: "none", border: "none", fontSize: 22, cursor: "pointer", color: "var(--color-text-muted)", lineHeight: 1 }}>×</button>
          </div>
          <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{path.join(" › ")}</div>

          {err && <div className="alert alert-error" style={{ margin: 0 }}>{err}</div>}

          {/* Identity — rename */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {label("Name")}
            <div style={{ display: "flex", gap: 8 }}>
              <input value={name} disabled={!canManage} onChange={(e) => setName(e.target.value)} style={{ flex: 1 }} />
              <button className="btn btn-primary btn-sm" disabled={busy || !canManage || !name.trim() || name === node.name}
                onClick={() => run(() => updateOrgNode(base, tok(), node.id, { name: name.trim() }))}>
                Rename
              </button>
            </div>
          </div>

          {/* Primary action */}
          {node.sells ? (
            <button className="btn btn-primary" onClick={() => { const t = tenantOf(node); if (t) onEnter({ merchantId: t.id, tenantName: t.name || "", nodeId: node.id, nodeName: node.name || "", outletId: node.outlet_id, storefrontName: node.name || "" }); }}>
              Enter storefront → <span style={{ opacity: 0.8, fontWeight: 400 }}>menu · tables &amp; QR</span>
            </button>
          ) : (
            <div style={{ display: "flex", gap: 8 }}>
              {childCount > 0 && (
                <button className="btn btn-secondary" style={{ flex: 1 }} onClick={onOpen}>Open {childCount} inside →</button>
              )}
              {/* Any chain is enterable — console scoped to its subtree (the tenant = the whole business). */}
              <button className="btn btn-primary" style={{ flex: 1 }} onClick={() => { const t = tenantOf(node); if (t) onEnter({ merchantId: t.id, tenantName: t.name || "", nodeId: node.id, nodeName: node.name || "" }); }}>
                {node.is_settlement_boundary ? "Enter group console →" : "Enter console →"}
              </button>
            </div>
          )}

          {/* Status + Billing */}
          {canManage && (
            <div style={{ display: "flex", flexDirection: "column", gap: 12, borderTop: "1px solid var(--color-border,#e5e7eb)", paddingTop: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={ROW_LABEL}>Status</span>
                <Toggle on={node.is_active} disabled={busy}
                  onChange={() => run(() => updateOrgNode(base, tok(), node.id, { is_active: !node.is_active }))}
                  label={node.is_active ? "Suspend" : "Activate"} />
                <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{node.is_active ? "Active" : "Suspended"}</span>
                {kpi && <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--color-text-muted)" }}>{kpi.customers.toLocaleString()} cust</span>}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={ROW_LABEL}>Subscription Fee</span>
                <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>S$</span>
                <input type="number" min={0} step="0.01" value={fee} onChange={(e) => setFee(e.target.value)} placeholder="0.00" style={{ width: 100 }} />
                <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>/mo</span>
                <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => run(() => updateOrgNode(base, tok(), node.id, { subscription_fee: (fee || "0").toString() }))}>Save</button>
              </div>
            </div>
          )}

          {/* Structure — chains only */}
          {canManage && isChain && (
            <div style={{ display: "flex", flexDirection: "column", gap: 10, borderTop: "1px solid var(--color-border,#e5e7eb)", paddingTop: 14 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={ROW_LABEL}>Structure</span>
                <button className="btn btn-secondary btn-sm" disabled={busy}
                  onClick={() => run(() => updateOrgNode(base, tok(), node.id, { chain_stopped: !node.chain_stopped }))}>
                  {node.chain_stopped ? "Resume chain" : "Stop chain"}
                </button>
              </div>
              {!addOpen ? (
                <button className="btn btn-secondary btn-sm" style={{ alignSelf: "flex-start" }} onClick={() => { setAddOpen(true); setAddKind(node.chain_stopped ? "STOREFRONT" : "CHAIN"); }}>+ Add child</button>
              ) : (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 8, alignItems: "center", padding: 10, border: "1px dashed var(--color-border,#e5e7eb)", borderRadius: 8 }}>
                  <select value={addKind} onChange={(e) => setAddKind(e.target.value)}>
                    {(node.chain_stopped ? ["STOREFRONT"] : ["CHAIN", "STOREFRONT"]).map((r) => (
                      <option key={r} value={r}>{r === "CHAIN" ? "Chain" : "Storefront"}</option>
                    ))}
                  </select>
                  <input placeholder="Name" value={addName} onChange={(e) => setAddName(e.target.value)} style={{ flex: 1, minWidth: 130 }} />
                  <input type="number" min={0} step="0.01" placeholder="S$/mo" value={addFee} onChange={(e) => setAddFee(e.target.value)} style={{ width: 84 }} />
                  <button className="btn btn-primary btn-sm" disabled={busy || !addName.trim()}
                    onClick={() => run(
                      () => createOrgNode(base, tok(), { parent_id: node.id, role: addKind, name: addName.trim(), subscription_fee: addFee.trim() || undefined }),
                      (r) => {
                        setAddName(""); setAddFee(""); setAddOpen(false);
                        const team = (r as OrgNodeCreated)?.pos_team;
                        if (team && team.length) setPosReveal(team);   // starter POS team PINs for the new storefront
                      },
                    )}>Create</button>
                  <button className="btn btn-secondary btn-sm" onClick={() => setAddOpen(false)}>Cancel</button>
                </div>
              )}
              {posReveal && posReveal.length > 0 && (
                <div style={{ border: "1px solid #bbf7d0", background: "#f0fdf4", borderRadius: 8, padding: 12 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, color: "#166534" }}>
                    Storefront created · starter POS team (manage + reveal PINs in Settings → Staff &amp; PINs)
                  </div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
                    {posReveal.map((m) => (
                      <div key={m.user_id} style={{ background: "#fff", border: "1px solid #d1fae5", borderRadius: 6, padding: "6px 10px" }}>
                        <span style={{ fontSize: 11, color: "var(--color-text-muted)", textTransform: "capitalize" }}>{m.role} · {m.full_name}</span>
                        <div style={{ fontFamily: "monospace", fontSize: 18, fontWeight: 700, letterSpacing: 2 }}>{m.pin}</div>
                      </div>
                    ))}
                  </div>
                  <button className="btn btn-secondary btn-sm" style={{ marginTop: 10 }} onClick={() => setPosReveal(null)}>Done</button>
                </div>
              )}
            </div>
          )}

          {/* Tenancies — stalls leased into this venue (chains only). rent_type = the switch. */}
          {canManage && isChain && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, borderTop: "1px solid var(--color-border,#e5e7eb)", paddingTop: 14 }}>
              <div style={{ display: "flex", alignItems: "center" }}>
                {label(`Tenancies${leases ? ` (${leases.length})` : ""}`)}
                <button className="btn btn-secondary btn-sm" style={{ marginLeft: "auto" }} onClick={() => setLsOpen((s) => !s)}>+ Lease a stall</button>
              </div>
              <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
                Stalls leased into this venue. <b>FIXED</b> = flat rent (you stay blind to their sales) · <b>GTO</b> = % of turnover (you read it).
              </span>
              {leases === null ? (
                <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Loading…</span>
              ) : leases.length === 0 ? (
                <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>No leased stalls (house stalls need no lease).</span>
              ) : (
                leases.map((l) => (
                  <div key={l.id} style={{ display: "flex", flexDirection: "column", gap: 4, paddingBottom: 8, borderBottom: "1px solid #f1f5f9" }}>
                    <span style={{ fontSize: 13, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{l.tenant_name ?? l.tenant_node_id}</span>
                    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <select value={l.rent_type} disabled={busy}
                        onChange={(e) => run(() => updateLease(base, tok(), node.id, l.id, { rent_type: e.target.value }), reloadLeases)}
                        style={{ fontSize: 12 }}>
                        <option value="FIXED">FIXED</option>
                        <option value="GTO">GTO</option>
                      </select>
                      <input type="number" min={0} step="0.01" value={rateEdit[l.id] ?? l.rate}
                        onChange={(e) => setRateEdit((m) => ({ ...m, [l.id]: e.target.value }))} style={{ width: 96 }} />
                      <span style={{ fontSize: 11, color: "var(--color-text-muted)", minWidth: 42 }}>{rentUnit(l.rent_type)}</span>
                      <button className="btn btn-primary btn-sm" style={{ marginLeft: "auto" }} disabled={busy || (rateEdit[l.id] ?? l.rate) === l.rate}
                        onClick={() => run(() => updateLease(base, tok(), node.id, l.id, { rate: (rateEdit[l.id] || "0").toString() }), reloadLeases)}>Save</button>
                      <button aria-label="Remove lease" title="Remove lease" disabled={busy}
                        onClick={() => run(() => deleteLease(base, tok(), node.id, l.id), reloadLeases)}
                        style={{ background: "none", border: "none", cursor: "pointer", color: "#b91c1c", fontSize: 16 }}>×</button>
                    </div>
                  </div>
                ))
              )}
              {lsOpen && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center", padding: 10, border: "1px dashed var(--color-border,#e5e7eb)", borderRadius: 8 }}>
                  <select value={lsTenant} onChange={(e) => setLsTenant(e.target.value)} style={{ flex: 1, minWidth: 150 }}>
                    <option value="">Choose a stall…</option>
                    {leaseCandidates.map((n) => <option key={n.id} value={n.id}>{n.name ?? n.id}</option>)}
                  </select>
                  <select value={lsType} onChange={(e) => setLsType(e.target.value)} style={{ fontSize: 12 }}>
                    <option value="FIXED">FIXED</option>
                    <option value="GTO">GTO</option>
                  </select>
                  <input type="number" min={0} step="0.01" placeholder={rentUnit(lsType)} value={lsRate}
                    onChange={(e) => setLsRate(e.target.value)} style={{ width: 84 }} />
                  <button className="btn btn-primary btn-sm" disabled={busy || !lsTenant || !lsRate.trim()}
                    onClick={() => run(
                      () => createLease(base, tok(), node.id, { tenant_node_id: lsTenant, rent_type: lsType, rate: lsRate.trim() }),
                      () => { setLsTenant(""); setLsRate(""); setLsType("FIXED"); setLsOpen(false); reloadLeases(); },
                    )}>Lease</button>
                  <button className="btn btn-secondary btn-sm" onClick={() => setLsOpen(false)}>Cancel</button>
                </div>
              )}
            </div>
          )}

          {/* Web logins — dashboard accounts (email + password). POS PINs live in Settings → Staff & PINs. */}
          {canManage && (
            <div style={{ display: "flex", flexDirection: "column", gap: 8, borderTop: "1px solid var(--color-border,#e5e7eb)", paddingTop: 14 }}>
              <div style={{ display: "flex", alignItems: "center" }}>
                {label(`Web logins${accounts ? ` (${accounts.length})` : ""}`)}
                <button className="btn btn-secondary btn-sm" style={{ marginLeft: "auto" }} onClick={() => setAcOpen((s) => !s)}>+ Add login</button>
              </div>
              {accounts === null ? (
                <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Loading…</span>
              ) : accounts.length === 0 ? (
                <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>No logins at this node yet.</span>
              ) : (
                accounts.map((a) => (
                  <div key={a.assignment_id} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13 }}>
                    <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{a.email}</span>
                    <span className="badge" style={{ background: "#eef2ff", color: "#3730a3", fontSize: 10, textTransform: "capitalize" }}>{a.role}</span>
                    <button aria-label="Revoke" title="Revoke login" disabled={busy}
                      onClick={() => run(() => revokeNodeAccount(base, tok(), node.id, a.assignment_id), reloadAccounts)}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "#b91c1c", fontSize: 15 }}>×</button>
                  </div>
                ))
              )}
              {acOpen && (
                <div style={{ display: "flex", flexDirection: "column", gap: 6, padding: 10, border: "1px dashed var(--color-border,#e5e7eb)", borderRadius: 8 }}>
                  <input placeholder="Email" type="email" value={acEmail} onChange={(e) => setAcEmail(e.target.value)} />
                  <input placeholder="Full name (optional)" value={acName} onChange={(e) => setAcName(e.target.value)} />
                  <input placeholder="Temp password (min 8)" type="text" value={acPass} onChange={(e) => setAcPass(e.target.value)} />
                  <div style={{ display: "flex", gap: 8 }}>
                    <select value={acRole} onChange={(e) => setAcRole(e.target.value)} style={{ flex: 1, textTransform: "capitalize" }}>
                      {ACCOUNT_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                    <button className="btn btn-primary btn-sm" disabled={busy || !acEmail.trim() || acPass.length < 8}
                      onClick={() => run(
                        () => createNodeAccount(base, tok(), node.id, { email: acEmail.trim(), full_name: acName.trim(), password: acPass, role: acRole }),
                        () => { setAcEmail(""); setAcName(""); setAcPass(""); setAcOpen(false); reloadAccounts(); },
                      )}>Create login</button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
