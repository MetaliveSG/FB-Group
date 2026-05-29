"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getSettings, updateSettings, getApiBase } from "@/lib/api";
import { getStaffToken, clearStaffToken, getOperatorMerchant } from "@/lib/auth";
import MerchantSidebar from "@/components/MerchantSidebar";
import type { MerchantSettings } from "@fbgroup/api-client";

export default function SettingsPage() {
  const router = useRouter();
  const base = getApiBase();

  const [settings, setSettings] = useState<MerchantSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) {
      router.push("/merchant/login");
      return;
    }
    getSettings(base, tok, getOperatorMerchant()?.id)
      .then((s) => {
        setSettings(s);
        setLoading(false);
      })
      .catch((err: unknown) => {
        const m = err instanceof Error ? err.message : "";
        if (m.includes("401")) {
          clearStaffToken();
          router.push("/merchant/login");
        } else {
          setError(m || "Failed to load settings");
          setLoading(false);
        }
      });
  }, [base, router]);

  async function togglePipeline(next: boolean) {
    const tok = getStaffToken();
    if (!tok) return;
    setSaving(true);
    setError(null);
    setMsg(null);
    try {
      const updated = await updateSettings(base, tok, { pipeline_enabled: next }, getOperatorMerchant()?.id);
      setSettings(updated);
      setMsg("Settings saved.");
      setTimeout(() => setMsg(null), 2500);
      // Notify the sidebar so the Pipeline nav link visibility updates.
      window.dispatchEvent(new CustomEvent("fbgroup:settings-changed"));
    } catch (err: unknown) {
      const m = err instanceof Error ? err.message : "Failed to save settings";
      const status =
        err && typeof err === "object" && "status" in err
          ? (err as { status?: number }).status
          : undefined;
      setError(status === 403 || m.includes("403") ? "Settings require the merchant owner role." : m);
    } finally {
      setSaving(false);
    }
  }

  return (
    <MerchantSidebar active="settings">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Merchant feature toggles</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {msg && <div className="alert alert-success">{msg}</div>}

      {loading ? (
        <div className="page-loading">
          <div className="spinner" /> Loading settings…
        </div>
      ) : settings ? (
        <div className="card">
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 16,
              flexWrap: "wrap",
            }}
          >
            <div>
              <div style={{ fontWeight: 600 }}>Sales &amp; Win-back Pipeline</div>
              <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                Show the Pipeline section. Walk-in-only merchants can hide it.
              </div>
            </div>
            <button
              className={`btn btn-sm ${settings.pipeline_enabled ? "btn-primary" : "btn-secondary"}`}
              disabled={saving}
              onClick={() => togglePipeline(!settings.pipeline_enabled)}
            >
              {settings.pipeline_enabled ? "Enabled" : "Disabled"}
            </button>
          </div>
        </div>
      ) : null}
    </MerchantSidebar>
  );
}
