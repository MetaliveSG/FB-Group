"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  orgTree, getMyPermissions,
  reportsSummary, reportsSales, reportsTopItems, reportsPayments, reportsRollup,
  getApiBase,
} from "@/lib/api";
import { getStaffToken, clearStaffToken, getOperatorMerchant } from "@/lib/auth";
import { formatSGD } from "@/lib/format";
import { REPORT_TIMEZONES } from "@/lib/timezones";
import MerchantSidebar from "@/components/MerchantSidebar";
import type {
  OrgTreeNode, ReportScope, ReportTotals, SalesPeriod, TopItem, PaymentSplitRow, RollupRow,
} from "@fbgroup/api-client";

type SourceSel = { platform: boolean; nodeId?: string; label: string };
type Preset = "today" | "7d" | "30d";

function isoDaysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  // Local (browser TZ, i.e. SGT) calendar date — NOT toISOString(), which would convert to UTC and
  // roll the date back 8h. The backend treats the YYYY-MM-DD as an SG-local day.
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}


export default function ReportsPage() {
  const router = useRouter();
  const base = getApiBase();
  const tok = () => getStaffToken();

  const [isOperator, setIsOperator] = useState(false);
  const [nodes, setNodes] = useState<OrgTreeNode[]>([]);
  const [source, setSource] = useState<SourceSel | null>(null);
  const [preset, setPreset] = useState<Preset>("7d");
  const [start, setStart] = useState(isoDaysAgo(6));
  const [end, setEnd] = useState(isoDaysAgo(0));
  const [tab, setTab] = useState<"overview" | "payments">("overview");
  // tzOverride = the display-lens dropdown ("" = use the tenant's business reporting tz).
  // businessTz = the tenant's canonical reporting tz (the "books"), echoed by the summary payload.
  const [tzOverride, setTzOverride] = useState("");
  const [businessTz, setBusinessTz] = useState("Asia/Singapore");

  const [summary, setSummary] = useState<ReportTotals | null>(null);
  const [sales, setSales] = useState<SalesPeriod[]>([]);
  const [items, setItems] = useState<TopItem[]>([]);
  const [payments, setPayments] = useState<PaymentSplitRow[]>([]);
  const [rollup, setRollup] = useState<RollupRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Apply a preset → date range.
  function applyPreset(p: Preset) {
    setPreset(p);
    setEnd(isoDaysAgo(0));
    setStart(p === "today" ? isoDaysAgo(0) : p === "7d" ? isoDaysAgo(6) : isoDaysAgo(29));
  }

  // Load the SOURCE options (caller's visible tree) + whether they're an operator (→ Platform option).
  useEffect(() => {
    const t = tok();
    if (!t) { router.push("/merchant/login"); return; }
    const mid = getOperatorMerchant()?.id;
    Promise.all([orgTree(base, t), getMyPermissions(base, t, mid)])
      .then(([tree, caps]) => {
        const ns = tree.nodes ?? [];
        setNodes(ns);
        const op = !!caps.is_super_admin || caps.permissions.includes("platform.merchants.view");
        setIsOperator(op);
        // Default SOURCE: operator → Platform; node account → the shallowest node they can see.
        const ctxNode = getOperatorMerchant()?.nodeId;
        if (ctxNode && ns.some((n) => n.id === ctxNode)) {
          const n = ns.find((x) => x.id === ctxNode)!;
          setSource({ platform: false, nodeId: n.id, label: n.name ?? n.id });
        } else if (op) {
          setSource({ platform: true, label: "Platform — all merchants" });
        } else if (ns.length) {
          const root = [...ns].sort((a, b) => a.depth - b.depth)[0];
          setSource({ platform: false, nodeId: root.id, label: root.name ?? root.id });
        }
      })
      .catch((e: unknown) => {
        const m = e instanceof Error ? e.message : "";
        if (m.includes("401")) { clearStaffToken(); router.push("/merchant/login"); return; }
        setError(m || "Failed to load report scope");
        setLoading(false);
      });
  }, [base, router]);

  const scope = useCallback((): ReportScope => ({
    platform: source?.platform || undefined,
    nodeId: source?.nodeId,
    merchantId: getOperatorMerchant()?.id,
    start, end,
    tz: tzOverride || undefined,   // "" → backend uses the tenant's business reporting tz
  }), [source, start, end, tzOverride]);

  const load = useCallback(async () => {
    const t = tok();
    if (!t || !source) return;
    setLoading(true);
    setError(null);
    const sc = scope();
    const gran = preset === "today" ? "hour" : "day";
    try {
      const [su, sa, it, pa, ro] = await Promise.all([
        reportsSummary(base, t, sc),
        reportsSales(base, t, sc, gran),
        reportsTopItems(base, t, sc, 8),
        reportsPayments(base, t, sc),
        reportsRollup(base, t, sc),
      ]);
      setSummary(su); setSales(sa); setItems(it); setPayments(pa); setRollup(ro);
      // The summary echoes the effective tz; when no override is active that IS the business tz.
      if (!tzOverride) setBusinessTz(su.timezone);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load reports");
    } finally {
      setLoading(false);
    }
  }, [base, source, scope, preset, tzOverride]);

  useEffect(() => { if (source) load(); }, [source, start, end, tzOverride, load]);

  // SOURCE options: Platform (operators) + every visible node, indented by depth.
  const sourceOptions: SourceSel[] = [
    ...(isOperator ? [{ platform: true, label: "Platform — all merchants" } as SourceSel] : []),
    ...[...nodes].sort((a, b) => a.depth - b.depth || (a.name ?? "").localeCompare(b.name ?? ""))
      .map((n) => ({ platform: false, nodeId: n.id, label: `${"  ".repeat(n.depth)}${n.name ?? n.id}` })),
  ];

  function onSelectSource(v: string) {
    if (v === "__platform__") { setSource({ platform: true, label: "Platform — all merchants" }); return; }
    const n = nodes.find((x) => x.id === v);
    if (n) setSource({ platform: false, nodeId: n.id, label: n.name ?? n.id });
  }

  function exportCsv() {
    const rows = [["Node", "Revenue", "Orders", "AOV"],
      ...rollup.map((r) => [r.name, r.revenue.toFixed(2), String(r.orders), r.avg_order_value.toFixed(2)])];
    const csv = rows.map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `report-${start}_${end}.csv`;
    a.click();
  }

  const maxSale = Math.max(1, ...sales.map((s) => s.revenue));
  const payTotal = Math.max(1, payments.reduce((s, p) => s + p.amount, 0));

  return (
    <MerchantSidebar active="reports">
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 10 }}>
        <div>
          <h1 className="page-title">Reports</h1>
          <p className="page-subtitle">Sales &amp; performance{source ? ` — ${source.label.trim()}` : ""}</p>
        </div>
        <button className="btn btn-secondary" onClick={exportCsv} disabled={loading || !rollup.length}>⬇ Export CSV</button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Controls: SOURCE + PERIOD */}
      <div className="card" style={{ marginBottom: 16, display: "flex", gap: 16, alignItems: "center", flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <label style={{ fontWeight: 600, fontSize: 13 }}>SOURCE</label>
          <select value={source?.platform ? "__platform__" : (source?.nodeId ?? "")}
                  onChange={(e) => onSelectSource(e.target.value)} style={{ minWidth: 240 }}>
            {sourceOptions.map((o) => (
              <option key={o.platform ? "__platform__" : o.nodeId} value={o.platform ? "__platform__" : o.nodeId}>{o.label}</option>
            ))}
          </select>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <label style={{ fontWeight: 600, fontSize: 13 }}>PERIOD</label>
          {(["today", "7d", "30d"] as Preset[]).map((p) => (
            <button key={p} className={`btn btn-sm ${preset === p ? "btn-primary" : "btn-secondary"}`}
                    onClick={() => applyPreset(p)}>{p === "today" ? "Today" : p === "7d" ? "7 days" : "30 days"}</button>
          ))}
          <input type="date" value={start} max={end} onChange={(e) => { setStart(e.target.value); setPreset("30d"); }} style={{ marginLeft: 6 }} />
          <span style={{ color: "var(--color-text-muted)" }}>→</span>
          <input type="date" value={end} min={start} onChange={(e) => setEnd(e.target.value)} />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <label style={{ fontWeight: 600, fontSize: 13 }}>TIMEZONE</label>
          <select value={tzOverride} onChange={(e) => setTzOverride(e.target.value)} style={{ minWidth: 210 }}>
            <option value="">Business — {businessTz}</option>
            {REPORT_TIMEZONES.map(([z, label]) => (
              <option key={z} value={z}>{label}</option>
            ))}
          </select>
        </div>
        {loading && <span className="spinner" />}
      </div>

      {/* When a display-lens tz is chosen that differs from the books, say so loudly. */}
      {tzOverride && tzOverride !== businessTz && (
        <div className="alert" style={{ background: "#fef3c7", border: "1px solid #fcd34d", color: "#92400e", marginBottom: 16 }}>
          Viewing in <strong>{tzOverride}</strong> — differs from the business reporting timezone
          (<strong>{businessTz}</strong>). Official totals (payouts/GST/daily close) use {businessTz}.
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: "flex", gap: 6, marginBottom: 16, borderBottom: "1px solid var(--color-border,#e5e7eb)" }}>
        {(["overview", "payments"] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
                  style={{ background: "none", border: "none", borderBottom: tab === t ? "2px solid var(--color-primary)" : "2px solid transparent",
                           padding: "8px 14px", cursor: "pointer", fontWeight: 700, color: tab === t ? "var(--color-primary)" : "var(--color-text-muted)", textTransform: "capitalize" }}>
            {t}
          </button>
        ))}
      </div>

      {tab === "overview" && summary && (
        <>
          {/* KPI tiles */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, marginBottom: 18 }}>
            {[
              ["Total Sales", formatSGD(summary.revenue)],
              ["No. of Transactions", String(summary.orders)],
              ["Avg Sales / Transaction", formatSGD(summary.avg_order_value)],
              ["Unique Customers", String(summary.unique_customers)],
            ].map(([label, val], i) => (
              <div className="card" key={label} style={i === 0 ? { background: "var(--color-primary,#1e293b)", color: "#fff" } : {}}>
                <div style={{ fontSize: 12, opacity: 0.8 }}>{label}</div>
                <div style={{ fontSize: 26, fontWeight: 900, marginTop: 4 }}>{val}</div>
              </div>
            ))}
          </div>
          <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginBottom: 16 }}>
            New-customer revenue {formatSGD(summary.new_customer_revenue)} · Repeat {formatSGD(summary.repeat_customer_revenue)}
          </div>

          {/* Sales chart */}
          <div className="card" style={{ marginBottom: 18 }}>
            <div className="card-title">Sales Chart ({preset === "today" ? "hourly" : "daily"})</div>
            {sales.length === 0 ? (
              <p style={{ color: "var(--color-text-muted)" }}>No sales in this period.</p>
            ) : (
              <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 160, marginTop: 12, overflowX: "auto" }}>
                {sales.map((s) => (
                  <div key={s.period} title={`${s.period}: ${formatSGD(s.revenue)} (${s.orders} orders)`}
                       style={{ flex: "1 0 14px", minWidth: 14, display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
                    <div style={{ width: "70%", height: `${(s.revenue / maxSale) * 130}px`, background: "var(--color-primary,#ea580c)", borderRadius: "3px 3px 0 0", minHeight: 2 }} />
                    <span style={{ fontSize: 9, color: "var(--color-text-muted)", whiteSpace: "nowrap", transform: "rotate(-45deg)", transformOrigin: "center" }}>{s.period.slice(5)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Top items + per-child rollup */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 16 }}>
            <div className="card">
              <div className="card-title">Top Items</div>
              {items.length === 0 ? <p style={{ color: "var(--color-text-muted)" }}>No items sold.</p> : items.map((it) => (
                <div key={it.name} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid #f1f5f9" }}>
                  <span>{it.name} <span style={{ color: "var(--color-text-muted)", fontSize: 12 }}>×{it.quantity}</span></span>
                  <strong>{formatSGD(it.revenue)}</strong>
                </div>
              ))}
            </div>
            <div className="card">
              <div className="card-title">Breakdown {source?.platform ? "by merchant" : "by child"} <span style={{ fontWeight: 400, fontSize: 12, color: "var(--color-text-muted)" }}>(click to drill in)</span></div>
              {rollup.length === 0 ? <p style={{ color: "var(--color-text-muted)" }}>No child nodes.</p> : rollup.map((r) => (
                <button key={r.node_id} onClick={() => setSource({ platform: false, nodeId: r.node_id, label: r.name })}
                        style={{ display: "flex", justifyContent: "space-between", width: "100%", background: "none", border: "none", borderBottom: "1px solid #f1f5f9", padding: "8px 0", cursor: "pointer", textAlign: "left" }}>
                  <span>{r.name} <span className="badge" style={{ fontSize: 9, background: r.sells ? "#fef3c7" : "#dbeafe", color: r.sells ? "#92400e" : "#1e40af" }}>{r.sells ? "Storefront" : "Chain"}</span></span>
                  <span><strong>{formatSGD(r.revenue)}</strong> <span style={{ color: "var(--color-text-muted)", fontSize: 12 }}>· {r.orders} ord</span> ›</span>
                </button>
              ))}
            </div>
          </div>
        </>
      )}

      {tab === "payments" && (
        <div className="card">
          <div className="card-title">Payment Methods</div>
          {payments.length === 0 ? <p style={{ color: "var(--color-text-muted)" }}>No payments in this period.</p> : payments.map((p) => (
            <div key={p.method} style={{ padding: "8px 0", borderBottom: "1px solid #f1f5f9" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <strong style={{ textTransform: "uppercase" }}>{p.method}</strong>
                <span>{formatSGD(p.amount)} · {p.count} txn · {Math.round((p.amount / payTotal) * 100)}%</span>
              </div>
              <div style={{ height: 6, background: "#f1f5f9", borderRadius: 3, marginTop: 4 }}>
                <div style={{ width: `${(p.amount / payTotal) * 100}%`, height: "100%", background: "var(--color-primary,#ea580c)", borderRadius: 3 }} />
              </div>
            </div>
          ))}
        </div>
      )}
    </MerchantSidebar>
  );
}
