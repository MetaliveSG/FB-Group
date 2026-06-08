"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { listNodeAccounts, createNodeAccount, revokeNodeAccount, getApiBase } from "@/lib/api";
import { getStaffToken, clearStaffToken } from "@/lib/auth";
import MerchantSidebar from "@/components/MerchantSidebar";
import NodeDirectory from "@/components/NodeDirectory";
import { useScope } from "@/lib/useScope";
import { Icons } from "@/components/ui";
import type { OrgNodeAccount } from "@fbgroup/api-client";

// The merchant Team page runs on the member-tree NODE model (one role vocab everywhere): a web login
// is assigned at a node and its authority cascades over that node's subtree. Web palette only —
// POS operators (cashier/supervisor) are PIN-only and live in Settings → Staff & PINs.
const ROLES = ["manager", "viewer", "finance"] as const;
const ROLE_LABELS: Record<string, string> = { manager: "Manager", viewer: "Viewer", finance: "Finance" };
const ROLE_HINTS: Record<string, string> = {
  manager: "full control of this node's subtree (org · menu · staff · orders · reports)",
  viewer: "read-only — view everything in scope EXCEPT reports",
  finance: "read-only — reports only",
};

export default function TeamPage() {
  const router = useRouter();
  const base = getApiBase();

  const { scope, isOperator, nodes, ready, enter } = useScope();
  const needPick = ready && isOperator && !!scope && scope.tenantId === null;
  const rootNodeId = scope?.currentNodeId ?? null;

  const [accounts, setAccounts] = useState<OrgNodeAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [forbidden, setForbidden] = useState(false);

  // Add-login form
  const [showForm, setShowForm] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<string>("viewer");
  const [nodeId, setNodeId] = useState("");
  const [inviting, setInviting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(
    async (tok: string, rid: string) => {
      const list = await listNodeAccounts(base, tok, rid, true); // subtree = all web logins in scope
      setAccounts(list);
    },
    [base]
  );

  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) { router.push("/merchant/login"); return; }
    if (!ready || needPick) return;
    if (!rootNodeId) { setLoading(false); return; }
    setNodeId((cur) => cur || rootNodeId);
    load(tok, rootNodeId)
      .then(() => setLoading(false))
      .catch((err: unknown) => {
        const msg = err instanceof Error ? err.message : "";
        const status =
          err && typeof err === "object" && "status" in err ? (err as { status?: number }).status : undefined;
        if (msg.includes("401")) { clearStaffToken(); router.push("/merchant/login"); }
        else if (status === 403 || msg.includes("403")) { setForbidden(true); setLoading(false); }
        else { setError(msg || "Failed to load team"); setLoading(false); }
      });
  }, [load, router, ready, needPick, rootNodeId]);

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !password || !nodeId) return;
    const tok = getStaffToken();
    if (!tok) return;
    setInviting(true);
    setFormError(null);
    try {
      await createNodeAccount(base, tok, nodeId, {
        email: email.trim(), password, full_name: fullName.trim(), role,
      });
      setEmail(""); setPassword(""); setFullName(""); setRole("viewer");
      setShowForm(false);
      if (rootNodeId) await load(tok, rootNodeId);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to add login";
      const status =
        err && typeof err === "object" && "status" in err ? (err as { status?: number }).status : undefined;
      if (status === 409 || msg.includes("409") || msg.toLowerCase().includes("exist")) {
        setFormError("That email is already taken.");
      } else { setFormError(msg); }
    } finally { setInviting(false); }
  }

  async function handleRevoke(a: OrgNodeAccount) {
    const tok = getStaffToken();
    if (!tok || !rootNodeId) return;
    try {
      await revokeNodeAccount(base, tok, a.node_id ?? rootNodeId, a.assignment_id);
      await load(tok, rootNodeId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to revoke access");
    }
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
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 className="page-title">Team</h1>
          <p className="page-subtitle">Web logins &amp; role assignments — Manager · Viewer · Finance, scoped to a node</p>
        </div>
        {!forbidden && (
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Cancel" : "Add login"}
          </button>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div className="page-loading"><div className="spinner" /> Loading team…</div>
      ) : forbidden ? (
        <div className="card">
          <p style={{ margin: 0 }}>Managing logins requires the <strong>Manager</strong> role at this node.</p>
        </div>
      ) : (
        <>
          {showForm && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div className="card-title" style={{ marginBottom: 12 }}>Add a web login</div>
              {formError && <div className="alert alert-error">{formError}</div>}
              <form onSubmit={handleInvite} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} style={{ flex: 1, minWidth: 180 }} />
                  <input type="text" placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} style={{ flex: 1, minWidth: 160 }} />
                </div>
                <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                  <input type="password" placeholder="Password (min 8)" value={password} onChange={(e) => setPassword(e.target.value)} style={{ flex: 1, minWidth: 160 }} />
                  <select value={role} onChange={(e) => setRole(e.target.value)} style={{ flex: 1, minWidth: 150 }}>
                    {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
                  </select>
                </div>
                <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{ROLE_HINTS[role]}</div>
                <label style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Assign at node</label>
                <select value={nodeId} onChange={(e) => setNodeId(e.target.value)} style={{ minWidth: 220 }}>
                  {nodes.map((n) => (
                    <option key={n.id} value={n.id}>
                      {" ".repeat((n.depth ?? 0) * 2)}{n.name ?? n.id}
                    </option>
                  ))}
                </select>
                <button type="submit" className="btn btn-primary btn-sm" disabled={inviting}>
                  {inviting ? "Adding…" : "Create login"}
                </button>
              </form>
            </div>
          )}

          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <div className="table-wrapper" style={{ border: "none" }}>
              <table>
                <thead>
                  <tr><th>User</th><th>Status</th><th>Role</th><th>Scope (node)</th><th /></tr>
                </thead>
                <tbody>
                  {accounts.length === 0 ? (
                    <tr>
                      <td colSpan={5} style={{ textAlign: "center", color: "var(--color-text-muted)", padding: 24 }}>
                        No web logins yet
                      </td>
                    </tr>
                  ) : (
                    accounts.map((a) => (
                      <tr key={a.assignment_id}>
                        <td>
                          <div style={{ fontWeight: 600 }}>{a.full_name || "—"}</div>
                          <div style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{a.email}</div>
                        </td>
                        <td>
                          <span className="badge" style={{ background: a.is_active ? "#dcfce7" : "#fee2e2", color: a.is_active ? "#166534" : "#991b1b" }}>
                            {a.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td>
                          <span className="badge" style={{ background: "#eef2ff", color: "#4338ca" }}>
                            {ROLE_LABELS[a.role] ?? a.role}
                          </span>
                        </td>
                        <td style={{ fontSize: 13 }}>{a.node_name ?? a.node_id}</td>
                        <td>
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: "2px 8px", fontSize: 12, display: "inline-flex", alignItems: "center" }}
                            onClick={() => handleRevoke(a)}
                            title="Revoke access"
                            aria-label="Revoke access"
                          >
                            <Icons.Trash2 size={14} aria-hidden />
                          </button>
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
