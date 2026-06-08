"use client";

import { useEffect, useState } from "react";
import { getSettings, updateSettings } from "@/lib/api";
import { getStaffToken } from "@/lib/auth";
import type { MerchantSettings } from "@fbgroup/api-client";

// POS receipt company header — printed at the top of every POS receipt. Self-contained (loads/saves
// via /org/settings); lives under POS → "POS Settings" (moved out of the merchant-wide Settings page).
export default function PosReceiptCard({ base, merchantId }: { base: string; merchantId?: string }) {
  const [settings, setSettings] = useState<MerchantSettings | null>(null);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) return;
    getSettings(base, tok, merchantId).then(setSettings).catch(() => setSettings(null));
  }, [base, merchantId]);

  async function save(changes: Partial<MerchantSettings["receipt"]>) {
    const tok = getStaffToken();
    if (!tok || !settings) return;
    setSaving(true); setError(null); setMsg(null);
    try {
      const updated = await updateSettings(base, tok, { receipt: { ...settings.receipt, ...changes } }, merchantId);
      setSettings(updated);
      setMsg("Receipt header saved.");
      setTimeout(() => setMsg(null), 2500);
    } catch (err: unknown) {
      const m = err instanceof Error ? err.message : "Failed to save";
      setError(m.includes("403") ? "Receipt config requires the merchant owner role." : m);
    } finally {
      setSaving(false);
    }
  }

  if (!settings?.receipt) return null;
  const fields = [["company_name", "Company name"], ["uen", "UEN"], ["address", "Address"], ["phone", "Phone"], ["footer", "Footer"]] as const;
  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div style={{ fontWeight: 600 }}>Receipt header</div>
      <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 10 }}>Printed at the top of every POS receipt.</div>
      {error && <div style={{ color: "#b91c1c", fontSize: 13, marginBottom: 8 }}>{error}</div>}
      {msg && <div style={{ color: "#15803d", fontSize: 13, marginBottom: 8 }}>{msg}</div>}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, maxWidth: 560 }}>
        {fields.map(([k, label]) => (
          <label key={k} style={{ fontSize: 13, gridColumn: (k === "address" || k === "footer") ? "1 / -1" : undefined }}>
            {label}
            <input defaultValue={settings.receipt[k]} disabled={saving}
                   onBlur={(e) => { if (e.target.value !== settings.receipt[k]) save({ [k]: e.target.value }); }}
                   style={{ display: "block", width: "100%", marginTop: 2 }} />
          </label>
        ))}
      </div>
    </div>
  );
}
