"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getSettings, updateSettings, getLoyaltyProgram, updateLoyaltyProgram, getApiBase } from "@/lib/api";
import { getStaffToken, clearStaffToken, getOperatorMerchant } from "@/lib/auth";
import { REPORT_TIMEZONES } from "@/lib/timezones";
import MerchantSidebar from "@/components/MerchantSidebar";
import NodeDirectory from "@/components/NodeDirectory";
import PosStaffCard from "@/components/PosStaffCard";
import { useScope } from "@/lib/useScope";
import { Toggle } from "@/components/ui";
import type { MerchantSettings, LoyaltyProgram } from "@fbgroup/api-client";

type ModuleFlag = "rewards_enabled" | "qr_ordering_enabled" | "pos_enabled";
const MODULES: { key: ModuleFlag; label: string; desc: string }[] = [
  { key: "rewards_enabled", label: "Rewards / loyalty", desc: "Earn & redeem coins. The core capture loop." },
  { key: "qr_ordering_enabled", label: "Table-QR ordering", desc: "Diners order from the menu by scanning the table QR." },
  { key: "pos_enabled", label: "External POS feed", desc: "Accept orders pushed in from your existing/external POS for capture & reconciliation (coming soon). NOT the in-house Staff POS at /pos." },
];

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
  const [loyalty, setLoyalty] = useState<LoyaltyProgram | null>(null);
  const [earnRate, setEarnRate] = useState("");
  const [welcome, setWelcome] = useState("");
  const [birthday, setBirthday] = useState("");

  // Tree-scoped guard: settings are per-tenant → an operator above a tenant boundary picks a merchant first.
  const { scope, isOperator, nodes, ready, enter } = useScope();
  const needPick = ready && isOperator && !!scope && scope.tenantId === null;

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) {
      router.push("/merchant/login");
      return;
    }
    if (!ready || needPick) return; // wait for scope; don't fetch until a merchant is in scope
    const mid = getOperatorMerchant()?.id;
    Promise.all([getSettings(base, tok, mid), getLoyaltyProgram(base, tok, mid)])
      .then(([s, lp]) => {
        setSettings(s);
        setWheelCost(String(s.wheel_spin_cost));
        setJackpotCost(String(s.jackpot_spin_cost));
        setLoyalty(lp);
        setEarnRate(String(lp.points_per_dollar));
        setWelcome(String(lp.welcome_bonus));
        setBirthday(String(lp.birthday_bonus));
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
  }, [base, router, ready, needPick]);

  async function toggleModule(key: ModuleFlag, next: boolean) {
    const tok = getStaffToken();
    if (!tok || !settings) return;
    setSaving(true); setError(null); setMsg(null);
    try {
      const updated = await updateSettings(base, tok, { [key]: next }, getOperatorMerchant()?.id);
      setSettings(updated);
      setMsg("Settings saved.");
      setTimeout(() => setMsg(null), 2500);
    } catch (err: unknown) {
      const m = err instanceof Error ? err.message : "Failed to save settings";
      setError(m.includes("403") ? "Settings require the merchant owner role." : m);
    } finally {
      setSaving(false);
    }
  }

  async function saveTimezone(tz: string) {
    const tok = getStaffToken();
    if (!tok || !settings) return;
    setSaving(true); setError(null); setMsg(null);
    try {
      const updated = await updateSettings(base, tok, { timezone: tz }, getOperatorMerchant()?.id);
      setSettings(updated);
      setMsg("Reporting timezone saved.");
      setTimeout(() => setMsg(null), 2500);
    } catch (err: unknown) {
      const m = err instanceof Error ? err.message : "Failed to save settings";
      setError(m.includes("403") ? "Settings require the merchant owner role." : m);
    } finally {
      setSaving(false);
    }
  }

  async function saveReceipt(changes: Partial<MerchantSettings["receipt"]>) {
    const tok = getStaffToken();
    if (!tok || !settings) return;
    setSaving(true); setError(null); setMsg(null);
    try {
      const updated = await updateSettings(base, tok, { receipt: { ...settings.receipt, ...changes } }, getOperatorMerchant()?.id);
      setSettings(updated);
      setMsg("Receipt header saved.");
      setTimeout(() => setMsg(null), 2500);
    } catch (err: unknown) {
      const m = err instanceof Error ? err.message : "Failed to save settings";
      setError(m.includes("403") ? "Settings require the merchant owner role." : m);
    } finally {
      setSaving(false);
    }
  }

  async function saveWelcomeVoucher(changes: Partial<NonNullable<MerchantSettings["welcome_voucher"]>>) {
    const tok = getStaffToken();
    if (!tok || !settings) return;
    setSaving(true); setError(null); setMsg(null);
    try {
      const wv = { ...settings.welcome_voucher, ...changes };
      const updated = await updateSettings(base, tok, { welcome_voucher: wv }, getOperatorMerchant()?.id);
      setSettings(updated);
      setMsg("Welcome voucher saved.");
      setTimeout(() => setMsg(null), 2500);
    } catch (err: unknown) {
      const m = err instanceof Error ? err.message : "Failed to save settings";
      setError(m.includes("403") ? "Settings require the merchant owner role." : m);
    } finally {
      setSaving(false);
    }
  }

  async function saveLoyalty() {
    const tok = getStaffToken();
    if (!tok) return;
    const ppd = Number(earnRate), w = Number(welcome), b = Number(birthday);
    if ([ppd, w, b].some((n) => Number.isNaN(n) || n < 0)) {
      setError("Loyalty values must be 0 or more.");
      return;
    }
    setSaving(true); setError(null); setMsg(null);
    try {
      const updated = await updateLoyaltyProgram(
        base, tok, { points_per_dollar: ppd, welcome_bonus: w, birthday_bonus: b },
        getOperatorMerchant()?.id
      );
      setLoyalty(updated);
      setEarnRate(String(updated.points_per_dollar));
      setWelcome(String(updated.welcome_bonus));
      setBirthday(String(updated.birthday_bonus));
      setMsg("Loyalty program saved.");
      setTimeout(() => setMsg(null), 2500);
    } catch (err: unknown) {
      const m = err instanceof Error ? err.message : "Failed to save";
      setError(m.includes("403") ? "Loyalty rules require the merchant owner role." : m);
    } finally {
      setSaving(false);
    }
  }

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
  const loyaltyDirty =
    !!loyalty &&
    (earnRate !== String(loyalty.points_per_dollar) ||
      welcome !== String(loyalty.welcome_bonus) ||
      birthday !== String(loyalty.birthday_bonus));

  if (needPick) {
    return (
      <MerchantSidebar active="settings">
        <NodeDirectory feature="Settings" nodes={nodes} currentNodeId={scope!.currentNodeId} onEnter={enter} />
      </MerchantSidebar>
    );
  }

  return (
    <MerchantSidebar active="settings">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Loyalty program, modules &amp; feature toggles</p>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {msg && <div className="alert alert-success">{msg}</div>}

      {settings && (
        <div className="card" style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <div>
            <div style={{ fontWeight: 600 }}>Reporting timezone</div>
            <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
              All sales reports, payouts &amp; the daily close use this timezone (the &ldquo;books&rdquo;).
            </div>
          </div>
          <select value={settings.timezone} disabled={saving} style={{ minWidth: 220 }}
                  onChange={(e) => saveTimezone(e.target.value)}>
            {REPORT_TIMEZONES.map(([z, label]) => (
              <option key={z} value={z}>{label}</option>
            ))}
            {!REPORT_TIMEZONES.some(([z]) => z === settings.timezone) && (
              <option value={settings.timezone}>{settings.timezone}</option>
            )}
          </select>
        </div>
      )}

      {/* POS receipt company header */}
      {settings?.receipt && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 600 }}>Receipt header (POS)</div>
          <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 10 }}>
            Printed at the top of every POS receipt.
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, maxWidth: 560 }}>
            {([["company_name", "Company name"], ["uen", "UEN"], ["address", "Address"], ["phone", "Phone"], ["footer", "Footer"]] as const).map(([k, label]) => (
              <label key={k} style={{ fontSize: 13, gridColumn: (k === "address" || k === "footer") ? "1 / -1" : undefined }}>
                {label}
                <input defaultValue={settings.receipt[k]} disabled={saving}
                       onBlur={(e) => { if (e.target.value !== settings.receipt[k]) saveReceipt({ [k]: e.target.value }); }}
                       style={{ display: "block", width: "100%", marginTop: 2 }} />
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Staff & PINs (POS) — owner self-serve for POS logins (below the Receipt header). */}
      <PosStaffCard base={base} />

      {/* Welcome voucher pack — granted on signup (a campaign trigger). */}
      {settings?.welcome_voucher && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
            <div>
              <div style={{ fontWeight: 600 }}>Welcome voucher</div>
              <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                Vouchers granted automatically when a new customer signs up here.
              </div>
            </div>
            <Toggle on={settings.welcome_voucher.enabled} disabled={saving}
                    onChange={(v) => saveWelcomeVoucher({ enabled: v })} />
          </div>
          {settings.welcome_voucher.enabled && (
            <div style={{ display: "flex", gap: 14, flexWrap: "wrap", marginTop: 12 }}>
              <label style={{ fontSize: 13 }}>$ off each
                <input type="number" min="0" step="0.5" defaultValue={settings.welcome_voucher.value} disabled={saving}
                       onBlur={(e) => saveWelcomeVoucher({ value: parseFloat(e.target.value) || 0 })}
                       style={{ width: 90, display: "block" }} />
              </label>
              <label style={{ fontSize: 13 }}>How many
                <input type="number" min="1" defaultValue={settings.welcome_voucher.count} disabled={saving}
                       onBlur={(e) => saveWelcomeVoucher({ count: parseInt(e.target.value, 10) || 1 })}
                       style={{ width: 90, display: "block" }} />
              </label>
              <label style={{ fontSize: 13 }}>Usable
                <select value={settings.welcome_voucher.per_period ?? ""} disabled={saving}
                        onChange={(e) => saveWelcomeVoucher({ per_period: (e.target.value || null) as "day" | "week" | "month" | null })}
                        style={{ display: "block" }}>
                  <option value="">No limit</option>
                  <option value="day">1 per day</option>
                  <option value="week">1 per week</option>
                  <option value="month">1 per month</option>
                </select>
              </label>
              <label style={{ fontSize: 13 }}>Valid (days)
                <input type="number" min="1" defaultValue={settings.welcome_voucher.valid_days ?? ""} disabled={saving}
                       onBlur={(e) => saveWelcomeVoucher({ valid_days: parseInt(e.target.value, 10) || null })}
                       style={{ width: 100, display: "block" }} />
              </label>
            </div>
          )}
        </div>
      )}

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
            <Toggle
              on={settings.pipeline_enabled}
              disabled={saving}
              onChange={(next) => togglePipeline(next)}
              label="Sales & Win-back Pipeline"
            />
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

      {/* Loyalty program — the standing earn rules (the self-serve config that was missing) */}
      {!loading && loyalty ? (
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontWeight: 600 }}>Loyalty program</div>
            <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
              Coins customers earn. Set 0 to switch a rule off. (Time-limited promos live under Campaigns.)
            </div>
          </div>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap", alignItems: "flex-end" }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="earn-rate">Coins per $1 spent</label>
              <input id="earn-rate" type="number" min={0} step="0.1" value={earnRate}
                     disabled={saving} onChange={(e) => setEarnRate(e.target.value)} style={{ maxWidth: 140 }} />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="welcome-bonus">Welcome bonus (first visit)</label>
              <input id="welcome-bonus" type="number" min={0} step={1} value={welcome}
                     disabled={saving} onChange={(e) => setWelcome(e.target.value)} style={{ maxWidth: 140 }} />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label htmlFor="birthday-bonus">Birthday bonus</label>
              <input id="birthday-bonus" type="number" min={0} step={1} value={birthday}
                     disabled={saving} onChange={(e) => setBirthday(e.target.value)} style={{ maxWidth: 140 }} />
            </div>
            <button className="btn btn-sm btn-primary" disabled={saving || !loyaltyDirty} onClick={saveLoyalty}>
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      ) : null}

      {/* Modules — which parts of the suite this merchant runs (gates behaviour) */}
      {!loading && settings ? (
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontWeight: 600 }}>Modules</div>
            <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
              Turn features on or off for this merchant.
            </div>
          </div>
          {MODULES.map((m) => (
            <div key={m.key} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, padding: "10px 0", borderTop: "1px solid var(--color-border)" }}>
              <div>
                <div style={{ fontWeight: 600 }}>{m.label}</div>
                <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{m.desc}</div>
              </div>
              <Toggle
                on={settings[m.key]}
                disabled={saving}
                onChange={(next) => toggleModule(m.key, next)}
                label={m.label}
              />
            </div>
          ))}
        </div>
      ) : null}
    </MerchantSidebar>
  );
}
