"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { QRCodeSVG } from "qrcode.react";
import { orgTables, createTable, deleteTable, menuOutlets, getApiBase } from "@/lib/api";
import { getStaffToken, clearStaffToken, getOperatorMerchant } from "@/lib/auth";
import MerchantSidebar from "@/components/MerchantSidebar";
import NodeDirectory from "@/components/NodeDirectory";
import { useScope } from "@/lib/useScope";
import { Icons } from "@/components/ui";
import type { OrgTable, MenuAdminOutlet } from "@fbgroup/api-client";

/**
 * Tables & QR — add/remove tables; each gets a unique QR token the kitchen prints and pastes on the
 * table. The QR encodes the customer-scan URL (…/t/{token}) → a diner scans → orders from that outlet.
 * Locked to the entered storefront when you drilled in from the Platform Console; otherwise an outlet
 * picker lets you manage any outlet (group mode / direct merchant login).
 */
export default function TablesQrPage() {
  const router = useRouter();
  const base = getApiBase();
  const mid = () => getOperatorMerchant()?.id;
  const ctxOutlet = () => getOperatorMerchant()?.outletId;          // set → storefront mode (locked)
  const ctxNode = () => getOperatorMerchant()?.nodeId;             // entered chain → scope to its subtree
  const ctxOutletName = () => getOperatorMerchant()?.outletName;

  const [outlets, setOutlets] = useState<MenuAdminOutlet[]>([]);
  const [oid, setOid] = useState<string>("");                       // the outlet currently managed
  const [tables, setTables] = useState<OrgTable[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [num, setNum] = useState(1);          // the table number; label is always "T" + zero-padded
  const [seats, setSeats] = useState("4");
  const tableLabel = `T${String(num).padStart(2, "0")}`;
  const [printTarget, setPrintTarget] = useState<string | null>(null); // "all" | tableId | null

  const { scope, isOperator, nodes, ready, enter } = useScope();
  const needPick = ready && isOperator && !!scope && scope.tenantId === null;

  // The public customer-scan origin (where /t/{token} is served). Browser origin in this PoC.
  const [origin, setOrigin] = useState("");
  // Mount gate: everything here is client-only (localStorage drill-in context + window.origin + QR
  // SVGs). Rendering it during SSR mismatches the client → hydration errors. Render after mount.
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setOrigin(window.location.origin); setMounted(true); }, []);
  const scanUrl = (token: string) => `${origin}/t/${token}`;

  const outletName = ctxOutlet()
    ? (ctxOutletName() ?? "Storefront")
    : (outlets.find((o) => o.outlet_id === oid)?.name ?? "Storefront");

  // Load the outlet list once → pick the entered storefront (locked) or the first outlet.
  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) { router.push("/merchant/login"); return; }
    if (!ready || needPick) return;
    menuOutlets(base, tok, mid(), ctxNode())   // backend scopes to the entered node's subtree
      .then((all) => {
        setOutlets(all);
        const ctx = ctxOutlet();
        setOid(ctx || all[0]?.outlet_id || "");
        if (!ctx && all.length === 0) setLoading(false);
      })
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("401")) { clearStaffToken(); router.push("/merchant/login"); return; }
        setError(msg || "Failed to load outlets");
        setLoading(false);
      });
  }, [base, router, ready, needPick]); // eslint-disable-line react-hooks/exhaustive-deps

  const load = useCallback(async () => {
    const tok = getStaffToken();
    if (!tok || !oid) { setLoading(false); return; }
    setLoading(true);
    try {
      setTables(await orgTables(base, tok, oid, mid()));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load tables");
    } finally {
      setLoading(false);
    }
  }, [base, oid]);

  useEffect(() => { if (oid) load(); }, [oid, load]);

  // Default the number to the next free one (max existing "T##" + 1) on load and after each add.
  useEffect(() => {
    const maxN = tables.reduce((m, t) => {
      const mt = /^T(\d+)$/i.exec(t.label.trim());
      return mt ? Math.max(m, parseInt(mt[1], 10)) : m;
    }, 0);
    setNum(maxN + 1);
  }, [tables]);

  // Fire the print dialog once the print area has rendered for the chosen target, then clear it.
  useEffect(() => {
    if (!printTarget) return;
    const t = setTimeout(() => window.print(), 60);
    const done = () => setPrintTarget(null);
    window.addEventListener("afterprint", done);
    return () => { clearTimeout(t); window.removeEventListener("afterprint", done); };
  }, [printTarget]);

  async function run(fn: () => Promise<unknown>, after?: () => void) {
    const tok = getStaffToken();
    if (!tok || !oid) return;
    setBusy(true);
    setError(null);
    try {
      await fn();
      after?.();
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  function addTable() {
    const tok = getStaffToken();
    if (!tok || !oid || num < 1) return;
    run(() => createTable(base, tok, oid, { label: tableLabel, seats: parseInt(seats) || 4 }, mid()));
    // num auto-advances to the next free number via the effect when `tables` reloads.
  }

  function removeTable(t: OrgTable) {
    const tok = getStaffToken();
    if (!tok || !window.confirm(`Delete table ${t.label}? Its QR code will stop working.`)) return;
    run(() => deleteTable(base, tok, t.id, mid()));
  }

  const printList = printTarget === "all" ? tables : tables.filter((t) => t.id === printTarget);

  if (needPick) {
    return (
      <MerchantSidebar active="tables">
        <NodeDirectory feature="Tables & QR" nodes={nodes} currentNodeId={scope!.currentNodeId} onEnter={enter} />
      </MerchantSidebar>
    );
  }

  // Until mounted, render the same minimal tree the server did (no client-only data) → no mismatch.
  if (!mounted) {
    return (
      <MerchantSidebar active="tables">
        <div className="page-header"><h1 className="page-title">Tables &amp; QR</h1></div>
        <div className="page-loading"><div className="spinner" /> Loading…</div>
      </MerchantSidebar>
    );
  }

  return (
    <MerchantSidebar active="tables">
      {/* Print stylesheet: on print, show ONLY the print area (clean QR cards). */}
      <style>{`
        @media print {
          body * { visibility: hidden !important; }
          #qr-print-area, #qr-print-area * { visibility: visible !important; }
          #qr-print-area { position: absolute; left: 0; top: 0; width: 100%; }
          .qr-print-card { page-break-inside: avoid; break-inside: avoid; }
        }
      `}</style>

      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 10 }}>
        <div>
          <h1 className="page-title">Tables &amp; QR</h1>
          <p className="page-subtitle">{outletName} — one QR per table, printed &amp; pasted for diners to scan</p>
        </div>
        {tables.length > 0 && (
          <button className="btn btn-secondary" onClick={() => setPrintTarget("all")} disabled={busy || !origin}>
            🖨️ Print all QR codes
          </button>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Outlet picker — only when NOT locked to an entered storefront. */}
      {!ctxOutlet() && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <label style={{ fontWeight: 600, fontSize: 14 }}>Outlet</label>
            <select value={oid} onChange={(e) => setOid(e.target.value)} style={{ minWidth: 220 }} disabled={busy || outlets.length === 0}>
              {outlets.length === 0 && <option value="">No outlets</option>}
              {outlets.map((o) => <option key={o.outlet_id} value={o.outlet_id}>{o.name}</option>)}
            </select>
          </div>
        </div>
      )}

      {/* Add a table — label is a fixed "T" prefix + a number stepper → T01, T02, … */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ fontWeight: 600, fontSize: 14 }}>Table</span>
          {/* Fixed prefix */}
          <input value="T" disabled readOnly aria-label="Table prefix"
                 style={{ width: 44, textAlign: "center", fontWeight: 800, background: "var(--color-surface-2,#f1f5f9)" }} />
          {/* Number stepper: −  [02]  + */}
          <div style={{ display: "flex", alignItems: "center", border: "1px solid var(--color-border,#e5e7eb)", borderRadius: 8, overflow: "hidden" }}>
            <button className="btn btn-secondary" style={{ border: "none", borderRadius: 0, padding: "6px 12px", fontSize: 18, lineHeight: 1 }}
                    disabled={!oid || num <= 1} onClick={() => setNum((n) => Math.max(1, n - 1))} aria-label="Decrease table number">−</button>
            <input type="number" min={1} value={num}
                   onChange={(e) => setNum(Math.max(1, parseInt(e.target.value) || 1))}
                   onKeyDown={(e) => { if (e.key === "Enter") addTable(); }} disabled={!oid}
                   style={{ width: 64, textAlign: "center", border: "none", borderLeft: "1px solid var(--color-border,#e5e7eb)", borderRight: "1px solid var(--color-border,#e5e7eb)", borderRadius: 0, fontWeight: 700, MozAppearance: "textfield" }} />
            <button className="btn btn-secondary" style={{ border: "none", borderRadius: 0, padding: "6px 12px", fontSize: 18, lineHeight: 1 }}
                    disabled={!oid} onClick={() => setNum((n) => n + 1)} aria-label="Increase table number">+</button>
          </div>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>→ <strong>{tableLabel}</strong></span>
          <span style={{ fontWeight: 600, fontSize: 14, marginLeft: 8 }}>Seats</span>
          <input type="number" min={1} max={50} value={seats}
                 onChange={(e) => setSeats(e.target.value)} style={{ width: 72 }} disabled={!oid} />
          <button className="btn btn-primary btn-sm" style={{ marginLeft: "auto" }}
                  disabled={busy || !oid} onClick={addTable}>
            + Add table
          </button>
        </div>
      </div>

      {loading ? (
        <div className="page-loading"><div className="spinner" /> Loading tables…</div>
      ) : !oid ? (
        <p style={{ color: "var(--color-text-muted)" }}>No outlet to manage. Onboard a storefront from the Platform Console first.</p>
      ) : tables.length === 0 ? (
        <p style={{ color: "var(--color-text-muted)" }}>No tables yet. Add one above to generate its QR code.</p>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 16 }}>
          {tables.map((t) => (
            <div className="card" key={t.id} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, textAlign: "center" }}>
              <div style={{ display: "flex", width: "100%", justifyContent: "space-between", alignItems: "center" }}>
                <strong style={{ fontSize: 16 }}>{t.label}</strong>
                <button className="btn btn-secondary btn-sm" style={{ padding: "2px 8px" }} disabled={busy}
                        onClick={() => removeTable(t)} title="Delete table" aria-label="Delete table">
                  <Icons.Trash2 size={15} aria-hidden />
                </button>
              </div>
              {t.qr_token && origin ? (
                <div style={{ background: "#fff", padding: 8, borderRadius: 8, border: "1px solid var(--color-border,#e5e7eb)" }}>
                  <QRCodeSVG value={scanUrl(t.qr_token)} size={148} level="M" />
                </div>
              ) : (
                <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>No QR token</div>
              )}
              <div style={{ fontSize: 11, color: "var(--color-text-muted)", wordBreak: "break-all" }}>{t.qr_token}</div>
              <button className="btn btn-secondary btn-sm" style={{ width: "100%" }} disabled={!t.qr_token || !origin}
                      onClick={() => setPrintTarget(t.id)}>
                🖨️ Print
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Print area — hidden on screen, the only thing visible on print. One card per chosen table. */}
      <div id="qr-print-area" style={{ position: "absolute", left: -99999, top: 0 }} aria-hidden>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 24, padding: 24 }}>
          {printList.map((t) => t.qr_token && (
            <div key={t.id} className="qr-print-card"
                 style={{ width: 300, border: "2px solid #111", borderRadius: 12, padding: 24, textAlign: "center",
                          display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
              <div style={{ fontSize: 22, fontWeight: 800 }}>{outletName}</div>
              <div style={{ fontSize: 16, fontWeight: 600, color: "#444" }}>Table {t.label}</div>
              <QRCodeSVG value={scanUrl(t.qr_token)} size={220} level="M" />
              <div style={{ fontSize: 18, fontWeight: 700 }}>📱 Scan to order</div>
              <div style={{ fontSize: 11, color: "#666" }}>Point your phone camera at the code</div>
            </div>
          ))}
        </div>
      </div>
    </MerchantSidebar>
  );
}
