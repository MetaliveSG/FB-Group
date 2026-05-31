"use client";

import { useState, useEffect, useCallback } from "react";
import { listPromotions, createPromotion, deactivatePromotion, getApiBase } from "@/lib/api";
import { getStaffToken, getOperatorMerchant } from "@/lib/auth";
import { Icons } from "@/components/ui";
import type { Promotion } from "@fbgroup/api-client";

// Time-bound point-multiplier promos (CAMPAIGN_MULTIPLIER) — distinct from the standing
// earn rules in Settings → Loyalty. Self-contained so it doesn't entangle the campaign list.
export default function PointMultipliers() {
  const base = getApiBase();
  const [promos, setPromos] = useState<Promotion[] | null>(null);
  const [label, setLabel] = useState("");
  const [multiplier, setMultiplier] = useState("2");
  const [startsOn, setStartsOn] = useState("");
  const [endsOn, setEndsOn] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const load = useCallback(async () => {
    const tok = getStaffToken();
    if (!tok) return;
    try {
      setPromos(await listPromotions(base, tok, getOperatorMerchant()?.id));
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to load promotions");
    }
  }, [base]);

  useEffect(() => { load(); }, [load]);

  async function create() {
    const tok = getStaffToken();
    if (!tok) return;
    const m = Number(multiplier);
    if (!label.trim() || Number.isNaN(m) || m < 1) {
      setErr("Enter a label and a multiplier of 1 or more.");
      return;
    }
    setBusy(true); setErr(null);
    try {
      await createPromotion(base, tok, {
        label: label.trim(), multiplier: m,
        starts_on: startsOn || null, ends_on: endsOn || null,
      }, getOperatorMerchant()?.id);
      setLabel(""); setMultiplier("2"); setStartsOn(""); setEndsOn("");
      await load();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Failed to create promotion";
      setErr(msg.includes("403") ? "Promotions require the owner / brand-manager role." : msg);
    } finally {
      setBusy(false);
    }
  }

  async function deactivate(id: string) {
    const tok = getStaffToken();
    if (!tok) return;
    setBusy(true); setErr(null);
    try {
      await deactivatePromotion(base, tok, id, getOperatorMerchant()?.id);
      await load();
    } finally {
      setBusy(false);
    }
  }

  const window = (p: Promotion) =>
    p.starts_on || p.ends_on ? `${p.starts_on ?? "…"} → ${p.ends_on ?? "…"}` : "Always on";

  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <div className="card-title" style={{ marginBottom: 4 }}>Point multipliers</div>
      <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 12 }}>
        Time-bound coin boosts (e.g. 2× this weekend). Applies to every earn during the window.
      </div>
      {err && <div className="alert alert-error">{err}</div>}

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end", marginBottom: 16 }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="pm-label">Label</label>
          <input id="pm-label" value={label} disabled={busy} onChange={(e) => setLabel(e.target.value)}
                 placeholder="Double Weekend" style={{ maxWidth: 180 }} />
        </div>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="pm-mult">Multiplier (×)</label>
          <input id="pm-mult" type="number" min={1} max={10} step="0.5" value={multiplier}
                 disabled={busy} onChange={(e) => setMultiplier(e.target.value)} style={{ maxWidth: 110 }} />
        </div>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="pm-start">Starts</label>
          <input id="pm-start" type="date" value={startsOn} disabled={busy}
                 onChange={(e) => setStartsOn(e.target.value)} style={{ maxWidth: 160 }} />
        </div>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="pm-end">Ends</label>
          <input id="pm-end" type="date" value={endsOn} disabled={busy}
                 onChange={(e) => setEndsOn(e.target.value)} style={{ maxWidth: 160 }} />
        </div>
        <button className="btn btn-sm btn-primary" disabled={busy} onClick={create}>Add</button>
      </div>

      {promos === null ? (
        <div style={{ color: "var(--color-text-muted)", fontSize: 13 }}>Loading…</div>
      ) : promos.length === 0 ? (
        <div style={{ color: "var(--color-text-muted)", fontSize: 13 }}>No multiplier promotions yet.</div>
      ) : (
        <table>
          <thead>
            <tr><th>Promo</th><th>Multiplier</th><th>Window</th><th>Status</th><th></th></tr>
          </thead>
          <tbody>
            {promos.map((p) => (
              <tr key={p.id} style={{ opacity: p.is_active ? 1 : 0.55 }}>
                <td>{p.label}</td>
                <td><strong>{p.multiplier}×</strong></td>
                <td style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{window(p)}</td>
                <td>
                  <span className="badge" style={{ background: p.is_active ? "#dcfce7" : "#f1f5f9", color: p.is_active ? "#166534" : "#64748b" }}>
                    {p.is_active ? "Active" : "Off"}
                  </span>
                </td>
                <td style={{ textAlign: "right" }}>
                  {p.is_active && (
                    <button className="btn btn-sm btn-secondary" style={{ padding: "2px 8px" }} disabled={busy}
                            onClick={() => deactivate(p.id)} title="Turn off promotion" aria-label="Turn off promotion">
                      <Icons.Trash2 size={15} aria-hidden />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
