"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useParams } from "next/navigation";
import {
  campaignDetail,
  buildAudience,
  sendCampaign,
  campaignMetrics,
  getApiBase,
} from "@/lib/api";
import { getStaffToken, clearStaffToken, getOperatorMerchant } from "@/lib/auth";
import { formatSGD, formatDate } from "@/lib/format";
import MerchantSidebar from "@/components/MerchantSidebar";
import {
  type CampaignDetail,
  type CampaignMetrics,
  type CampaignType,
} from "@fbgroup/api-client";

const TYPE_LABELS: Record<CampaignType, string> = {
  whatsapp_promo: "WhatsApp Promo",
  birthday: "Birthday",
  winback: "Win-back",
  weekday_boost: "Weekday Boost",
  new_customer_return: "New Customer Return",
  vip_reward: "VIP Reward",
};

function statusColor(status: string): { bg: string; fg: string } {
  switch (status) {
    case "delivered":
      return { bg: "#dcfce7", fg: "#166534" };
    case "sent":
      return { bg: "#dbeafe", fg: "#1e40af" };
    case "failed":
      return { bg: "#fee2e2", fg: "#991b1b" };
    default:
      return { bg: "#f3f4f6", fg: "#4b5563" };
  }
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="kpi-card">
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
    </div>
  );
}

