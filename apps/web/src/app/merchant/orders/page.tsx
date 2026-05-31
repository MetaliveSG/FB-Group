"use client";

import { useState, useEffect, useCallback, Fragment } from "react";
import { useRouter } from "next/navigation";
import { getMerchantOrders, getApiBase } from "@/lib/api";
import { getStaffToken, clearStaffToken, getOperatorMerchant } from "@/lib/auth";
import { formatSGD } from "@/lib/format";
import MerchantSidebar from "@/components/MerchantSidebar";
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

  useEffect(() => { load(status); }, [load, status]);

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
