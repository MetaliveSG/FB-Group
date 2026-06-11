"use client";
// Per-storefront Kitchen Display (KDS) station — a private link the kitchen tablet opens (no login).
// Issue / copy / open / rotate / revoke the station token. Lives in the merchant Ordering setup hub.
import { useEffect, useState } from "react";
import { getNodeKdsStation, issueNodeKdsStation, revokeNodeKdsStation, getApiBase } from "@/lib/api";
import { getStaffToken } from "@/lib/auth";
import type { KdsStation } from "@fbgroup/api-client";

export default function KdsStationCard({ nodeId }: { nodeId: string }) {
  const base = getApiBase();
  const [kds, setKds] = useState<KdsStation | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) return;
    getNodeKdsStation(base, tok, nodeId).then(setKds).catch(() => setKds(null));
  }, [base, nodeId]);

  const issue = () => {
    const tok = getStaffToken();
    if (!tok) return;
    setBusy(true);
    issueNodeKdsStation(base, tok, nodeId).then(setKds).catch(() => {}).finally(() => setBusy(false));
  };
  const revoke = () => {
    const tok = getStaffToken();
    if (!tok) return;
    setBusy(true);
    revokeNodeKdsStation(base, tok, nodeId)
      .then(() => setKds((k) => (k ? { ...k, token: null, is_active: false } : k)))
      .catch(() => {}).finally(() => setBusy(false));
  };
  const link = (t: string) => `${typeof window !== "undefined" ? window.location.origin : ""}/kds?station=${encodeURIComponent(t)}`;

  if (!kds) return null;

  return (
    <div className="card" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ fontWeight: 800 }}>Kitchen display (KDS)</div>
      {kds.is_active && kds.token ? (
        <>
          <div style={{ display: "flex", gap: 6 }}>
            <input readOnly value={link(kds.token)} onFocus={(e) => e.currentTarget.select()}
              style={{ flex: 1, fontSize: 12, padding: "8px 10px", border: "1px solid var(--color-border,#e5e7eb)", borderRadius: 6, color: "var(--color-text)", background: "var(--color-surface-alt,#f8fafc)" }} />
            <button type="button" className="btn btn-secondary" disabled={busy}
              onClick={() => navigator.clipboard?.writeText(link(kds.token!)).catch(() => {})}>Copy</button>
          </div>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <button type="button" className="btn btn-secondary" disabled={busy}
              onClick={() => window.open(link(kds.token!), "_blank", "noopener,noreferrer")}>Open kitchen screen</button>
            <button type="button" disabled={busy} onClick={issue}
              style={{ background: "none", border: "none", color: "var(--color-primary,#dc2626)", fontSize: 12, fontWeight: 700, cursor: busy ? "default" : "pointer" }}>Rotate token</button>
            <button type="button" disabled={busy} onClick={revoke}
              style={{ background: "none", border: "none", color: "#b91c1c", fontSize: 12, fontWeight: 700, cursor: busy ? "default" : "pointer", marginLeft: "auto" }}>Revoke</button>
          </div>
          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Open this link once on the kitchen tablet — it stays signed in (no login). Rotate or revoke if a device is lost.</span>
        </>
      ) : (
        <>
          <button type="button" className="btn btn-primary" style={{ alignSelf: "flex-start", fontWeight: 700 }} disabled={busy} onClick={issue}>
            Set up kitchen screen
          </button>
          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Issues a private link for this storefront’s kitchen tablet (no login). Needs Table QR on.</span>
        </>
      )}
    </div>
  );
}
