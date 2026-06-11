"use client";
// Branding (Tier-1 theming) — set the brand's primary/accent colour + logo URL. Saved on the node and
// cascade-merged (enterprise → brand → outlet), injected as CSS-var overrides on the customer app.
import { useEffect, useRef, useState } from "react";
import { getNodeTheme, setNodeTheme, getApiBase } from "@/lib/api";
import { getStaffToken } from "@/lib/auth";
import type { BrandTheme } from "@fbgroup/api-client";

// A small brand-friendly palette for one-tap picking (custom colour still available via the input).
const PRESETS = [
  "#e23a0f", "#cc0001", "#d4380d", "#fa8c16", "#faad14", "#ffcc00",
  "#16335b", "#1d4ed8", "#0ea5e9", "#0e7490", "#15803d", "#16a34a",
  "#7c3aed", "#db2777", "#be123c", "#000000", "#475569", "#ffffff",
];

// A controlled colour field: a swatch button toggles a popover (presets + custom input). The popover
// HIDES on a preset pick and on any outside click — unlike a bare <input type="color"> whose OS panel
// stays open. The hex text input stays for precise/paste entry.
function ColorField({
  label, value, placeholder, disabled, onChange,
}: {
  label: string; value: string; placeholder: string; disabled?: boolean; onChange: (v: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, [open]);

  const swatchColor = value || "#ffffff";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <span style={{ width: 110, fontSize: 13, fontWeight: 600 }}>{label}</span>
      <div ref={ref} style={{ position: "relative" }}>
        <button
          type="button" disabled={disabled} aria-label={`${label} — pick colour`}
          onClick={() => setOpen((o) => !o)}
          style={{ width: 40, height: 32, padding: 0, borderRadius: 6, cursor: disabled ? "default" : "pointer",
            border: "1px solid var(--color-border,#e5e7eb)", background: swatchColor }}
        />
        {open && (
          <div style={{ position: "absolute", top: 38, left: 0, zIndex: 20, background: "#fff", padding: 10,
            borderRadius: 10, border: "1px solid var(--color-border,#e5e7eb)", boxShadow: "0 10px 30px rgba(0,0,0,0.18)", width: 184 }}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 6 }}>
              {PRESETS.map((c) => (
                <button key={c} type="button" aria-label={c}
                  onClick={() => { onChange(c); setOpen(false); }}
                  style={{ width: 22, height: 22, borderRadius: 5, cursor: "pointer", background: c,
                    border: value.toLowerCase() === c.toLowerCase() ? "2px solid var(--color-text,#111)" : "1px solid rgba(0,0,0,0.12)" }} />
              ))}
            </div>
            <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, fontSize: 12, fontWeight: 600 }}>
              Custom
              <input type="color" value={value || "#e23a0f"} onChange={(e) => onChange(e.target.value)}
                style={{ width: 34, height: 26, padding: 0, border: "1px solid var(--color-border,#e5e7eb)", borderRadius: 5, background: "none", cursor: "pointer" }} />
            </label>
          </div>
        )}
      </div>
      <input type="text" value={value} placeholder={placeholder} disabled={disabled} onChange={(e) => onChange(e.target.value)}
        style={{ width: 110, fontSize: 13, padding: "6px 8px", border: "1px solid var(--color-border,#e5e7eb)", borderRadius: 6 }} />
    </div>
  );
}

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

  return (
    <div className="card" style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12, maxWidth: 480 }}>
      <div style={{ fontWeight: 800 }}>Branding</div>
      <ColorField label="Primary colour" value={own.primary || ""} placeholder="inherit" disabled={busy} onChange={(v) => set({ primary: v })} />
      <ColorField label="Accent (optional)" value={own.accent || ""} placeholder="inherit" disabled={busy} onChange={(v) => set({ accent: v })} />
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ width: 110, fontSize: 13, fontWeight: 600 }}>Logo URL</span>
        <input type="text" value={own.logo_url || ""} placeholder="https://… (hosted image)" disabled={busy}
          onChange={(e) => set({ logo_url: e.target.value })}
          style={{ flex: 1, fontSize: 13, padding: "6px 8px", border: "1px solid var(--color-border,#e5e7eb)", borderRadius: 6 }} />
      </div>
      {/* Live preview — primary header + primary & accent buttons (what the diner's app will use). */}
      <div style={{ borderRadius: 10, overflow: "hidden", border: "1px solid var(--color-border,#e5e7eb)" }}>
        <div style={{ padding: "12px 14px", color: "#fff", fontWeight: 800, background: primary }}>
          {own.logo_url ? <img src={own.logo_url} alt="logo" style={{ height: 22, verticalAlign: "middle" }} /> : "Your storefront"}
        </div>
        <div style={{ padding: 12, display: "flex", gap: 8, alignItems: "center" }}>
          <button type="button" style={{ background: primary, color: "#fff", border: "none", borderRadius: 8, padding: "8px 14px", fontWeight: 700 }}>Add to cart</button>
          {accent && <button type="button" style={{ background: accent, color: "#4a2e00", border: "none", borderRadius: 8, padding: "8px 14px", fontWeight: 800 }}>Rewards</button>}
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
