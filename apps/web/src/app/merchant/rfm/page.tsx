"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { rfm, launchWinback, getApiBase } from "@/lib/api";
import { getStaffToken, clearStaffToken, getOperatorMerchant } from "@/lib/auth";
import { formatSGD } from "@/lib/format";
import MerchantSidebar from "@/components/MerchantSidebar";
import NodeDirectory from "@/components/NodeDirectory";
import { useScope } from "@/lib/useScope";
import type { RfmReport, WinbackResult } from "@fbgroup/api-client";

const WINBACK_SEGMENTS = ["At Risk", "Hibernating", "Can't Lose Them"];

function segmentColor(segment: string): { bg: string; fg: string } {
  const s = segment.toLowerCase();
  if (s.includes("champion")) return { bg: "#dcfce7", fg: "#166534" };
  if (s.includes("loyal")) return { bg: "#dbeafe", fg: "#1e40af" };
  if (s.includes("potential") || s.includes("promising")) return { bg: "#eef2ff", fg: "#4338ca" };
  if (s.includes("new")) return { bg: "#cffafe", fg: "#155e75" };
  if (s.includes("attention") || s.includes("about")) return { bg: "#fef9c3", fg: "#854d0e" };
  if (s.includes("risk")) return { bg: "#ffedd5", fg: "#9a3412" };
  if (s.includes("hibernat") || s.includes("lost") || s.includes("lose")) return { bg: "#fee2e2", fg: "#991b1b" };
  return { bg: "#f3f4f6", fg: "#4b5563" };
}

