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
  const [wheelCost, setWheelCost] = useState("");
  const [jackpotCost, setJackpotCost] = useState("");

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) {
      router.push("/merchant/login");
      return;
    }
    getSettings(base, tok, getOperatorMerchant()?.id)
      .then((s) => {
        setSettings(s);
        setWheelCost(String(s.wheel_spin_cost));
        setJackpotCost(String(s.jackpot_spin_cost));
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

  async function saveSpinCosts() {
    const tok = getStaffToken();
    if (!tok) return;
    const wheel = Number(wheelCost);
    const jackpot = Number(jackpotCost);
    if (!Number.isInteger(wheel) || wheel < 0 || !Number.isInteger(jackpot) || jackpot < 0) {
      setError("Spin costs must be whole numbers of 0 or more.");
      return;
    }
    setSaving(true);
    setError(null);
    setMsg(null);
    try {
      const updated = await updateSettings(
        base,
        tok,
        { wheel_spin_cost: wheel, jackpot_spin_cost: jackpot },
        getOperatorMerchant()?.id
      );
      setSettings(updated);
      setWheelCost(String(updated.wheel_spin_cost));
      setJackpotCost(String(updated.jackpot_spin_cost));
      setMsg("Settings saved.");
      setTimeout(() => setMsg(null), 2500);
    } catch (err: unknown) {
      const m = err instanceof Error ? err.message : "Failed to save settings";
      setError(m.includes("403") ? "Settings require the merchant owner role." : m);
    } finally {
      setSaving(false);
    }
  }

  const spinCostsDirty =
    !!settings &&
    (wheelCost !== String(settings.wheel_spin_cost) || jackpotCost !== String(settings.jackpot_spin_cost));

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

      {!loading && settings ? (
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontWeight: 600 }}>Game spin costs</div>
            <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
              Coins a diner spends per play. Set 0 to make a game free.
            </div>
          </div>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-end" }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="wheel-cost">Spin the Wheel (coins)</label>
              <input
                id="wheel-cost"
                type="number"
                min={0}
                step={1}
                value={wheelCost}
                disabled={saving}
                onChange={(e) => setWheelCost(e.target.value)}
                style={{ maxWidth: 140 }}
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="jackpot-cost">888 Jackpot (coins)</label>
              <input
                id="jackpot-cost"
                type="number"
                min={0}
                step={1}
                value={jackpotCost}
                disabled={saving}
                onChange={(e) => setJackpotCost(e.target.value)}
                style={{ maxWidth: 140 }}
              />
            </div>
            <button
              className="btn btn-sm btn-primary"
              disabled={saving || !spinCostsDirty}
              onClick={saveSpinCosts}
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      ) : null}
    </MerchantSidebar>
  );
}
