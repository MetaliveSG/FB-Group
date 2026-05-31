"use client";

import { useState, useEffect, useCallback, Fragment } from "react";
import { useRouter } from "next/navigation";
import {
  platformOverview,
  platformMerchants,
  platformCoalitions,
  platformCreateMerchant,
  platformSetMerchantActive,
  platformUpdateMerchant,
  platformOperators,
  platformInviteOperator,
  platformRevokeOperator,
  platformCreateCoalition,
  platformUpdateCoalition,
  platformAddCoalitionMember,
  platformRemoveCoalitionMember,
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
import { Toggle, Icons } from "@/components/ui";
import type {
  PlatformOverview,
  MerchantKpi,
  Coalition,
  Operator,
} from "@fbgroup/api-client";

// The three adoption module flags, in display order.
const MODULE_FLAGS: { key: string; label: string }[] = [
  { key: "rewards_enabled", label: "Rewards" },
  { key: "qr_ordering_enabled", label: "QR Ordering" },
  { key: "pos_enabled", label: "POS" },
];

function errStatus(err: unknown): number | undefined {
  return err && typeof err === "object" && "status" in err
    ? (err as { status?: number }).status
    : undefined;
}
function errMsg(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export default function OperatorConsolePage() {
  const router = useRouter();
  const base = getApiBase();

  const [overview, setOverview] = useState<PlatformOverview | null>(null);
  const [merchants, setMerchants] = useState<MerchantKpi[]>([]);
  const [coalitions, setCoalitions] = useState<Coalition[]>([]);
  const [operators, setOperators] = useState<Operator[]>([]);
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

  // Merchant edit (rename + module flags)
  const [editMerchantId, setEditMerchantId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editFlags, setEditFlags] = useState<Record<string, boolean>>({});
  const [savingMerchant, setSavingMerchant] = useState(false);

  // Operators
  const [showOpForm, setShowOpForm] = useState(false);
  const [opEmail, setOpEmail] = useState("");
  const [opPassword, setOpPassword] = useState("");
  const [opName, setOpName] = useState("");
  const [opCreating, setOpCreating] = useState(false);
  const [opError, setOpError] = useState<string | null>(null);
  const [opSuccess, setOpSuccess] = useState<string | null>(null);

  // Coalitions
  const [showCoaForm, setShowCoaForm] = useState(false);
  const [coaName, setCoaName] = useState("");
  const [coaCreating, setCoaCreating] = useState(false);
  const [coaError, setCoaError] = useState<string | null>(null);
  const [editCoaId, setEditCoaId] = useState<string | null>(null);
  const [editCoaName, setEditCoaName] = useState("");
  const [addMemberSel, setAddMemberSel] = useState<Record<string, string>>({});

  const loadAll = useCallback(
    async (tok: string) => {
      const [ov, ms, cs, ops] = await Promise.all([
        platformOverview(base, tok),
        platformMerchants(base, tok),
        platformCoalitions(base, tok),
        platformOperators(base, tok),
      ]);
      setOverview(ov);
      setMerchants(ms);
      setCoalitions(cs);
      setOperators(ops);
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
        const msg = errMsg(err, "");
        if (errStatus(err) === 403 || msg.includes("403")) {
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
      setError(errMsg(err, "Failed to update merchant status"));
    } finally {
      setTogglingId(null);
    }
  }

  function startEditMerchant(m: MerchantKpi) {
    setEditMerchantId(m.id);
    setEditName(m.name);
    setEditFlags({ ...m.module_flags });
    setError(null);
  }

  async function saveMerchant(merchantId: string) {
    const tok = getStaffToken();
    if (!tok) return;
    setSavingMerchant(true);
    try {
      const updated = await platformUpdateMerchant(base, tok, merchantId, {
        name: editName.trim(),
        module_flags: editFlags,
      });
      setMerchants((prev) => prev.map((x) => (x.id === merchantId ? updated : x)));
      setEditMerchantId(null);
    } catch (err: unknown) {
      setError(errMsg(err, "Failed to update merchant"));
    } finally {
      setSavingMerchant(false);
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
      const msg = errMsg(err, "Failed to create merchant");
      if (errStatus(err) === 409 || msg.toLowerCase().includes("exist") || msg.includes("409")) {
        setFormError("That owner email already exists. Choose a different email.");
      } else {
        setFormError(msg);
      }
    } finally {
      setCreating(false);
    }
  }

  async function inviteOperator(e: React.FormEvent) {
    e.preventDefault();
    const tok = getStaffToken();
    if (!tok) return;
    setOpError(null);
    setOpSuccess(null);
    setOpCreating(true);
    try {
      const op = await platformInviteOperator(base, tok, {
        email: opEmail.trim(),
        password: opPassword,
        full_name: opName.trim() || undefined,
      });
      setOpSuccess(`Added operator ${op.email}.`);
      setOpEmail("");
      setOpPassword("");
      setOpName("");
      const ops = await platformOperators(base, tok);
      setOperators(ops);
    } catch (err: unknown) {
      const msg = errMsg(err, "Failed to add operator");
      if (errStatus(err) === 409 || msg.includes("409")) {
        setOpError("That email already exists. Choose a different email.");
      } else {
        setOpError(msg);
      }
    } finally {
      setOpCreating(false);
    }
  }

  async function revokeOperator(op: Operator) {
    const tok = getStaffToken();
    if (!tok) return;
    if (!window.confirm(`Remove operator access for ${op.email}?`)) return;
    try {
      await platformRevokeOperator(base, tok, op.id);
      setOperators((prev) => prev.filter((x) => x.id !== op.id));
    } catch (err: unknown) {
      setOpError(errMsg(err, "Failed to remove operator"));
    }
  }

  async function createCoalition(e: React.FormEvent) {
    e.preventDefault();
    const tok = getStaffToken();
    if (!tok) return;
    setCoaError(null);
    setCoaCreating(true);
    try {
      const c = await platformCreateCoalition(base, tok, coaName.trim());
      setCoalitions((prev) => [...prev, c]);
      setCoaName("");
      setShowCoaForm(false);
    } catch (err: unknown) {
      setCoaError(errMsg(err, "Failed to create coalition"));
    } finally {
      setCoaCreating(false);
    }
  }

  function replaceCoalition(c: Coalition) {
    setCoalitions((prev) => prev.map((x) => (x.id === c.id ? c : x)));
  }

  async function toggleCoalitionActive(c: Coalition) {
    const tok = getStaffToken();
    if (!tok) return;
    try {
      const updated = await platformUpdateCoalition(base, tok, c.id, { is_active: !c.is_active });
      replaceCoalition(updated);
    } catch (err: unknown) {
      setCoaError(errMsg(err, "Failed to update coalition"));
    }
  }

  async function saveCoalitionName(c: Coalition) {
    const tok = getStaffToken();
    if (!tok) return;
    try {
      const updated = await platformUpdateCoalition(base, tok, c.id, { name: editCoaName.trim() });
      replaceCoalition(updated);
      setEditCoaId(null);
    } catch (err: unknown) {
      setCoaError(errMsg(err, "Failed to rename coalition"));
    }
  }

  async function addMember(c: Coalition) {
    const tok = getStaffToken();
    if (!tok) return;
    const merchantId = addMemberSel[c.id];
    if (!merchantId) return;
    try {
      const updated = await platformAddCoalitionMember(base, tok, c.id, merchantId);
      replaceCoalition(updated);
      setAddMemberSel((prev) => ({ ...prev, [c.id]: "" }));
    } catch (err: unknown) {
      setCoaError(errMsg(err, "Failed to add member"));
    }
  }

  async function removeMember(c: Coalition, merchantId: string) {
    const tok = getStaffToken();
    if (!tok) return;
    try {
      const updated = await platformRemoveCoalitionMember(base, tok, c.id, merchantId);
      replaceCoalition(updated);
    } catch (err: unknown) {
      setCoaError(errMsg(err, "Failed to remove member"));
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

  const merchantName = (id: string) => merchants.find((m) => m.id === id)?.name || id;

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
              <th>Modules</th>
              <th>Revenue</th>
              <th>Orders</th>
              <th>Customers</th>
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
                <Fragment key={m.id}>
                  <tr>
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
                    <td>
                      <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                        {MODULE_FLAGS.filter((f) => m.module_flags?.[f.key]).map((f) => (
                          <span
                            key={f.key}
                            className="badge"
                            style={{ background: "#ecfdf5", color: "#047857", fontSize: 11 }}
                          >
                            {f.label}
                          </span>
                        ))}
                        {MODULE_FLAGS.every((f) => !m.module_flags?.[f.key]) && (
                          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>—</span>
                        )}
                      </div>
                    </td>
                    <td>{formatSGD(m.revenue)}</td>
                    <td>{m.orders.toLocaleString()}</td>
                    <td>{m.customers.toLocaleString()}</td>
                    <td>
                      <div style={{ fontSize: 13 }}>{m.owner_name || "—"}</div>
                      <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                        {m.owner_email || ""}
                      </div>
                    </td>
                    <td>
                      <div style={{ display: "inline-flex", gap: 6 }}>
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ padding: "4px 8px", display: "inline-flex", alignItems: "center" }}
                          onClick={() =>
                            editMerchantId === m.id ? setEditMerchantId(null) : startEditMerchant(m)
                          }
                          title="Edit merchant"
                          aria-label="Edit merchant"
                        >
                          <Icons.Pencil size={14} aria-hidden />
                        </button>
                        <button className="btn btn-secondary btn-sm" onClick={() => enterMerchant(m)}>
                          Enter →
                        </button>
                      </div>
                    </td>
                  </tr>
                  {editMerchantId === m.id && (
                    <tr>
                      <td colSpan={8} style={{ background: "var(--color-surface-2, #f8fafc)" }}>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 20, alignItems: "flex-end", padding: "4px 0" }}>
                          <div className="form-group" style={{ margin: 0, minWidth: 220 }}>
                            <label htmlFor={`edit-name-${m.id}`}>Merchant Name</label>
                            <input
                              id={`edit-name-${m.id}`}
                              type="text"
                              value={editName}
                              onChange={(e) => setEditName(e.target.value)}
                            />
                          </div>
                          <div style={{ display: "flex", gap: 18, flexWrap: "wrap" }}>
                            {MODULE_FLAGS.map((f) => (
                              <div key={f.key} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                                <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{f.label}</span>
                                <Toggle
                                  on={!!editFlags[f.key]}
                                  onChange={() =>
                                    setEditFlags((prev) => ({ ...prev, [f.key]: !prev[f.key] }))
                                  }
                                  label={`Toggle ${f.label}`}
                                />
                              </div>
                            ))}
                          </div>
                          <div style={{ display: "flex", gap: 8 }}>
                            <button
                              className="btn btn-primary btn-sm"
                              disabled={savingMerchant || !editName.trim()}
                              onClick={() => saveMerchant(m.id)}
                            >
                              {savingMerchant ? "Saving…" : "Save"}
                            </button>
                            <button className="btn btn-secondary btn-sm" onClick={() => setEditMerchantId(null)}>
                              Cancel
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Platform operators */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 14,
        }}
      >
        <h2 className="card-title" style={{ fontSize: 18 }}>
          Operators
        </h2>
        <button className="btn btn-primary btn-sm" onClick={() => setShowOpForm((s) => !s)}>
          {showOpForm ? "Cancel" : "+ Add Operator"}
        </button>
      </div>
      <p style={{ fontSize: 13, color: "var(--color-text-muted)", marginTop: 0, marginBottom: 14 }}>
        Operators have full super-admin access to this console.
      </p>

      {showOpForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          {opError && <div className="alert alert-error">{opError}</div>}
          {opSuccess && <div className="alert alert-success">{opSuccess}</div>}
          <form onSubmit={inviteOperator}>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: 14,
              }}
            >
              <div className="form-group">
                <label htmlFor="op-name">Name (optional)</label>
                <input id="op-name" type="text" value={opName} onChange={(e) => setOpName(e.target.value)} />
              </div>
              <div className="form-group">
                <label htmlFor="op-email">Email</label>
                <input
                  id="op-email"
                  type="email"
                  value={opEmail}
                  onChange={(e) => setOpEmail(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label htmlFor="op-password">Password</label>
                <input
                  id="op-password"
                  type="password"
                  value={opPassword}
                  onChange={(e) => setOpPassword(e.target.value)}
                  required
                  minLength={8}
                  placeholder="min 8 characters"
                />
              </div>
            </div>
            <button type="submit" className="btn btn-primary" disabled={opCreating}>
              {opCreating ? "Adding…" : "Add Operator"}
            </button>
          </form>
        </div>
      )}

      <div className="table-wrapper" style={{ marginBottom: 28 }}>
        <table>
          <thead>
            <tr>
              <th>Operator</th>
              <th>Email</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {operators.map((op) => (
              <tr key={op.id}>
                <td>
                  <strong>{op.full_name || op.email}</strong>
                  {op.is_self && (
                    <span
                      className="badge"
                      style={{ marginLeft: 8, background: "#eff6ff", color: "var(--color-primary)", fontSize: 11 }}
                    >
                      You
                    </span>
                  )}
                </td>
                <td>{op.email}</td>
                <td>
                  <span
                    className="badge"
                    style={{
                      background: op.is_active ? "#dcfce7" : "#fee2e2",
                      color: op.is_active ? "#166534" : "#991b1b",
                    }}
                  >
                    {op.is_active ? "Active" : "Inactive"}
                  </span>
                </td>
                <td>
                  {!op.is_self && (
                    <button
                      className="btn btn-secondary btn-sm"
                      style={{ padding: "4px 8px", display: "inline-flex", alignItems: "center" }}
                      onClick={() => revokeOperator(op)}
                      title="Remove operator access"
                      aria-label="Remove operator access"
                    >
                      <Icons.Trash2 size={14} aria-hidden />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Coalitions */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 14,
        }}
      >
        <h2 className="card-title" style={{ fontSize: 18 }}>
          Coalitions
        </h2>
        <button className="btn btn-primary btn-sm" onClick={() => setShowCoaForm((s) => !s)}>
          {showCoaForm ? "Cancel" : "+ New Coalition"}
        </button>
      </div>

      {coaError && <div className="alert alert-error">{coaError}</div>}

      {showCoaForm && (
        <div className="card" style={{ marginBottom: 20 }}>
          <form onSubmit={createCoalition} style={{ display: "flex", gap: 10, alignItems: "flex-end", flexWrap: "wrap" }}>
            <div className="form-group" style={{ margin: 0, minWidth: 240 }}>
              <label htmlFor="coa-name">Coalition Name</label>
              <input
                id="coa-name"
                type="text"
                value={coaName}
                onChange={(e) => setCoaName(e.target.value)}
                required
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={coaCreating || !coaName.trim()}>
              {coaCreating ? "Creating…" : "Create"}
            </button>
          </form>
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
          gap: 16,
        }}
      >
        {coalitions.length === 0 ? (
          <p style={{ color: "var(--color-text-muted)" }}>No coalitions.</p>
        ) : (
          coalitions.map((c) => {
            const nonMembers = merchants.filter((m) => !c.member_ids.includes(m.id));
            return (
              <div className="card" key={c.id}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 8,
                    gap: 8,
                  }}
                >
                  {editCoaId === c.id ? (
                    <input
                      type="text"
                      value={editCoaName}
                      onChange={(e) => setEditCoaName(e.target.value)}
                      style={{ flex: 1 }}
                      autoFocus
                    />
                  ) : (
                    <strong>{c.name}</strong>
                  )}
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    {editCoaId === c.id ? (
                      <>
                        <button
                          className="btn btn-primary btn-sm"
                          style={{ padding: "4px 8px" }}
                          onClick={() => saveCoalitionName(c)}
                          disabled={!editCoaName.trim()}
                        >
                          <Icons.Check size={14} aria-hidden />
                        </button>
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ padding: "4px 8px" }}
                          onClick={() => setEditCoaId(null)}
                        >
                          <Icons.X size={14} aria-hidden />
                        </button>
                      </>
                    ) : (
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ padding: "4px 8px", display: "inline-flex", alignItems: "center" }}
                        onClick={() => {
                          setEditCoaId(c.id);
                          setEditCoaName(c.name);
                        }}
                        title="Rename coalition"
                        aria-label="Rename coalition"
                      >
                        <Icons.Pencil size={14} aria-hidden />
                      </button>
                    )}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                  <Toggle
                    on={c.is_active}
                    onChange={() => toggleCoalitionActive(c)}
                    label={c.is_active ? "Deactivate coalition" : "Activate coalition"}
                  />
                  <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                    {c.is_active ? "Active" : "Inactive"} · {c.points_issued.toLocaleString()} pts issued
                  </span>
                </div>

                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 10 }}>
                  {c.member_ids.length === 0 ? (
                    <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>No members yet.</span>
                  ) : (
                    c.member_ids.map((mid) => (
                      <span
                        key={mid}
                        className="badge"
                        style={{
                          background: "#eff6ff",
                          color: "var(--color-primary)",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: 4,
                        }}
                      >
                        {merchantName(mid)}
                        <button
                          onClick={() => removeMember(c, mid)}
                          title="Remove member"
                          aria-label={`Remove ${merchantName(mid)}`}
                          style={{
                            background: "none",
                            border: "none",
                            cursor: "pointer",
                            padding: 0,
                            display: "inline-flex",
                            color: "inherit",
                          }}
                        >
                          <Icons.X size={12} aria-hidden />
                        </button>
                      </span>
                    ))
                  )}
                </div>

                {nonMembers.length > 0 && (
                  <div style={{ display: "flex", gap: 6 }}>
                    <select
                      value={addMemberSel[c.id] || ""}
                      onChange={(e) => setAddMemberSel((prev) => ({ ...prev, [c.id]: e.target.value }))}
                      style={{ flex: 1 }}
                      aria-label="Select merchant to add"
                    >
                      <option value="">Add merchant…</option>
                      {nonMembers.map((m) => (
                        <option key={m.id} value={m.id}>
                          {m.name}
                        </option>
                      ))}
                    </select>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => addMember(c)}
                      disabled={!addMemberSel[c.id]}
                      style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
                    >
                      <Icons.Plus size={14} aria-hidden /> Add
                    </button>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
