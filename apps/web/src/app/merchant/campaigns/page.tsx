"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { listCampaigns, createCampaign, getApiBase } from "@/lib/api";
import { getStaffToken, clearStaffToken, getOperatorMerchant } from "@/lib/auth";
import { formatSGD } from "@/lib/format";
import MerchantSidebar from "@/components/MerchantSidebar";
import PointMultipliers from "@/components/PointMultipliers";
import {
  CAMPAIGN_TYPES,
  type CampaignListItem,
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

function TypeBadge({ type }: { type: CampaignType }) {
  return (
    <span
      className="badge"
      style={{ background: "#eef2ff", color: "#4338ca" }}
    >
      {TYPE_LABELS[type] ?? type}
    </span>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ minWidth: 70 }}>
      <div style={{ fontSize: 11, color: "var(--color-text-muted)", textTransform: "uppercase" }}>
        {label}
      </div>
      <div style={{ fontWeight: 600, fontSize: 14 }}>{value}</div>
    </div>
  );
}

export default function CampaignsPage() {
  const router = useRouter();
  const base = getApiBase();

  const [campaigns, setCampaigns] = useState<CampaignListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New campaign form
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState<CampaignType>("whatsapp_promo");
  const [segment, setSegment] = useState("");
  const [template, setTemplate] = useState("Hi {name}, enjoy a special offer this week!");
  const [rewardPoints, setRewardPoints] = useState("");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(
    async (tok: string) => {
      const mid = getOperatorMerchant()?.id;
      const list = await listCampaigns(base, tok, mid);
      setCampaigns(list);
    },
    [base]
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
          setError(msg || "Failed to load campaigns");
          setLoading(false);
        }
      });
  }, [load, router]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    const tok = getStaffToken();
    if (!tok) return;
    setCreating(true);
    setFormError(null);
    try {
      await createCampaign(
        base,
        tok,
        {
          name: name.trim(),
          campaign_type: type,
          segment_key: segment.trim() || undefined,
          message_template: template,
          reward_points: parseInt(rewardPoints, 10) || 0,
        },
        getOperatorMerchant()?.id
      );
      setName("");
      setSegment("");
      setTemplate("Hi {name}, enjoy a special offer this week!");
      setRewardPoints("");
      setShowForm(false);
      await load(tok);
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to create campaign");
    } finally {
      setCreating(false);
    }
  }

  return (
    <MerchantSidebar active="campaigns">
      <div
        className="page-header"
        style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}
      >
        <div>
          <h1 className="page-title">Campaigns</h1>
          <p className="page-subtitle">Retention &amp; promotional messaging</p>
        </div>
        <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "New campaign"}
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <PointMultipliers />

      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <div className="card-title" style={{ marginBottom: 12 }}>
            New Campaign
          </div>
          {formError && <div className="alert alert-error">{formError}</div>}
          <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <input
                type="text"
                placeholder="Campaign name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                style={{ flex: 2, minWidth: 200 }}
              />
              <select
                value={type}
                onChange={(e) => setType(e.target.value as CampaignType)}
                style={{ flex: 1, minWidth: 160 }}
              >
                {CAMPAIGN_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {TYPE_LABELS[t]}
                  </option>
                ))}
              </select>
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <input
                type="text"
                placeholder="Segment override (optional)"
                value={segment}
                onChange={(e) => setSegment(e.target.value)}
                style={{ flex: 1, minWidth: 180 }}
              />
              <input
                type="number"
                min="0"
                placeholder="Reward coins"
                value={rewardPoints}
                onChange={(e) => setRewardPoints(e.target.value)}
                style={{ flex: 1, minWidth: 140 }}
              />
            </div>
            <textarea
              placeholder="Message template"
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              rows={3}
            />
            <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
              Tip: use <code>{"{name}"}</code> to insert the customer&apos;s first name. Audience
              auto-targets a segment based on type unless you set an override.
            </div>
            <button type="submit" className="btn btn-primary btn-sm" disabled={creating}>
              {creating ? "Creating…" : "Create campaign"}
            </button>
          </form>
        </div>
      )}

      {loading ? (
        <div className="page-loading">
          <div className="spinner" /> Loading campaigns…
        </div>
      ) : campaigns.length === 0 ? (
        <p style={{ color: "var(--color-text-muted)" }}>No campaigns yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {campaigns.map((c) => (
            <div
              key={c.id}
              className="card clickable"
              style={{ cursor: "pointer" }}
              onClick={() => router.push(`/merchant/campaigns/${c.id}`)}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 12,
                  gap: 10,
                  flexWrap: "wrap",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span style={{ fontWeight: 700, fontSize: 15 }}>{c.name}</span>
                  <TypeBadge type={c.campaign_type} />
                  {!c.is_active && (
                    <span className="badge" style={{ background: "#e5e7eb", color: "#4b5563" }}>
                      Inactive
                    </span>
                  )}
                </div>
                {c.segment_key && (
                  <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                    Segment: {c.segment_key}
                  </span>
                )}
              </div>
              <div
                style={{
                  display: "flex",
                  gap: 18,
                  flexWrap: "wrap",
                  borderTop: "1px solid var(--color-border, #e5e7eb)",
                  paddingTop: 10,
                }}
              >
                <Metric label="Sent" value={String(c.metrics.sent)} />
                <Metric label="Delivered" value={String(c.metrics.delivered)} />
                <Metric label="Redeemed" value={String(c.metrics.redeemed)} />
                <Metric label="Revenue" value={formatSGD(c.metrics.revenue_generated)} />
                <Metric
                  label="Conversion"
                  value={`${(c.metrics.conversion_rate * 100).toFixed(1)}%`}
                />
                <Metric label="ROI" value={`${c.metrics.roi.toFixed(2)}x`} />
              </div>
            </div>
          ))}
        </div>
      )}
    </MerchantSidebar>
  );
}