function ScorePill({ label, score }: { label: string; score: number }) {
  // 1 (low) → 5 (high): green for high, red for low
  const hue = (score - 1) * 30; // 0=red .. 120=green
  return (
    <span
      title={`${label}=${score}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 22,
        height: 22,
        borderRadius: 5,
        fontSize: 12,
        fontWeight: 700,
        color: "#fff",
        background: `hsl(${hue}, 65%, 42%)`,
        marginRight: 3,
      }}
    >
      {score}
    </span>
  );
}

export default function RfmPage() {
  const router = useRouter();
  const base = getApiBase();

  const [report, setReport] = useState<RfmReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { scope, isOperator, nodes, ready, enter } = useScope();
  const needPick = ready && isOperator && !!scope && scope.tenantId === null;

  // Win-back launcher
  const [withCampaign, setWithCampaign] = useState(true);
  const [launching, setLaunching] = useState(false);
  const [winbackResult, setWinbackResult] = useState<WinbackResult | null>(null);

  const load = useCallback(
    async (tok: string) => {
      const r = await rfm(base, tok, getOperatorMerchant()?.id);
      setReport(r);
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
    load(tok)
      .then(() => setLoading(false))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("401")) {
          clearStaffToken();
          router.push("/merchant/login");
        } else {
          setError(msg || "Failed to load RFM report");
          setLoading(false);
        }
      });
  }, [load, router, ready, needPick]);

  async function handleLaunchWinback() {
    const tok = getStaffToken();
    if (!tok) return;
    setLaunching(true);
    setError(null);
    setWinbackResult(null);
    try {
      const res = await launchWinback(
        base,
        tok,
        { rfm_segments: WINBACK_SEGMENTS, create_campaign: withCampaign },
        getOperatorMerchant()?.id
      );
      setWinbackResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to launch win-back");
    } finally {
      setLaunching(false);
    }
  }

  const maxDist =
    report && Object.values(report.distribution).length > 0
      ? Math.max(...Object.values(report.distribution))
      : 1;

  if (needPick) {
    return (
      <MerchantSidebar active="rfm">
        <NodeDirectory feature="RFM Analytics" nodes={nodes} currentNodeId={scope!.currentNodeId} onEnter={enter} />
      </MerchantSidebar>
    );
  }

  return (
    <MerchantSidebar active="rfm">
      <div className="page-header">
        <h1 className="page-title">RFM Analytics</h1>
        <p className="page-subtitle">
          Recency / Frequency / Monetary segmentation
          {report ? ` · ${report.count} customers` : ""}
        </p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="page-loading">
          <div className="spinner" /> Loading RFM…
        </div>
      ) : report ? (
        <>
          {/* Win-back launcher */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-title" style={{ marginBottom: 10 }}>
              Win-back Campaign
            </div>
            <p style={{ fontSize: 13, color: "var(--color-text-muted)", marginTop: 0, marginBottom: 12 }}>
              Target lapsing customers in <strong>{WINBACK_SEGMENTS.join(", ")}</strong> — creates win-back
              pipeline opportunities and optionally sends a WhatsApp message.
            </p>
            <div style={{ display: "flex", gap: 14, alignItems: "center", flexWrap: "wrap" }}>
              <label style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 14 }}>
                <input
                  type="checkbox"
                  checked={withCampaign}
                  onChange={(e) => setWithCampaign(e.target.checked)}
                />
                Also send WhatsApp
              </label>
              <button className="btn btn-primary btn-sm" disabled={launching} onClick={handleLaunchWinback}>
                {launching ? "Launching…" : "Launch win-back"}
              </button>
            </div>
            {winbackResult && (
              <div className="alert alert-success" style={{ marginTop: 12, marginBottom: 0 }}>
                Targeted {winbackResult.targets} customer{winbackResult.targets === 1 ? "" : "s"} ·{" "}
                {winbackResult.opportunities_created} opportunit
                {winbackResult.opportunities_created === 1 ? "y" : "ies"} created
                {winbackResult.campaign_id
                  ? ` · ${winbackResult.campaign_delivered} message${winbackResult.campaign_delivered === 1 ? "" : "s"} delivered`
                  : ""}
                {". "}
                <a href="/merchant/pipeline">View win-back pipeline →</a>
              </div>
            )}
          </div>

          {/* Distribution */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div className="card-title" style={{ marginBottom: 14 }}>
              Segment Distribution
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {Object.entries(report.distribution)
                .sort((a, b) => b[1] - a[1])
                .map(([seg, count]) => {
                  const c = segmentColor(seg);
                  return (
                    <div key={seg} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span
                        className="badge"
                        style={{ background: c.bg, color: c.fg, minWidth: 120, justifyContent: "center" }}
                      >
                        {seg}
                      </span>
                      <div
                        style={{
                          flex: 1,
                          height: 18,
                          background: "#f3f4f6",
                          borderRadius: 4,
                          overflow: "hidden",
                        }}
                      >
                        <div
                          style={{
                            width: `${Math.max(2, (count / maxDist) * 100)}%`,
                            height: "100%",
                            background: c.fg,
                            opacity: 0.85,
                          }}
                        />
                      </div>
                      <span style={{ fontWeight: 600, minWidth: 36, textAlign: "right" }}>{count}</span>
                    </div>
                  );
                })}
            </div>
          </div>

          {/* Customers table */}
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div className="card-title" style={{ padding: "16px 20px 0" }}>
              Customers
            </div>
            <div className="table-wrapper" style={{ border: "none" }}>
              <table>
                <thead>
                  <tr>
                    <th>Customer</th>
                    <th>R / F / M</th>
                    <th>Code</th>
                    <th>Monetary</th>
                    <th>Frequency</th>
                    <th>Recency</th>
                    <th>Segment</th>
                  </tr>
                </thead>
                <tbody>
                  {report.customers.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ textAlign: "center", color: "var(--color-text-muted)", padding: 24 }}>
                        No customers
                      </td>
                    </tr>
                  ) : (
                    report.customers.map((c) => {
                      const sc = segmentColor(c.segment);
                      return (
                        <tr key={c.customer_id}>
                          <td style={{ fontWeight: 600 }}>{c.name}</td>
                          <td style={{ whiteSpace: "nowrap" }}>
                            <ScorePill label="R" score={c.r} />
                            <ScorePill label="F" score={c.f} />
                            <ScorePill label="M" score={c.m} />
                          </td>
                          <td style={{ fontFamily: "monospace" }}>{c.rfm}</td>
                          <td>{formatSGD(c.monetary)}</td>
                          <td>{c.frequency}</td>
                          <td>{c.recency_days}d</td>
                          <td>
                            <span className="badge" style={{ background: sc.bg, color: sc.fg }}>
                              {c.segment}
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}
    </MerchantSidebar>
  );
}
