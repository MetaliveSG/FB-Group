"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  crmCustomers,
  crmSegments,
  reportSummary,
  reportSales,
  reportTopItems,
  bulkTag,
  bulkOwner,
  bulkTask,
} from "@/lib/api";
import { getStaffToken, clearStaffToken, getStaffUser, getOperatorMerchant } from "@/lib/auth";
import { getApiBase } from "@/lib/api";
import { formatSGD, churnColor } from "@/lib/format";
import LineChart from "@/components/LineChart";
import BarChart from "@/components/BarChart";
import MerchantSidebar from "@/components/MerchantSidebar";
import NodeDirectory from "@/components/NodeDirectory";
import { useScope } from "@/lib/useScope";
import type {
  CustomerSummary,
  SegmentSummary,
  ReportSummary,
  SalesPeriod,
  TopItem,
} from "@fbgroup/api-client";

function SidebarLayout({ children }: { children: React.ReactNode }) {
  return <MerchantSidebar active="crm">{children}</MerchantSidebar>;
}

export default function CrmPage() {
  const router = useRouter();
  const base = getApiBase();

  // Tree-scoped guard: an operator sitting ABOVE a tenant boundary (Platform scope, no merchant
  // entered) must pick a merchant — CRM is tenant-wide, so loading it with a null merchant_id would 500.
  const { scope, isOperator, nodes, ready, enter } = useScope();
  const needPick = ready && isOperator && !!scope && scope.tenantId === null;

  const [token, setToken] = useState<string | null>(null);
  const [customers, setCustomers] = useState<CustomerSummary[]>([]);
  const [segments, setSegments] = useState<SegmentSummary | null>(null);
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [sales, setSales] = useState<SalesPeriod[]>([]);
  const [topItems, setTopItems] = useState<TopItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [segmentFilter, setSegmentFilter] = useState("");

  // Bulk selection
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [bulkTagInput, setBulkTagInput] = useState("");
  const [bulkTaskInput, setBulkTaskInput] = useState("");
  const [bulkBusy, setBulkBusy] = useState(false);
  const [bulkMsg, setBulkMsg] = useState<string | null>(null);

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) {
      router.push("/merchant/login");
      return;
    }
    setToken(tok);
  }, [router]);

  const loadData = useCallback(
    async (tok: string, seg?: string, srch?: string) => {
      setLoading(true);
      setError(null);
      const mid = getOperatorMerchant()?.id;
      try {
        const [custData, segData, sumData, salesData, itemsData] = await Promise.all([
          crmCustomers(base, tok, { segment: seg || undefined, search: srch || undefined }, mid),
          crmSegments(base, tok, mid),
          reportSummary(base, tok, mid),
          reportSales(base, tok, { granularity: "day", days: 30 }, mid),
          reportTopItems(base, tok, mid),
        ]);
        setCustomers(custData);
        setSegments(segData);
        setSummary(sumData);
        setSales(salesData);
        setTopItems(itemsData);
        setSelected(new Set());
      } catch (err: unknown) {
        if (err instanceof Error && err.message.includes("401")) {
          clearStaffToken();
          router.push("/merchant/login");
        } else {
          setError(err instanceof Error ? err.message : "Failed to load data");
        }
      } finally {
        setLoading(false);
      }
    },
    [base, router]
  );

  useEffect(() => {
    // Wait for the scope to resolve; don't fetch while we still owe the user a merchant pick.
    if (token && ready && !needPick) {
      loadData(token, segmentFilter, search);
    }
  }, [token, loadData, segmentFilter, search, ready, needPick]);

  function toggleOne(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((prev) =>
      prev.size === customers.length ? new Set() : new Set(customers.map((c) => c.id))
    );
  }

  function flashBulk(msg: string) {
    setBulkMsg(msg);
    setTimeout(() => setBulkMsg(null), 3000);
  }

  async function runBulk(action: () => Promise<{ affected: number }>, label: string) {
    if (!token || selected.size === 0) return;
    setBulkBusy(true);
    try {
      const res = await action();
      flashBulk(`${label} — ${res.affected} customer${res.affected === 1 ? "" : "s"} affected.`);
      await loadData(token, segmentFilter, search);
    } catch (err: unknown) {
      flashBulk(err instanceof Error ? err.message : "Bulk action failed");
    } finally {
      setBulkBusy(false);
    }
  }

  function bulkAddTag() {
    const tag = bulkTagInput.trim();
    if (!tag) return;
    const mid = getOperatorMerchant()?.id;
    runBulk(
      () => bulkTag(base, token!, { tag, customer_ids: Array.from(selected) }, mid),
      `Tagged "${tag}"`
    ).then(() => setBulkTagInput(""));
  }

  function bulkAssignToMe() {
    const me = getStaffUser();
    if (!me) {
      flashBulk("Cannot determine your staff id.");
      return;
    }
    const mid = getOperatorMerchant()?.id;
    runBulk(
      () => bulkOwner(base, token!, { owner_user_id: me.id, customer_ids: Array.from(selected) }, mid),
      "Assigned to me"
    );
  }

  function bulkCreateTask() {
    const title = bulkTaskInput.trim();
    if (!title) return;
    const mid = getOperatorMerchant()?.id;
    runBulk(
      () => bulkTask(base, token!, { title, customer_ids: Array.from(selected) }, mid),
      `Created task "${title}"`
    ).then(() => setBulkTaskInput(""));
  }

  const SEGMENT_LABELS: Record<string, string> = {
    total: "Total",
    vip: "VIP",
    frequent: "Frequent",
    high_spender: "High Spender",
    inactive: "Inactive",
    new: "New",
    low_frequency: "Low Freq.",
    birthday_month: "Birthday",
  };

  const salesChartData = sales.map((p) => ({
    label: p.period,
    value: p.revenue,
  }));

  const topItemsData = topItems.slice(0, 10).map((item) => ({
    label: item.name,
    value: item.revenue,
  }));

  if (needPick) {
    return (
      <SidebarLayout>
        <NodeDirectory
          feature="CRM & Analytics"
          nodes={nodes}
          currentNodeId={scope!.currentNodeId}
          onEnter={enter}
        />
      </SidebarLayout>
    );
  }

  if (loading && !customers.length) {
    return (
      <SidebarLayout>
        <div className="page-loading">
          <div className="spinner" /> Loading dashboard…
        </div>
      </SidebarLayout>
    );
  }

  return (
    <SidebarLayout>
      <div className="page-header">
        <h1 className="page-title">CRM &amp; Analytics</h1>
        <p className="page-subtitle">Makan Express — Customer insights &amp; sales overview</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Segment chips */}
      {segments && (
        <div className="segments-row">
          {Object.entries(SEGMENT_LABELS).map(([key, label]) => (
            <div
              key={key}
              className="chip"
              style={{
                cursor: "pointer",
                borderColor:
                  segmentFilter === (key === "total" ? "" : key)
                    ? "var(--color-primary)"
                    : undefined,
                background:
                  segmentFilter === (key === "total" ? "" : key) ? "#eff6ff" : undefined,
              }}
              onClick={() => setSegmentFilter(key === "total" ? "" : key)}
            >
              <span className="chip-number">{segments[key] ?? 0}</span>
              <span>{label}</span>
            </div>
          ))}
        </div>
      )}

      {/* KPIs */}
      {summary && (
        <div className="kpi-grid">
          <div className="kpi-card">
            <div className="kpi-label">Total Revenue</div>
            <div className="kpi-value">{formatSGD(summary.revenue)}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Orders</div>
            <div className="kpi-value">{summary.orders.toLocaleString()}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Unique Customers</div>
            <div className="kpi-value">{summary.unique_customers.toLocaleString()}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Avg. Order Value</div>
            <div className="kpi-value">{formatSGD(summary.avg_order_value)}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">New Cust. Revenue</div>
            <div className="kpi-value">{formatSGD(summary.new_customer_revenue)}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Repeat Revenue</div>
            <div className="kpi-value">{formatSGD(summary.repeat_customer_revenue)}</div>
          </div>
        </div>
      )}

      {/* Charts row */}
      <div className="grid-2" style={{ marginBottom: 28 }}>
        <div className="chart-container">
          <div className="chart-title">Revenue — Last 30 Days</div>
          <LineChart
            data={salesChartData}
            height={180}
            color="#1b6ca8"
            showDots={salesChartData.length <= 31}
          />
        </div>
        <div className="chart-container">
          <div className="chart-title">Top Items by Revenue</div>
          <BarChart data={topItemsData} height={180} color="#0f4c75" horizontal />
        </div>
      </div>

      {/* Customer table */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div style={{ padding: "16px 20px" }}>
          <div className="filter-row">
            <input
              type="text"
              placeholder="Search name, email, phone…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ maxWidth: 280 }}
            />
            <select
              value={segmentFilter}
              onChange={(e) => setSegmentFilter(e.target.value)}
              style={{ maxWidth: 180 }}
            >
              <option value="">All segments</option>
              {Object.entries(SEGMENT_LABELS)
                .filter(([k]) => k !== "total")
                .map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
            </select>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)", marginLeft: "auto" }}>
              {customers.length} customer{customers.length !== 1 ? "s" : ""}
            </span>
          </div>

          {bulkMsg && (
            <div className="alert alert-success" style={{ marginTop: 12, marginBottom: 0 }}>
              {bulkMsg}
            </div>
          )}

          {selected.size > 0 && (
            <div
              style={{
                marginTop: 12,
                padding: "10px 12px",
                background: "#eff6ff",
                border: "1px solid #bfdbfe",
                borderRadius: 8,
                display: "flex",
                flexWrap: "wrap",
                gap: 10,
                alignItems: "center",
              }}
            >
              <strong style={{ fontSize: 13 }}>{selected.size} selected</strong>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <input
                  type="text"
                  placeholder="Tag…"
                  value={bulkTagInput}
                  onChange={(e) => setBulkTagInput(e.target.value)}
                  style={{ width: 110, padding: "5px 8px" }}
                />
                <button className="btn btn-secondary btn-sm" disabled={bulkBusy} onClick={bulkAddTag}>
                  Add tag
                </button>
              </div>
              <button className="btn btn-secondary btn-sm" disabled={bulkBusy} onClick={bulkAssignToMe}>
                Assign to me
              </button>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <input
                  type="text"
                  placeholder="Task title…"
                  value={bulkTaskInput}
                  onChange={(e) => setBulkTaskInput(e.target.value)}
                  style={{ width: 130, padding: "5px 8px" }}
                />
                <button className="btn btn-secondary btn-sm" disabled={bulkBusy} onClick={bulkCreateTask}>
                  Create task
                </button>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                style={{ marginLeft: "auto" }}
                onClick={() => setSelected(new Set())}
              >
                Clear
              </button>
            </div>
          )}
        </div>

        <div className="table-wrapper" style={{ borderRadius: 0, border: "none" }}>
          <table>
            <thead>
              <tr>
                <th style={{ width: 36 }}>
                  <input
                    type="checkbox"
                    aria-label="Select all"
                    checked={customers.length > 0 && selected.size === customers.length}
                    onChange={toggleAll}
                  />
                </th>
                <th>Name</th>
                <th>Tier</th>
                <th>Lifecycle</th>
                <th>Total Spend</th>
                <th>Visits</th>
                <th>Coins</th>
                <th>Churn</th>
                <th>Owner</th>
                <th>Tasks</th>
                <th>Segments</th>
              </tr>
            </thead>
            <tbody>
              {customers.length === 0 ? (
                <tr>
                  <td colSpan={11} style={{ textAlign: "center", color: "var(--color-text-muted)", padding: 24 }}>
                    No customers found
                  </td>
                </tr>
              ) : (
                customers.map((c) => (
                  <tr
                    key={c.id}
                    className="clickable"
                    onClick={() => router.push(`/merchant/crm/${c.id}`)}
                  >
                    <td onClick={(e) => e.stopPropagation()} style={{ width: 36 }}>
                      <input
                        type="checkbox"
                        aria-label={`Select ${c.full_name ?? c.id}`}
                        checked={selected.has(c.id)}
                        onChange={() => toggleOne(c.id)}
                      />
                    </td>
                    <td>
                      <div style={{ fontWeight: 600 }}>{c.full_name ?? "—"}</div>
                      <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                        {c.email ?? c.phone ?? "—"}
                      </div>
                    </td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          background:
                            c.tier === "gold"
                              ? "#fef3c7"
                              : c.tier === "silver"
                              ? "#f3f4f6"
                              : "#fde8d8",
                          color:
                            c.tier === "gold"
                              ? "#92400e"
                              : c.tier === "silver"
                              ? "#374151"
                              : "#9a3412",
                        }}
                      >
                        {c.tier.charAt(0).toUpperCase() + c.tier.slice(1)}
                      </span>
                    </td>
                    <td style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                      {c.lifecycle_stage.replace(/_/g, " ")}
                    </td>
                    <td style={{ fontWeight: 600 }}>{formatSGD(c.total_spend)}</td>
                    <td>{c.visit_count}</td>
                    <td>{c.points_balance.toLocaleString()}</td>
                    <td>
                      <span
                        className="badge"
                        style={{
                          background: churnColor(c.churn_label) + "22",
                          color: churnColor(c.churn_label),
                        }}
                      >
                        {c.churn_label}
                      </span>
                    </td>
                    <td style={{ fontSize: 13 }}>
                      {c.owner_name ? (
                        c.owner_name
                      ) : (
                        <span style={{ color: "var(--color-text-muted)" }}>Unassigned</span>
                      )}
                    </td>
                    <td>
                      {c.open_tasks > 0 ? (
                        <span
                          className="badge"
                          style={{ background: "#fef3c7", color: "#92400e" }}
                        >
                          {c.open_tasks} task{c.open_tasks !== 1 ? "s" : ""}
                        </span>
                      ) : (
                        <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>—</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        {c.segments.slice(0, 3).map((seg) => (
                          <span key={seg} className="badge" style={{ background: "#e0e7ff", color: "#3730a3", fontSize: 11 }}>
                            {seg}
                          </span>
                        ))}
                        {c.segments.length > 3 && (
                          <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
                            +{c.segments.length - 3}
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </SidebarLayout>
  );
}
