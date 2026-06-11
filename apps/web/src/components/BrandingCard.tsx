"use client";
// Branding (Tier-1 theming) — set the brand's primary/accent colour + logo URL. Saved on the node and
// cascade-merged (enterprise → brand → outlet), injected as CSS-var overrides on the customer app.
import { useEffect, useState } from "react";
import { getNodeTheme, setNodeTheme, getApiBase } from "@/lib/api";
import { getStaffToken } from "@/lib/auth";
import type { BrandTheme } from "@fbgroup/api-client";

export default function BrandingCard({ nodeId }: { nodeId: string }) {
  const base = getApiBase();
  const [own, setOwn] = useState<BrandTheme>({});
  const [resolved, setResolved] = useState<BrandTheme>({});
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) return;
    getNodeTheme(base, tok, nodeId)
      .then((t) => { setOwn(t.own ?? {}); setResolved(t.resolved ?? {}); })
      .catch(() => {});
  }, [base, nodeId]);

  const set = (patch: Partial<BrandTheme>) => { setOwn((o) => ({ ...o, ...patch })); setSaved(false); };
  const primary = own.primary || resolved.primary || "#e23a0f";   // preview colour (own → inherited → default)
  const accent = own.accent || resolved.accent || "";

  const save = () => {
    const tok = getStaffToken();
    if (!tok) return;
    const clean: BrandTheme = {};
    if (own.primary) clean.primary = own.primary;
    if (own.accent) clean.accent = own.accent;
    if (own.logo_url) clean.logo_url = own.logo_url;
    setBusy(true);
    setNodeTheme(base, tok, nodeId, Object.keys(clean).length ? clean : null)
      .then((t) => { setOwn(t.own ?? {}); setResolved(t.resolved ?? {}); setSaved(true); })
      .catch(() => {}).finally(() => setBusy(false));
  };
  const reset = () => { setOwn({}); const tok = getStaffToken(); if (!tok) return;
    setBusy(true); setNodeTheme(base, tok, nodeId, null).then((t) => { setResolved(t.resolved ?? {}); setSaved(true); }).finally(() => setBusy(false)); };

  const swatch = (label: string, value: string, onChange: (v: string) => void) => (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span style={{ width: 110, fontSize: 13, fontWeight: 600 }}>{label}</span>
      <input type="color" value={value || "#e23a0f"} disabled={busy} onChange={(e) => onChange(e.target.value)}
        style={{ width: 40, height: 32, padding: 0, border: "1px solid var(--color-border,#e5e7eb)", borderRadius: 6, background: "none" }} />
      <input type="text" value={value} placeholder="inherit" disabled={busy} onChange={(e) => onChange(e.target.value)}
        style={{ width: 110, fontSize: 13, padding: "6px 8px", border: "1px solid var(--color-border,#e5e7eb)", borderRadius: 6 }} />
    </div>
  );

  return (
    <div className="card" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12, maxWidth: 480 }}>
      <div style={{ fontWeight: 800 }}>Branding</div>
      {swatch("Primary colour", own.primary || "", (v) => set({ primary: v }))}
      {swatch("Accent (optional)", own.accent || "", (v) => set({ accent: v }))}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ width: 110, fontSize: 13, fontWeight: 600 }}>Logo URL</span>
        <input type="text" value={own.logo_url || ""} placeholder="https://… (hosted image)" disabled={busy}
          onChange={(e) => set({ logo_url: e.target.value })}
          style={{ flex: 1, fontSize: 13, padding: "6px 8px", border: "1px solid var(--color-border,#e5e7eb)", borderRadius: 6 }} />
      </div>
      {/* Live preview — a header + button rendered in the chosen colour (what the diner's app will use). */}
      <div style={{ borderRadius: 10, overflow: "hidden", border: "1px solid var(--color-border,#e5e7eb)" }}>
        <div style={{ padding: "12px 14px", color: "#fff", fontWeight: 800, background: primary }}>
          {own.logo_url ? <img src={own.logo_url} alt="logo" style={{ height: 22, verticalAlign: "middle" }} /> : "Your storefront"}
        </div>
        <div style={{ padding: 12, display: "flex", gap: 8, alignItems: "center" }}>
          <button type="button" style={{ background: primary, color: "#fff", border: "none", borderRadius: 8, padding: "8px 14px", fontWeight: 700 }}>Add to cart</button>
          {accent && <span style={{ color: accent, fontWeight: 700 }}>● accent</span>}
          <span style={{ marginLeft: "auto", fontSize: 11, color: "var(--color-text-muted)" }}>preview</span>
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <button type="button" className="btn btn-primary" disabled={busy} onClick={save}>Save branding</button>
        <button type="button" disabled={busy} onClick={reset} style={{ background: "none", border: "none", color: "var(--color-text-muted)", fontSize: 12, fontWeight: 700, cursor: busy ? "default" : "pointer" }}>Reset to inherit</button>
        {saved && <span style={{ color: "var(--color-success,#16a34a)", fontSize: 12, fontWeight: 700 }}>Saved ✓</span>}
      </div>
      <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>Cascades to everything below this node (enterprise → brand → outlet). Empty fields inherit from the parent.</span>
    </div>
  );
}
