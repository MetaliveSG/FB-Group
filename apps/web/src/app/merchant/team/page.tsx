"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { listUsers, inviteUser, revokeAssignment, menuOutlets, getApiBase } from "@/lib/api";
import { getStaffToken, clearStaffToken, getOperatorMerchant } from "@/lib/auth";
import MerchantSidebar from "@/components/MerchantSidebar";
import NodeDirectory from "@/components/NodeDirectory";
import { useScope } from "@/lib/useScope";
import { Icons } from "@/components/ui";
import {
  STAFF_ROLES,
  type AdminUser,
  type MenuAdminOutlet,
  type StaffRole,
  type ScopeType,
} from "@fbgroup/api-client";

const ROLE_LABELS: Record<StaffRole, string> = {
  merchant_owner: "Merchant Owner",
  brand_manager: "Brand Manager",
  outlet_manager: "Outlet Manager",
  staff: "Staff",
};

export default function TeamPage() {
  const router = useRouter();
  const base = getApiBase();

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [outlets, setOutlets] = useState<MenuAdminOutlet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);

  const { scope, isOperator, nodes, ready, enter } = useScope();
  const needPick = ready && isOperator && !!scope && scope.tenantId === null;

  // Invite form
  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<StaffRole>("staff");
  const [scopeKind, setScopeKind] = useState<"merchant" | "outlet">("merchant");
  const [outletId, setOutletId] = useState("");
  const [inviting, setInviting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(
    async (tok: string) => {
      const mid = getOperatorMerchant()?.id;
      const list = await listUsers(base, tok, mid);
      setUsers(list);
      // Outlets are used for outlet-scoped invites; non-fatal if it fails.
      const ots = await menuOutlets(base, tok, mid).catch(() => [] as MenuAdminOutlet[]);
      setOutlets(ots);
      if (ots.length > 0 && !outletId) setOutletId(ots[0].outlet_id);
    },
    [base, outletId]
  );

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) {
      router.push("/merchant/login");
      return;
    }
    if (!ready || needPick) return;
    load(tok)
      .then(() => setLoading(false))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "";
        const status =
          err && typeof err === "object" && "status" in err
            ? (err as { status?: number }).status
            : undefined;
        if (msg.includes("401")) {
          clearStaffToken();
          router.push("/merchant/login");
        } else if (status === 403 || msg.includes("403")) {
          setForbidden(true);
          setLoading(false);
        } else {
          setError(msg || "Failed to load users");
          setLoading(false);
        }
      });
  }, [load, router, ready, needPick]);

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password) return;
    const tok = getStaffToken();
    if (!tok) return;
    setInviting(true);
    setFormError(null);
    const mid = getOperatorMerchant()?.id;
    const scope_type: ScopeType = scopeKind;
    const scope_id =
      scopeKind === "outlet" ? outletId : mid; // merchant scope → merchant id (or default)
    try {
      await inviteUser(
        base,
        tok,
        {
          email: email.trim(),
          password,
          full_name: fullName.trim(),
          role,
          scope_type,
          scope_id: scope_id || undefined,
        },
        mid
      );
      setEmail("");
      setPassword("");
      setFullName("");
      setRole("staff");
      setScopeKind("merchant");
      setShowForm(false);
      await load(tok);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to invite user";
      const status =
        err && typeof err === "object" && "status" in err
          ? (err as { status?: number }).status
          : undefined;
      if (status === 409 || msg.includes("409") || msg.toLowerCase().includes("exist")) {
        setFormError("That email is already taken.");
      } else {
        setFormError(msg);
      }
    } finally {
      setInviting(false);
    }
  }

  async function handleRevoke(assignmentId: string) {
    const tok = getStaffToken();
    if (!tok) return;
    try {
      await revokeAssignment(base, tok, assignmentId, getOperatorMerchant()?.id);
      await load(tok);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to revoke assignment");
    }
  }

  function scopeLabel(scopeType: string, scopeId: string | null): string {
    if (scopeType === "outlet") {
      const o = outlets.find((x) => x.outlet_id === scopeId);
      return `outlet: ${o?.name ?? scopeId ?? "?"}`;
    }
    return scopeType;
  }

  if (needPick) {
    return (
      <MerchantSidebar active="team">
        <NodeDirectory feature="Team" nodes={nodes} currentNodeId={scope!.currentNodeId} onEnter={enter} />
      </MerchantSidebar>
    );
  }

  return (
    <MerchantSidebar active="team">
      <div
        className="page-header"
        style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}
      >
        <div>
          <h1 className="page-title">Team</h1>
          <p className="page-subtitle">Users &amp; role assignments</p>
        </div>
        {!forbidden && (
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Cancel" : "Invite user"}
          </button>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="page-loading">
          <div className="spinner" /> Loading team…
        </div>
      ) : forbidden ? (
        <div className="card">
          <p style={{ margin: 0 }}>
            User management requires the <strong>merchant owner</strong> role.
          </p>
        </div>
      ) : (
        <>
          {showForm && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="card-title" style={{ marginBottom: 12 }}>
                Invite User
              </div>
              {formError && <div className="alert alert-error">{formError}</div>}
              <form onSubmit={handleInvite} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    style={{ flex: 1, minWidth: 180 }}
                  />
                  <input
                    type="text"
                    placeholder="Full name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    style={{ flex: 1, minWidth: 160 }}
                  />
                </div>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <input
                    type="password"
                    placeholder="Password (min 8)"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    style={{ flex: 1, minWidth: 160 }}
                  />
                  <select value={role} onChange={(e) => setRole(e.target.value as StaffRole)} style={{ flex: 1, minWidth: 150 }}>
                    {STAFF_ROLES.map((r) => (
                      <option key={r} value={r}>
                        {ROLE_LABELS[r]}
                      </option>
                    ))}
                  </select>
                </div>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
                  <select
                    value={scopeKind}
                    onChange={(e) => setScopeKind(e.target.value as "merchant" | "outlet")}
                    style={{ flex: 1, minWidth: 150 }}
                  >
                    <option value="merchant">Whole merchant</option>
                    <option value="outlet">Single outlet</option>
                  </select>
                  {scopeKind === "outlet" && (
                    <select value={outletId} onChange={(e) => setOutletId(e.target.value)} style={{ flex: 1, minWidth: 180 }}>
                      {outlets.map((o) => (
                        <option key={o.outlet_id} value={o.outlet_id}>
                          {o.name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>
                <button type="submit" className="btn btn-primary btn-sm" disabled={inviting}>
                  {inviting ? "Inviting…" : "Create user"}
                </button>
              </form>
            </div>
          )}

          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div className="table-wrapper" style={{ border: "none" }}>
              <table>
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Status</th>
                    <th>Roles</th>
                  </tr>
                </thead>
                <tbody>
                  {users.length === 0 ? (
                    <tr>
                      <td colSpan={3} style={{ textAlign: "center", color: "var(--color-text-muted)", padding: 24 }}>
                        No users
                      </td>
                    </tr>
                  ) : (
                    users.map((u) => (
                      <tr key={u.id}>
                        <td>
                          <div style={{ fontWeight: 600 }}>{u.full_name || "—"}</div>
                          <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{u.email}</div>
                        </td>
                        <td>
                          <span
                            className="badge"
                            style={{
                              background: u.is_active ? "#dcfce7" : "#fee2e2",
                              color: u.is_active ? "#166534" : "#991b1b",
                            }}
                          >
                            {u.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td>
                          {u.roles.length === 0 ? (
                            <span style={{ color: "var(--color-text-muted)" }}>—</span>
                          ) : (
                            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                              {u.roles.map((r) => (
                                <div key={r.assignment_id} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                                  <span className="badge" style={{ background: "#eef2ff", color: "#4338ca" }}>
                                    {ROLE_LABELS[r.role as StaffRole] ?? r.role}
                                  </span>
                                  <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                                    {scopeLabel(r.scope_type, r.scope_id)}
                                  </span>
                                  <button
                                    className="btn btn-secondary btn-sm"
                                    style={{ padding: "2px 8px", fontSize: 12, display: "inline-flex", alignItems: "center" }}
                                    onClick={() => handleRevoke(r.assignment_id)}
                                    title="Revoke access"
                                    aria-label="Revoke access"
                                  >
                                    <Icons.Trash2 size={14} aria-hidden />
                                  </button>
                                </div>
                              ))}
                            </div>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </MerchantSidebar>
  );
}
