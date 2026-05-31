"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  platformOverview,
  platformMerchants,
  platformCoalitions,
  platformCreateMerchant,
  platformSetMerchantActive,
  getApiBase,
  installAuthHandler,
  AUTH_LOGOUT_EVENT,
} from "@/lib/api";
import {
  getStaffToken,
  clearStaffToken,
  setOperatorMerchant,
} from "@/lib/auth";
import { formatSGD } from "@/lib/format";
import { Toggle } from "@/components/ui";
import type {
  PlatformOverview,
  MerchantKpi,
  Coalition,
} from "@fbgroup/api-client";

export default function OperatorConsolePage() {
  const router = useRouter();
  const base = getApiBase();

  const [overview, setOverview] = useState<PlatformOverview | null>(null);
  const [merchants, setMerchants] = useState<MerchantKpi[]>([]);
  const [coalitions, setCoalitions] = useState<Coalition[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  // Onboard merchant form
  const [showForm, setShowForm] = useState(false);
  const [mName, setMName] = useState("");
  const [mEmail, setMEmail] = useState("");
  const [mPassword, setMPassword] = useState("");
  const [mOwnerName, setMOwnerName] = useState("");
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  const loadAll = useCallback(
    async (tok: string) => {
      const [ov, ms, cs] = await Promise.all([
        platformOverview(base, tok),
        platformMerchants(base, tok),
        platformCoalitions(base, tok),
      ]);
      setOverview(ov);
      setMerchants(ms);
      setCoalitions(cs);
    },
    [base]
  );

  useEffect(() => {
    installAuthHandler();
    function onLogout(e: Event) {
      const detail = (e as CustomEvent).detail as { actor?: string } | undefined;
      if (detail?.actor && detail.actor !== "staff") return;
      router.push("/operator/login");
    }
    window.addEventListener(AUTH_LOGOUT_EVENT, onLogout);

    const tok = getStaffToken();
    if (!tok) {
      router.push("/operator/login");
      return () => window.removeEventListener(AUTH_LOGOUT_EVENT, onLogout);
    }
    loadAll(tok)
      .then(() => setLoading(false))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "";
        const status =
          err && typeof err === "object" && "status" in err
            ? (err as { status?: number }).status
            : undefined;
        if (status === 403 || msg.includes("403")) {
          // Not an operator — bounce to operator login (it explains why).
          clearStaffToken();
          router.push("/operator/login");
        } else {
          setError(msg || "Failed to load operator console");
          setLoading(false);
        }
      });

    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, onLogout);
  }, [loadAll, router]);

  function enterMerchant(m: MerchantKpi) {
    setOperatorMerchant({ id: m.id, name: m.name });
    router.push("/merchant/crm");
  }

  async function toggleActive(m: MerchantKpi) {
    const tok = getStaffToken();
    if (!tok) return;
    setTogglingId(m.id);
    try {
      const updated = await platformSetMerchantActive(base, tok, m.id, !m.is_active);
      setMerchants((prev) => prev.map((x) => (x.id === m.id ? updated : x)));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update merchant status");
    } finally {
      setTogglingId(null);
    }
  }

  async function onboard(e: React.FormEvent) {
    e.preventDefault();
    const tok = getStaffToken();
    if (!tok) return;
    setFormError(null);
    setFormSuccess(null);
    setCreating(true);
    try {
      const res = await platformCreateMerchant(base, tok, {
        name: mName.trim(),
        owner_email: mEmail.trim(),
        owner_password: mPassword,
        owner_name: mOwnerName.trim() || undefined,
      });
      setFormSuccess(`Created "${res.name}" with owner ${res.owner_email}.`);
      setMName("");
      setMEmail("");
      setMPassword("");
      setMOwnerName("");
      await loadAll(tok);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create merchant";
      const status =
        err && typeof err === "object" && "status" in err
          ? (err as { status?: number }).status
          : undefined;
      if (status === 409 || msg.toLowerCase().includes("exist") || msg.includes("409")) {
        setFormError("That owner email already exists. Choose a different email.");
      } else {
        setFormError(msg);
      }
    } finally {
      setCreating(false);
    }
  }

  function logout() {
    clearStaffToken();
    router.push("/operator/login");
  }

  if (loading) {
    return (
      <div className="page-loading">
        <div className="spinner" /> Loading operator console…
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "28px 32px" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          marginBottom: 24,
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div>
          <h1 className="page-title">Operator Console</h1>
          <p className="page-subtitle">Platform overview across all merchants</p>
        </div>
        <button onClick={logout} className="btn btn-secondary btn-sm">
          Logout
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Global KPIs */}
      {overview && (
        <div className="kpi-grid" style={{ marginBottom: 28 }}>
          <div className="kpi-card">
            <div className="kpi-label">GMV</div>
            <div className="kpi-value">{formatSGD(overview.gmv)}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Orders</div>
            <div className="kpi-value">{overview.orders.toLocaleString()}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Active Customers</div>
            <div className="kpi-value">{overview.active_customers.toLocaleString()}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Merchants</div>
            <div className="kpi-value">
              {overview.merchants_active}
              <span style={{ fontSize: 14, color: "var(--color-text-muted)" }}>
                {" "}
                / {overview.merchants_total}
              </span>
            </div>
            <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>active / total</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Brands</div>
            <div className="kpi-value">{overview.brands.toLocaleString()}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Outlets</div>
            <div className="kpi-value">{overview.outlets.toLocaleString()}</div>
          </div>
          <div className="kpi-card">
            <div className="kpi-label">Coalitions</div>
            <div className="kpi-value">{overview.coalitions.toLocaleString()}</div>
          </div>
        </div>
      )}

      {/* Merchant directory */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 14,
        }}
      >
        <h2 className="card-title" style={{ fontSize: 18 }}>
          Merchant Directory
        </h2>
        <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Cancel" : "+ Onboard Merchant"}
        </button>
      </div>

      {/* Onboard form */}
      {showForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <h3 className="card-title" style={{ marginBottom: 14 }}>
            Onboard New Merchant
          </h3>
          {formError && <div className="alert alert-error">{formError}</div>}
          {formSuccess && <div className="alert alert-success">{formSuccess}</div>}
          <form onSubmit={onboard}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: 14,
              }}
            >
              <div className="form-group">
                <label htmlFor="m-name">Merchant Name</label>
                <input
                  id="m-name"
                  type="text"
                  value={mName}
                  onChange={(e) => setMName(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="m-owner-name">Owner Name (optional)</label>
                <input
                  id="m-owner-name"
                  type="text"
                  value={mOwnerName}
                  onChange={(e) => setMOwnerName(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label htmlFor="m-email">Owner Email</label>
                <input
                  id="m-email"
                  type="email"
                  value={mEmail}
                  onChange={(e) => setMEmail(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="m-password">Owner Password</label>
                <input
                  id="m-password"
                  type="password"
                  value={mPassword}
                  onChange={(e) => setMPassword(e.target.value)}
                  required
                  minLength={8}
                  placeholder="min 8 characters"
                />
              </div>
            </div>
            <button type="submit" className="btn btn-primary" disabled={creating}>
              {creating ? "Creating…" : "Create Merchant"}
            </button>
          </form>
        </div>
      )}

      <div className="table-wrapper" style={{ marginBottom: 28 }}>
        <table>
          <thead>
            <tr>
              <th>Merchant</th>
              <th>Status</th>
              <th>Revenue</th>
              <th>Orders</th>
              <th>Customers</th>
              <th>Outlets</th>
              <th>Owner</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {merchants.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: "center", color: "var(--color-text-muted)" }}>
                  No merchants yet.
                </td>
              </tr>
            ) : (
              merchants.map((m) => (
                <tr key={m.id}>
                  <td>
                    <strong>{m.name}</strong>
                    <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                      {m.brands} brand{m.brands === 1 ? "" : "s"}
                    </div>
                  </td>
                  <td>
                    <div style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                      <Toggle
                        on={m.is_active}
                        disabled={togglingId === m.id}
                        onChange={() => toggleActive(m)}
                        label={m.is_active ? "Suspend merchant" : "Activate merchant"}
                      />
                      <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                        {togglingId === m.id ? "…" : m.is_active ? "Active" : "Suspended"}
                      </span>
                    </div>
                  </td>
                  <td>{formatSGD(m.revenue)}</td>
                  <td>{m.orders.toLocaleString()}</td>
                  <td>{m.customers.toLocaleString()}</td>
                  <td>{m.outlets}</td>
                  <td>
                    <div style={{ fontSize: 13 }}>{m.owner_name || "—"}</div>
                    <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                      {m.owner_email || ""}
                    </div>
                  </td>
                  <td>
                    <button className="btn btn-secondary btn-sm" onClick={() => enterMerchant(m)}>
                      Enter merchant →
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Coalitions */}
      <h2 className="card-title" style={{ fontSize: 18, marginBottom: 14 }}>
        Coalitions
      </h2>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: 16,
        }}
      >
        {coalitions.length === 0 ? (
          <p style={{ color: "var(--color-text-muted)" }}>No coalitions.</p>
        ) : (
          coalitions.map((c) => (
            <div className="card" key={c.id}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 8,
                }}
              >
                <strong>{c.name}</strong>
                <span
                  className="badge"
                  style={{
                    background: c.is_active ? "#dcfce7" : "#fee2e2",
                    color: c.is_active ? "#166534" : "#991b1b",
                  }}
                >
                  {c.is_active ? "Active" : "Inactive"}
                </span>
              </div>
              <div style={{ fontSize: 13, color: "var(--color-text-muted)", marginBottom: 8 }}>
                {c.member_count} member{c.member_count === 1 ? "" : "s"} ·{" "}
                {c.points_issued.toLocaleString()} pts issued
              </div>
              {c.members.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {c.members.map((mem, i) => (
                    <span
                      key={i}
                      className="badge"
                      style={{ background: "#eff6ff", color: "var(--color-primary)" }}
                    >
                      {mem}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
