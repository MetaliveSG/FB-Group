"use client";

import { useState, useEffect, useCallback, Fragment } from "react";
import { useRouter } from "next/navigation";
import { getMerchantOrders, redeemVoucher, getApiBase } from "@/lib/api";
import { getStaffToken, clearStaffToken, getOperatorMerchant } from "@/lib/auth";
import { formatSGD } from "@/lib/format";
import MerchantSidebar from "@/components/MerchantSidebar";
import NodeDirectory from "@/components/NodeDirectory";
import { useScope } from "@/lib/useScope";
import type { MerchantOrder } from "@fbgroup/api-client";

const STATUSES = ["", "pending", "accepted", "preparing", "ready", "completed", "cancelled"];

function statusBadge(status: string) {
  const done = status === "completed";
  const bad = status === "cancelled" || status === "declined";
  return { background: done ? "#dcfce7" : bad ? "#fee2e2" : "#fef9c3", color: done ? "#166534" : bad ? "#991b1b" : "#854d0e" };
}

export default function MerchantOrdersPage() {
  const router = useRouter();
  const base = getApiBase();
  const [orders, setOrders] = useState<MerchantOrder[] | null>(null);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [vCode, setVCode] = useState("");
  const [vBusy, setVBusy] = useState(false);
  const [vMsg, setVMsg] = useState<{ id: string; text: string; ok: boolean } | null>(null);

  // Tree-scoped guard: orders are tenant-wide → an operator above a tenant boundary picks a merchant first.
  const { scope, isOperator, nodes, ready, enter } = useScope();
  const needPick = ready && isOperator && !!scope && scope.tenantId === null;

  const load = useCallback(async (s: string) => {
    const tok = getStaffToken();
    if (!tok) { router.push("/merchant/login"); return; }
    try {
      setOrders(await getMerchantOrders(base, tok, { status: s || undefined }, getOperatorMerchant()?.id));
    } catch (err: unknown) {
      const m = err instanceof Error ? err.message : "";
      if (m.includes("401")) { clearStaffToken(); router.push("/merchant/login"); }
      else setError(m || "Failed to load orders");
    }
  }, [base, router]);

  useEffect(() => { if (ready && !needPick) load(status); }, [load, status, ready, needPick]);

  async function applyVoucher(orderId: string) {
    const code = vCode.trim();
    if (!code) return;
    const tok = getStaffToken();
    if (!tok) { router.push("/merchant/login"); return; }
    setVBusy(true); setVMsg(null);
    try {
      const r = await redeemVoucher(base, tok, code, { order_id: orderId });
      setVMsg({ id: orderId, ok: true,
        text: `Applied $${(r.discount_amount ?? 0).toFixed(2)} — new total $${(r.order_total ?? 0).toFixed(2)}` });
      setVCode("");
      await load(status);
    } catch (err: unknown) {
      setVMsg({ id: orderId, ok: false, text: err instanceof Error ? err.message : "Voucher could not be applied" });
    } finally {
      setVBusy(false);
    }
  }

  if (needPick) {
    return (
      <MerchantSidebar active="orders">
        <NodeDirectory feature="Orders" nodes={nodes} currentNodeId={scope!.currentNodeId} onEnter={enter} />
      </MerchantSidebar>
    );
  }

  return (
    <MerchantSidebar active="orders">
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 className="page-title">Orders</h1>
          <p className="page-subtitle">All orders across your outlets</p>
        </div>
        <select value={status} onChange={(e) => setStatus(e.target.value)} style={{ maxWidth: 180 }}>
          {STATUSES.map((s) => <option key={s} value={s}>{s ? s[0].toUpperCase() + s.slice(1) : "All statuses"}</option>)}
        </select>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div className="table-wrapper" style={{ border: "none", borderRadius: 0 }}>
          <table>
            <thead>
              <tr>
                <th style={{ width: 24 }}></th>
                <th>Order</th><th>Outlet</th><th>Customer</th><th>Status</th><th>Total</th>
              </tr>
            </thead>
            <tbody>
              {orders === null ? (
                <tr><td colSpan={6} style={{ textAlign: "center", padding: 20, color: "var(--color-text-muted)" }}>Loading…</td></tr>
              ) : orders.length === 0 ? (
                <tr><td colSpan={6} style={{ textAlign: "center", padding: 20, color: "var(--color-text-muted)" }}>No orders</td></tr>
              ) : (
                orders.map((o) => {
                  const open = expanded === o.id;
                  return (
                    <Fragment key={o.id}>
                      <tr onClick={() => setExpanded(open ? null : o.id)} style={{ cursor: "pointer" }}>
                        <td style={{ textAlign: "center", color: "var(--color-text-muted)" }}>{open ? "▾" : "▸"}</td>
                        <td><code style={{ fontSize: 12 }}>{o.id.slice(0, 8)}…</code>{o.table_label ? <span style={{ color: "var(--color-text-muted)", fontSize: 12 }}> · {o.table_label}</span> : ""}</td>
                        <td style={{ fontSize: 13 }}>{o.outlet_name}</td>
                        <td style={{ fontSize: 13 }}>{o.customer_name ?? <span style={{ color: "var(--color-text-muted)" }}>Walk-in</span>}</td>
                        <td><span className="badge" style={statusBadge(o.status)}>{o.status}</span></td>
                        <td style={{ fontWeight: 700 }}>{formatSGD(o.total)}</td>
                      </tr>
                      {open && (
                        <tr>
                          <td colSpan={6} style={{ background: "var(--color-surface-alt, #f8fafc)", padding: "12px 20px" }}>
                            <table style={{ width: "100%", fontSize: 13 }}>
                              <tbody>
                                {o.items.map((it, i) => (
                                  <tr key={i}>
                                    <td style={{ padding: "2px 0" }}>
                                      <strong>{it.quantity}×</strong> {it.name_snapshot}
                                      {it.modifiers && it.modifiers.length > 0 && (
                                        <span style={{ color: "var(--color-text-muted)" }}> — {it.modifiers.map((m) => m.name).join(", ")}</span>
                                      )}
                                    </td>
                                    <td style={{ textAlign: "right" }}>{formatSGD(it.line_total)}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                            <div style={{ borderTop: "1px dashed var(--color-border)", marginTop: 8, paddingTop: 8, maxWidth: 280, marginLeft: "auto", fontSize: 13 }}>
                              {([["Subtotal", o.subtotal], ["Service charge", o.service_charge], ["GST", o.tax]] as [string, number][]).map(([l, v]) => (
                                <div key={l} style={{ display: "flex", justifyContent: "space-between", color: "var(--color-text-muted)" }}>
                                  <span>{l}</span><span>{formatSGD(v)}</span>
                                </div>
                              ))}
                              <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 700, marginTop: 2 }}>
                                <span>Total</span><span>{formatSGD(o.total)}</span>
                              </div>
                            </div>
                            {/* Cashier: scan/enter a voucher to apply it to this order */}
                            {o.status !== "completed" && o.status !== "cancelled" && (
                              <div style={{ borderTop: "1px dashed var(--color-border)", marginTop: 10, paddingTop: 10, display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                                <input
                                  value={vCode}
                                  onChange={(e) => setVCode(e.target.value.toUpperCase())}
                                  placeholder="Scan or enter voucher code"
                                  style={{ flex: 1, minWidth: 180, fontFamily: "monospace" }}
                                  onKeyDown={(e) => { if (e.key === "Enter") applyVoucher(o.id); }}
                                />
                                <button className="btn btn-primary btn-sm" disabled={vBusy} onClick={() => applyVoucher(o.id)}>
                                  {vBusy ? "Applying…" : "Apply voucher"}
                                </button>
                                {vMsg && vMsg.id === o.id && (
                                  <span style={{ fontSize: 13, color: vMsg.ok ? "#166534" : "#991b1b" }}>{vMsg.text}</span>
                                )}
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </MerchantSidebar>
  );
}