export default function CampaignDetailPage() {
  const router = useRouter();
  const params = useParams();
  const campaignId = params.id as string;
  const base = getApiBase();

  const [detail, setDetail] = useState<CampaignDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [audienceSize, setAudienceSize] = useState<number | null>(null);
  const [building, setBuilding] = useState(false);
  const [sending, setSending] = useState(false);

  const load = useCallback(
    async (tok: string) => {
      const mid = getOperatorMerchant()?.id;
      const d = await campaignDetail(base, tok, campaignId, mid);
      setDetail(d);
      // Seed the displayed audience size from existing metrics if any.
      if (d.metrics.audience > 0) setAudienceSize((prev) => prev ?? d.metrics.audience);
    },
    [base, campaignId]
  );

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) {
      router.push("/merchant/login");
      return;
    }
    load(tok)
      .then(() => setLoading(false))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "";
        if (msg.includes("401")) {
          clearStaffToken();
          router.push("/merchant/login");
        } else {
          setError(msg || "Failed to load campaign");
          setLoading(false);
        }
      });
  }, [load, router]);

  function flash(msg: string) {
    setActionMsg(msg);
    setTimeout(() => setActionMsg(null), 4000);
  }

  async function handleBuildAudience() {
    const tok = getStaffToken();
    if (!tok) return;
    setBuilding(true);
    setError(null);
    try {
      const res = await buildAudience(base, tok, campaignId, getOperatorMerchant()?.id);
      setAudienceSize(res.audience_size);
      flash(`Audience built: ${res.audience_size} recipients.`);
      await load(tok);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to build audience");
    } finally {
      setBuilding(false);
    }
  }

  async function handleSend() {
    const tok = getStaffToken();
    if (!tok) return;
    setSending(true);
    setError(null);
    try {
      const res = await sendCampaign(base, tok, campaignId, getOperatorMerchant()?.id);
      flash(`Sent to ${res.audience}: ${res.delivered} delivered, ${res.failed} failed.`);
      // Refresh detail (messages) + metrics after send.
      await load(tok);
      const m: CampaignMetrics = await campaignMetrics(
        base,
        tok,
        campaignId,
        getOperatorMerchant()?.id
      );
      setDetail((prev) => (prev ? { ...prev, metrics: m } : prev));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to send campaign");
    } finally {
      setSending(false);
    }
  }

  if (loading) {
    return (
      <MerchantSidebar active="campaigns">
        <div className="page-loading">
          <div className="spinner" /> Loading campaign…
        </div>
      </MerchantSidebar>
    );
  }

  if (!detail) {
    return (
      <MerchantSidebar active="campaigns">
        {error && <div className="alert alert-error">{error}</div>}
        <a href="/merchant/campaigns" className="btn btn-secondary btn-sm">
          ← Back to campaigns
        </a>
      </MerchantSidebar>
    );
  }

  const { campaign, metrics, messages } = detail;
  const hasAudience = audienceSize !== null && audienceSize > 0;

  return (
    <MerchantSidebar active="campaigns">
      <a
        href="/merchant/campaigns"
        style={{ fontSize: 13, color: "var(--color-text-muted)" }}
      >
        ← Back to campaigns
      </a>

      <div className="page-header" style={{ marginTop: 8 }}>
        <h1 className="page-title">{campaign.name}</h1>
        <p className="page-subtitle">
          {TYPE_LABELS[campaign.campaign_type] ?? campaign.campaign_type}
          {" · "}
          Segment: {campaign.segment_key ?? "(auto)"}
          {" · "}
          {campaign.reward_points} reward pts
          {" · "}
          {campaign.is_active ? "Active" : "Inactive"}
        </p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {actionMsg && <div className="alert alert-success">{actionMsg}</div>}

      {/* Message template */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="kpi-label" style={{ marginBottom: 6 }}>
          Message Template
        </div>
        <div style={{ fontSize: 14, whiteSpace: "pre-wrap" }}>{campaign.message_template || "—"}</div>
      </div>

      {/* Metrics cards */}
      <div className="kpi-grid" style={{ marginBottom: 20 }}>
        <MetricCard label="Audience" value={String(metrics.audience)} />
        <MetricCard label="Sent" value={String(metrics.sent)} />
        <MetricCard label="Delivered" value={String(metrics.delivered)} />
        <MetricCard label="Failed" value={String(metrics.failed)} />
        <MetricCard label="Redeemed" value={String(metrics.redeemed)} />
        <MetricCard label="Revenue" value={formatSGD(metrics.revenue_generated)} />
        <MetricCard label="Conversion" value={`${(metrics.conversion_rate * 100).toFixed(1)}%`} />
        <MetricCard label="Cost" value={formatSGD(metrics.cost)} />
        <MetricCard label="ROI" value={`${metrics.roi.toFixed(2)}x`} />
      </div>

      {/* Actions */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <button className="btn btn-secondary btn-sm" disabled={building} onClick={handleBuildAudience}>
            {building ? "Building…" : "Build audience"}
          </button>
          {audienceSize !== null && (
            <span style={{ fontSize: 14, fontWeight: 600 }}>
              Audience: {audienceSize} recipient{audienceSize === 1 ? "" : "s"}
            </span>
          )}
          <button
            className="btn btn-primary btn-sm"
            disabled={sending || !hasAudience}
            onClick={handleSend}
            title={hasAudience ? "" : "Build an audience first"}
            style={{ marginLeft: "auto" }}
          >
            {sending ? "Sending…" : "Send via WhatsApp (mock)"}
          </button>
        </div>
        {!hasAudience && (
          <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 8 }}>
            Build the audience before sending.
          </div>
        )}
      </div>

      {/* Message log */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        <div className="card-title" style={{ padding: "16px 20px 0" }}>
          Message Log
        </div>
        <div className="table-wrapper" style={{ border: "none" }}>
          <table>
            <thead>
              <tr>
                <th>To</th>
                <th>Status</th>
                <th>Attempts</th>
                <th>Provider Ref</th>
                <th>Body</th>
              </tr>
            </thead>
            <tbody>
              {messages.length === 0 ? (
                <tr>
                  <td
                    colSpan={5}
                    style={{ textAlign: "center", color: "var(--color-text-muted)", padding: 24 }}
                  >
                    No messages yet — build an audience and send.
                  </td>
                </tr>
              ) : (
                messages.map((m) => {
                  const sc = statusColor(m.status);
                  return (
                    <tr key={m.id}>
                      <td style={{ fontFamily: "monospace", fontSize: 12 }}>{m.to_address}</td>
                      <td>
                        <span className="badge" style={{ background: sc.bg, color: sc.fg }}>
                          {m.status}
                        </span>
                      </td>
                      <td>{m.attempts}</td>
                      <td style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                        {m.provider_ref ?? "—"}
                      </td>
                      <td style={{ fontSize: 13, maxWidth: 320 }}>{m.body}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
        <div style={{ padding: "8px 20px 16px", fontSize: 12, color: "var(--color-text-muted)" }}>
          Created {formatDate(campaign.created_at)}
        </div>
      </div>
    </MerchantSidebar>
  );
}
