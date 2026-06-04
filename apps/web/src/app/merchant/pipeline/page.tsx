"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  pipeline,
  listOpportunities,
  updateOpportunity,
  crmCustomers,
  getApiBase,
} from "@/lib/api";
import { getStaffToken, clearStaffToken, getOperatorMerchant } from "@/lib/auth";
import { formatSGD, prettyStage } from "@/lib/format";
import MerchantSidebar from "@/components/MerchantSidebar";
import NodeDirectory from "@/components/NodeDirectory";
import { useScope } from "@/lib/useScope";
import type { Pipeline, PipelineStage, Opportunity, PipelineType } from "@fbgroup/api-client";

function stageHeaderColor(s: PipelineStage): { bg: string; fg: string } {
  if (s.is_won) return { bg: "#dcfce7", fg: "#166534" };
  if (s.is_lost) return { bg: "#e5e7eb", fg: "#4b5563" };
  return { bg: "#eff6ff", fg: "#1e40af" };
}

export default function PipelinePage() {
  const router = useRouter();
  const base = getApiBase();

  const [mode, setMode] = useState<PipelineType>("sales");
  const [pipe, setPipe] = useState<Pipeline | null>(null);
  const [opps, setOpps] = useState<Opportunity[]>([]);
  const [custNames, setCustNames] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const { scope, isOperator, nodes, ready, enter } = useScope();
  const needPick = ready && isOperator && !!scope && scope.tenantId === null;

  const load = useCallback(
    async (tok: string, pipelineType: PipelineType) => {
      const mid = getOperatorMerchant()?.id;
      const [pl, op, customers] = await Promise.all([
        pipeline(base, tok, pipelineType, mid),
        listOpportunities(base, tok, pipelineType, mid),
        crmCustomers(base, tok, undefined, mid).catch(() => []),
      ]);
      setPipe(pl);
      setOpps(op);
      const map: Record<string, string> = {};
      for (const c of customers) map[c.id] = c.full_name ?? "Customer";
      setCustNames(map);
    },
    [base]
  );

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) {
      router.push("/merchant/login");
      return;
    }
    if (!ready || needPick) return;
    setLoading(true);
    load(tok, mode)
      .then(() => setLoading(false))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("401")) {
          clearStaffToken();
          router.push("/merchant/login");
        } else {
          setError(msg || "Failed to load pipeline");
          setLoading(false);
        }
      });
  }, [load, router, mode, ready, needPick]);

  // Stage keys for the active mode, in board order from the API.
  const stageKeys = pipe ? pipe.stages.map((s) => s.stage) : [];

  async function advanceStage(opp: Opportunity, stage: string) {
    const tok = getStaffToken();
    if (!tok || stage === opp.stage) return;
    setUpdatingId(opp.id);
    try {
      await updateOpportunity(base, tok, opp.id, { stage }, getOperatorMerchant()?.id);
      await load(tok, mode);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update opportunity");
    } finally {
      setUpdatingId(null);
    }
  }

  function TabButton({ value, label }: { value: PipelineType; label: string }) {
    const activeTab = mode === value;
    return (
      <button
        onClick={() => setMode(value)}
        style={{
          padding: "8px 16px",
          border: "1px solid var(--color-border, #e5e7eb)",
          borderBottom: activeTab ? "2px solid #1e40af" : "1px solid var(--color-border, #e5e7eb)",
          background: activeTab ? "#eff6ff" : "#fff",
          color: activeTab ? "#1e40af" : "#475569",
          fontWeight: 600,
          fontSize: 14,
          cursor: "pointer",
          borderRadius: "8px 8px 0 0",
        }}
      >
        {label}
      </button>
    );
  }

  if (needPick) {
    return (
      <MerchantSidebar active="pipeline">
        <NodeDirectory feature="Pipeline" nodes={nodes} currentNodeId={scope!.currentNodeId} onEnter={enter} />
      </MerchantSidebar>
    );
  }

  return (
    <MerchantSidebar active="pipeline">
      <div className="page-header">
        <h1 className="page-title">Pipeline</h1>
        <p className="page-subtitle">Opportunities by stage</p>
      </div>

      {/* Mode tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
        <TabButton value="sales" label="Sales" />
        <TabButton value="winback" label="Win-back" />
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="page-loading">
          <div className="spinner" /> Loading pipeline…
        </div>
      ) : (
        <>
          {/* Summary */}
          {pipe && (
            <div className="kpi-grid" style={{ marginBottom: 24 }}>
              <div className="kpi-card">
                <div className="kpi-label">Open Value</div>
                <div className="kpi-value">{formatSGD(pipe.open_value)}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">{mode === "winback" ? "Recovered Value" : "Won Value"}</div>
                <div className="kpi-value">{formatSGD(pipe.won_value)}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">Open Opportunities</div>
                <div className="kpi-value">{pipe.open_count.toLocaleString()}</div>
              </div>
            </div>
          )}

          {/* Kanban board — columns rendered dynamically from the API stages */}
          <div style={{ display: "flex", gap: 14, overflowX: "auto", paddingBottom: 8 }}>
            {pipe?.stages.map((stageDef) => {
              const stage = stageDef.stage;
              const colOpps = opps.filter((o) => o.stage === stage);
              const colors = stageHeaderColor(stageDef);
              const total = colOpps.reduce((s, o) => s + o.amount, 0);
              return (
                <div
                  key={stage}
                  style={{
                    minWidth: 240,
                    flex: "0 0 240px",
                    background: "var(--color-bg, #f8fafc)",
                    border: "1px solid var(--color-border, #e5e7eb)",
                    borderRadius: 10,
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  <div
                    style={{
                      background: colors.bg,
                      color: colors.fg,
                      padding: "10px 12px",
                      borderTopLeftRadius: 10,
                      borderTopRightRadius: 10,
                      fontWeight: 700,
                      fontSize: 13,
                      display: "flex",
                      justifyContent: "space-between",
                    }}
                  >
                    <span>
                      {prettyStage(stage)} ({colOpps.length})
                    </span>
                    <span>{formatSGD(total)}</span>
                  </div>
                  <div style={{ padding: 10, display: "flex", flexDirection: "column", gap: 8 }}>
                    {colOpps.length === 0 ? (
                      <div style={{ fontSize: 12, color: "var(--color-text-muted, #94a3b8)", padding: "8px 2px" }}>
                        No opportunities
                      </div>
                    ) : (
                      colOpps.map((o) => (
                        <div
                          key={o.id}
                          style={{
                            background: "#fff",
                            border: "1px solid var(--color-border, #e5e7eb)",
                            borderRadius: 8,
                            padding: 10,
                          }}
                        >
                          <div style={{ fontWeight: 600, fontSize: 14 }}>{o.name}</div>
                          <div style={{ fontSize: 13, color: "var(--color-primary, #1e40af)", fontWeight: 600 }}>
                            {formatSGD(o.amount)}
                          </div>
                          <div style={{ fontSize: 12, color: "var(--color-text-muted, #64748b)", marginBottom: 6 }}>
                            {custNames[o.customer_id] ?? "Customer"}
                          </div>
                          <select
                            value={o.stage}
                            disabled={updatingId === o.id}
                            onChange={(e) => advanceStage(o, e.target.value)}
                            style={{ width: "100%", fontSize: 12, padding: "4px 6px" }}
                          >
                            {stageKeys.map((s) => (
                              <option key={s} value={s}>
                                {prettyStage(s)}
                              </option>
                            ))}
                          </select>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </MerchantSidebar>
  );
}
