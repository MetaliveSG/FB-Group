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
  platformMyPermissions,
  orgTree,
  createOrgNode,
  updateOrgNode,
  listVenueLeases,
  getApiBase,
  installAuthHandler,
  AUTH_LOGOUT_EVENT,
} from "@/lib/api";
import {
  getStaffToken,
  clearStaffToken,
  setOperatorMerchant,
  clearOperatorMerchant,
} from "@/lib/auth";
import { formatSGD } from "@/lib/format";
import NodeDetailDrawer from "@/components/NodeDetailDrawer";
import { Toggle, Icons } from "@/components/ui";
import {
  OPERATOR_ROLE_LABELS,
  type PlatformOverview,
  type MerchantKpi,
  type Coalition,
  type Operator,
  type OperatorRole,
  type PlatformCapabilities,
  type OrgTreeNode,
  type Lease,
} from "@fbgroup/api-client";

const OPERATOR_ROLE_OPTIONS: { value: OperatorRole; label: string; hint: string }[] = [
  { value: "platform_admin", label: "Admin", hint: "Merchants + coalitions + drill-in (no operator mgmt)" },
  { value: "platform_onboarder", label: "Onboarding", hint: "Onboard/edit merchants only" },
  { value: "platform_support", label: "Support", hint: "Read-only (overview, merchants, read drill-in)" },
  { value: "super_admin", label: "Owner", hint: "Full access, incl. managing operators" },
];

// The three adoption module flags, in display order.
const MODULE_FLAGS: { key: string; label: string }[] = [
  { key: "rewards_enabled", label: "Rewards" },
  { key: "qr_ordering_enabled", label: "QR Ordering" },
  { key: "pos_enabled", label: "POS" },
];

// Member-tree node display: colour per role + a coarse rank so a level lists Brands before
// Outlets before Stalls. Mirrors the merchant Org-Tree page.
const ROLE_STYLE: Record<string, { bg: string; fg: string }> = {
  CHAIN: { bg: "#dbeafe", fg: "#1e40af" },
  STOREFRONT: { bg: "#fef3c7", fg: "#92400e" },
};
const ROLE_RANK: Record<string, number> = { CHAIN: 0, STOREFRONT: 1 };
// Canonical Title-Case kind labels (consistent with the Manager/Cashier role chips).
// NOT exported — a Next.js page file rejects arbitrary named exports.
const KIND_LABEL: Record<string, string> = { CHAIN: "Chain", STOREFRONT: "Storefront" };

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
  const [tree, setTree] = useState<OrgTreeNode[]>([]);
  const [drill, setDrill] = useState<string[]>([]);  // member-tree path: node ids root→current
  const [detailId, setDetailId] = useState<string | null>(null);  // node whose detail drawer is open
  const [venueLeases, setVenueLeases] = useState<Lease[]>([]);     // stalls leased INTO the current node
  // Member-tree management (manage the tree right here in the directory; no separate Org-Tree page):
  const [manageId, setManageId] = useState<string | null>(null);   // node whose manage panel is open
  const [nodeBusy, setNodeBusy] = useState(false);
  const [nodeErr, setNodeErr] = useState<string | null>(null);
  const [feeVal, setFeeVal] = useState("");                        // subscription-fee input
  const [addKind, setAddKind] = useState("CHAIN");                 // add-child kind
  const [addName, setAddName] = useState("");
  const [addFee, setAddFee] = useState("");
  const [coalitions, setCoalitions] = useState<Coalition[]>([]);
  const [operators, setOperators] = useState<Operator[]>([]);
  const [caps, setCaps] = useState<PlatformCapabilities | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  // Onboard merchant form
  const [showForm, setShowForm] = useState(false);
  const [mName, setMName] = useState("");
  const [mEmail, setMEmail] = useState("");
  const [mPassword, setMPassword] = useState("");
  const [mOwnerName, setMOwnerName] = useState("");
  const [mKind, setMKind] = useState<"chain" | "storefront">("storefront");
  const [mFee, setMFee] = useState("");
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
  const [opRole, setOpRole] = useState<OperatorRole>("platform_admin");
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
      // Capabilities first — they decide which sections this operator may load/render.
      const c = await platformMyPermissions(base, tok);
      setCaps(c);
      const has = (p: string) => c.is_owner || c.permissions.includes(p);
      const [ov, ms, cs, tr] = await Promise.all([
        platformOverview(base, tok),
        platformMerchants(base, tok),
        platformCoalitions(base, tok),
        orgTree(base, tok).catch(() => ({ nodes: [], can_manage: false })),
      ]);
      setOverview(ov);
      setMerchants(ms);
      setCoalitions(cs);
      setTree(tr.nodes);
      // Operators list is Owner-only — only fetch it when allowed (else it 403s).
      setOperators(has("platform.operators.manage") ? await platformOperators(base, tok) : []);
    },
    [base]
  );

  useEffect(() => {
    installAuthHandler();
    function onLogout(e: Event) {
      const detail = (e as CustomEvent).detail as { actor?: string } | undefined;
      if (detail?.actor && detail.actor !== "staff") return;
      router.push("/platform/login");
    }
    window.addEventListener(AUTH_LOGOUT_EVENT, onLogout);

    const tok = getStaffToken();
    if (!tok) {
      router.push("/platform/login");
      return () => window.removeEventListener(AUTH_LOGOUT_EVENT, onLogout);
    }
    loadAll(tok)
      .then(() => setLoading(false))
      .catch((err: unknown) => {
        const msg = errMsg(err, "");
        if (errStatus(err) === 403 || msg.includes("403")) {
          // Not an operator — bounce to operator login (it explains why).
          clearStaffToken();
          router.push("/platform/login");
        } else {
          setError(msg || "Failed to load operator console");
          setLoading(false);
        }
      });

    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, onLogout);
  }, [loadAll, router]);

  // Enter any member-tree node's console. `merchantId`/`tenantName` = the tenant (merchant-scoped
  // pages: CRM, settings…). `nodeId` = the entered node → the outlet surfaces (Menu, Tables & QR)
  // scope to its subtree. `outletId` (Storefront only) locks those surfaces to its one outlet.
  function enterNode(a: { merchantId: string; tenantName: string; nodeId: string; nodeName: string;
                          outletId?: string | null; storefrontName?: string }) {
    setOperatorMerchant({
      id: a.merchantId, name: a.tenantName,
      nodeId: a.nodeId, nodeName: a.nodeName,
      outletId: a.outletId ?? undefined, outletName: a.outletId ? a.storefrontName : undefined,
    });
    // A scoped node (sub-chain or storefront) lands on the Menu so the scoping is visible; the bare
    // tenant lands on the CRM home.
    router.push(a.nodeId && a.nodeId !== a.merchantId ? "/merchant/menu" : "/merchant/crm");
  }

  // --- Member-tree management (add Chain/Storefront, edit fee, stop-chain) inline in the directory ---
  // Leased-in stalls under the node we're currently viewing (venue). Reloads on navigation and
  // when the detail drawer closes (the drawer is where leases are added/edited). Empty at root or
  // for a node with no tenancies; never throws (a non-venue / no-access node just returns []).
  useEffect(() => {
    const tok = getStaffToken();
    const currentId = drill.length ? drill[drill.length - 1] : null;
    if (!tok || !currentId) { setVenueLeases([]); return; }
    listVenueLeases(base, tok, currentId).then(setVenueLeases).catch(() => setVenueLeases([]));
  }, [drill, detailId, base]);

  async function reloadTree() {
    const tok = getStaffToken();
    if (tok) setTree((await orgTree(base, tok)).nodes);
  }
  function openManage(node: OrgTreeNode) {
    setManageId(manageId === node.id ? null : node.id);
    setFeeVal(node.subscription_fee ?? "");
    setAddKind(node.chain_stopped ? "STOREFRONT" : "CHAIN");
    setAddName("");
    setAddFee("");
    setNodeErr(null);
  }
  async function runNode(fn: () => Promise<unknown>) {
    setNodeBusy(true);
    setNodeErr(null);
    try {
      await fn();
      await reloadTree();
    } catch (err: unknown) {
      setNodeErr(errMsg(err, "Action failed"));
    } finally {
      setNodeBusy(false);
    }
  }
  async function saveFee(node: OrgTreeNode) {
    const tok = getStaffToken();
    if (!tok) return;
    await runNode(() => updateOrgNode(base, tok, node.id, { subscription_fee: feeVal.trim() || "0" }));
  }
  async function toggleStop(node: OrgTreeNode) {
    const tok = getStaffToken();
    if (!tok) return;
    await runNode(() => updateOrgNode(base, tok, node.id, { chain_stopped: !node.chain_stopped }));
  }
  async function addChild(parentId: string) {
    const tok = getStaffToken();
    if (!tok || !addName.trim()) return;
    await runNode(async () => {
      await createOrgNode(base, tok, {
        parent_id: parentId, role: addKind, name: addName.trim(),
        subscription_fee: addFee.trim() || undefined,
      });
      setAddName("");
      setAddFee("");
    });
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
        kind: mKind,
        subscription_fee: mFee.trim() || undefined,
      });
      setFormSuccess(`Created ${mKind} "${res.name}" with owner ${res.owner_email}.`);
      setMName("");
      setMEmail("");
      setMPassword("");
      setMOwnerName("");
      setMFee("");
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
        role: opRole,
      });
      setOpSuccess(`Added ${OPERATOR_ROLE_LABELS[op.role]} operator ${op.email}.`);
      setOpEmail("");
      setOpPassword("");
      setOpName("");
      setOpRole("platform_admin");
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
    router.push("/platform/login");
  }

  if (loading) {
    return (
      <div className="page-loading">
        <div className="spinner" /> Loading operator console…
      </div>
    );
  }

  const merchantName = (id: string) => merchants.find((m) => m.id === id)?.name || id;
  // Capability gate for console actions (server still enforces — this only prunes the UI).
  const can = (p: string) => !!caps && (caps.is_owner || caps.permissions.includes(p));
  const canOnboard = can("platform.merchants.onboard");
  const canSuspend = can("platform.merchants.suspend");
  const canDrillIn = can("platform.merchant.access");
  const canCoalitions = can("platform.coalitions.manage");
  const canOperators = can("platform.operators.manage");

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
          <h1 className="page-title">Platform Console</h1>
          <p className="page-subtitle">Platform overview across all merchants</p>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <button
            onClick={() => { clearOperatorMerchant(); router.push("/merchant/reports"); }}
            className="btn btn-primary btn-sm"
            title="Ecosystem-wide reports (defaults to Platform; drill into any node)"
          >
            📊 Reports
          </button>
          <button onClick={logout} className="btn btn-secondary btn-sm">
            Logout
          </button>
        </div>
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
        {canOnboard && (
          <button className="btn btn-primary btn-sm" onClick={() => setShowForm((s) => !s)}>
            {showForm ? "Cancel" : "+ Onboard Merchant"}
          </button>
        )}
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
              <div className="form-group">
                <label htmlFor="m-kind">Type</label>
                <select id="m-kind" value={mKind} onChange={(e) => setMKind(e.target.value as "chain" | "storefront")}>
                  <option value="storefront">Storefront</option>
                  <option value="chain">Chain</option>
                </select>
                <span style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 4 }}>
                  Chain nests other locations; Storefront is a single selling location.
                </span>
              </div>
              <div className="form-group">
                <label htmlFor="m-fee">Subscription Fee</label>
                <input
                  id="m-fee"
                  type="number"
                  min={0}
                  step="0.01"
                  value={mFee}
                  onChange={(e) => setMFee(e.target.value)}
                  placeholder="S$/mo (optional)"
                />
              </div>
            </div>
            <button type="submit" className="btn btn-primary" disabled={creating}>
              {creating ? "Creating…" : `Create ${mKind === "storefront" ? "Storefront" : "Chain"}`}
            </button>
          </form>
        </div>
      )}

      {(() => {
        // Member-tree drill-down: zoom from the roots (enterprises + standalone merchants) DOWN
        // the org spine — Chain → … → Storefront. Tenant Chains (settlement boundaries) carry the
        // live KPIs + suspend/edit; a Storefront gets the Enter button (the operating unit). Chains
        // are structure you zoom into. Same member-tree the merchant Org-Tree page shows.
        const present = new Set(tree.map((n) => n.id));
        const byId = new Map(tree.map((n) => [n.id, n]));
        const kpiById = new Map(merchants.map((m) => [m.id, m]));
        const childrenOf = (pid: string | null) =>
          tree
            .filter((n) => (pid === null ? !n.parent_id || !present.has(n.parent_id) : n.parent_id === pid))
            .sort(
              (a, b) =>
                (ROLE_RANK[a.role] ?? 9) - (ROLE_RANK[b.role] ?? 9) ||
                (a.name || "").localeCompare(b.name || "")
            );
        const currentId = drill.length ? drill[drill.length - 1] : null;
        const level = childrenOf(currentId);
        // The tenant ("merchant") a node belongs to = nearest ancestor settlement boundary. A
        // Storefront is the operating unit you ENTER; entering drills into its tenant's console.
        const tenantOf = (node: OrgTreeNode): OrgTreeNode | undefined => {
          let cur: OrgTreeNode | undefined = node;
          while (cur) {
            if (cur.is_settlement_boundary) return cur;
            cur = cur.parent_id ? byId.get(cur.parent_id) : undefined;
          }
          return undefined;
        };
        const crumb = (active: boolean) => ({
          background: "none",
          border: "none",
          padding: 0,
          font: "inherit",
          cursor: "pointer",
          color: active ? "var(--color-text, #111)" : "#ea580c",
          fontWeight: active ? 700 : 500,
          textDecoration: active ? "none" : "underline",
        });
        // A "link / bridge" glyph (Lucide Link2) — signals a stall that lives in ANOTHER tree and
        // is merely leased in here (vs an owned child). Inline SVG so it tints to any token colour.
        const linkIcon = (
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"
               style={{ flexShrink: 0 }}>
            <path d="M9 17H7A5 5 0 0 1 7 7h2" /><path d="M15 7h2a5 5 0 1 1 0 10h-2" />
            <line x1="8" x2="16" y1="12" y2="12" />
          </svg>
        );
        return (
          <div className="card" style={{ marginBottom: 28 }}>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", marginBottom: 14, fontSize: 13 }}>
              <button onClick={() => setDrill([])} style={crumb(drill.length === 0)}>
                All merchants
              </button>
              {drill.map((id, i) => (
                <Fragment key={id}>
                  <span style={{ color: "var(--color-text-muted)" }}>›</span>
                  <button onClick={() => setDrill(drill.slice(0, i + 1))} style={crumb(i === drill.length - 1)}>
                    {byId.get(id)?.name || id}
                  </button>
                </Fragment>
              ))}
            </div>

            {tree.length === 0 ? (
              <p style={{ color: "var(--color-text-muted)" }}>No merchants yet.</p>
            ) : level.length === 0 && venueLeases.length === 0 ? (
              <p style={{ color: "var(--color-text-muted)" }}>Nothing under this node.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {level.map((n) => {
                  const kids = childrenOf(n.id);
                  const kpi = kpiById.get(n.id);
                  const rs = ROLE_STYLE[n.role] ?? { bg: "#f1f5f9", fg: "#334155" };
                  return (
                    <div
                      key={n.id}
                      style={{
                        border: "1px solid var(--color-border, #e5e7eb)",
                        borderRadius: 10,
                        padding: "10px 12px",
                        opacity: n.is_active ? 1 : 0.55,
                        display: "flex",
                        alignItems: "center",
                        gap: 12,
                        flexWrap: "wrap",
                      }}
                    >
                      <span className="badge" style={{ background: rs.bg, color: rs.fg, fontSize: 11, fontWeight: 700 }}>
                        {KIND_LABEL[n.role] ?? n.role}
                      </span>
                      <button
                        onClick={() => (kids.length ? setDrill([...drill, n.id]) : setDetailId(n.id))}
                        style={{ background: "none", border: "none", padding: 0, font: "inherit", fontWeight: 600, cursor: "pointer", color: "inherit", textAlign: "left" }}
                      >
                        {n.name || "(unnamed)"}
                        {kids.length > 0 && (
                          <span style={{ color: "var(--color-text-muted)", fontWeight: 400, fontSize: 12 }}> · {kids.length} inside ›</span>
                        )}
                      </button>
                      <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                        {n.qr_path && (
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: "4px 12px", fontWeight: 600 }}
                            onClick={() => window.open(n.qr_path!, "_blank", "width=430,height=900,noopener,noreferrer")}
                            title={n.sells ? "Open this stall's QR menu (new window)" : "Open this group's stalls (new window)"}
                          >
                            QR Menu
                          </button>
                        )}
                        <button
                          className="btn btn-primary btn-sm"
                          style={{ padding: "4px 14px", fontWeight: 700 }}
                          onClick={() => {
                            const t = tenantOf(n);
                            if (t) enterNode({ merchantId: t.id, tenantName: t.name || "", nodeId: n.id,
                                               nodeName: n.name || "",
                                               outletId: n.sells ? n.outlet_id : undefined,
                                               storefrontName: n.sells ? (n.name || "") : undefined });
                          }}
                          title={n.sells ? "Enter this storefront (menu · tables & QR)" : "Enter this chain's console (scoped to its subtree)"}
                        >
                          Enter
                        </button>
                        {n.is_settlement_boundary && kpi && (
                          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{formatSGD(kpi.revenue)}</span>
                        )}
                        {!n.is_active && (
                          <span className="badge" style={{ background: "#fee2e2", color: "#991b1b", fontSize: 10 }}>Suspended</span>
                        )}
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ padding: "4px 10px", fontWeight: 700 }}
                          onClick={() => setDetailId(n.id)}
                          title="Details & manage"
                          aria-label="Details"
                        >
                          ⋯
                        </button>
                      </div>
                    </div>
                  );
                })}

                {/* Leased-in stalls: independent tenants (own businesses, another tree) renting
                    space at THIS venue. Deliberately distinct from owned stalls above — dashed
                    violet rail + "Tenant" badge + link glyph + rent terms — so an operator never
                    confuses "I own this" with "this rents from me". */}
                {venueLeases.length > 0 && (
                  <>
                    <div style={{ display: "flex", alignItems: "center", gap: 7, margin: "10px 2px 2px",
                                  fontSize: 11, fontWeight: 700, letterSpacing: 0.4, textTransform: "uppercase", color: "#7c3aed" }}>
                      <span style={{ display: "inline-flex" }}>{linkIcon}</span>
                      Leased-in stalls ({venueLeases.length})
                      <span style={{ fontWeight: 500, letterSpacing: 0, textTransform: "none", color: "var(--color-text-muted)" }}>
                        · independent tenants renting space here
                      </span>
                    </div>
                    {venueLeases.map((l) => {
                      const isGto = l.rent_type === "GTO";
                      return (
                        <div
                          key={l.id}
                          style={{
                            border: "1px solid #ede9fe",
                            borderLeft: "3px dashed #a78bfa",
                            background: "#faf5ff",
                            borderRadius: 10,
                            padding: "10px 12px",
                            display: "flex",
                            alignItems: "center",
                            gap: 12,
                            flexWrap: "wrap",
                          }}
                        >
                          <span className="badge" style={{ background: "#ede9fe", color: "#6d28d9", fontSize: 11,
                                  fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 4 }}>
                            {linkIcon} Tenant
                          </span>
                          <span style={{ fontWeight: 600 }}>{l.tenant_name || l.tenant_node_id}</span>
                          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>· leases space (own business)</span>
                          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
                            <span className="badge" style={{ background: isGto ? "#fef3c7" : "#f1f5f9",
                                    color: isGto ? "#92400e" : "#475569", fontSize: 11, fontWeight: 700 }}>
                              {isGto ? `GTO · ${Number(l.rate)}%` : `FIXED · ${formatSGD(Number(l.rate))}/mo`}
                            </span>
                            <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
                              {isGto ? "you see turnover" : "sales private"}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </>
                )}
              </div>
            )}
          </div>
        );
      })()}

      {detailId && (() => {
        const node = tree.find((n) => n.id === detailId);
        if (!node) return null;
        return (
          <NodeDetailDrawer
            node={node}
            nodes={tree}
            kpi={merchants.find((m) => m.id === node.id)}
            canManage={node.can_manage}
            onClose={() => setDetailId(null)}
            onChanged={reloadTree}
            onEnter={enterNode}
            onOpen={() => { setDrill([...drill, node.id]); setDetailId(null); }}
          />
        );
      })()}


      {/* Platform operators — Owner-only (manage other operators' access + roles) */}
      {canOperators && (
        <>
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
        Operators are platform logins. Each holds a role that scopes what they can do;
        only an <strong>Owner</strong> can add or remove operators.
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
              <div className="form-group">
                <label htmlFor="op-role">Role</label>
                <select
                  id="op-role"
                  value={opRole}
                  onChange={(e) => setOpRole(e.target.value as OperatorRole)}
                >
                  {OPERATOR_ROLE_OPTIONS.map((r) => (
                    <option key={r.value} value={r.value}>
                      {r.label}
                    </option>
                  ))}
                </select>
                <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>
                  {OPERATOR_ROLE_OPTIONS.find((r) => r.value === opRole)?.hint}
                </span>
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
              <th>Role</th>
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
                      background: op.role === "super_admin" ? "#fef3c7" : "#eef2ff",
                      color: op.role === "super_admin" ? "#92400e" : "#4338ca",
                    }}
                  >
                    {OPERATOR_ROLE_LABELS[op.role]}
                  </span>
                </td>
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
        </>
      )}

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
        {canCoalitions && (
          <button className="btn btn-primary btn-sm" onClick={() => setShowCoaForm((s) => !s)}>
            {showCoaForm ? "Cancel" : "+ New Coalition"}
          </button>
        )}
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
                  {canCoalitions && (
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
                  )}
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
                  {canCoalitions && (
                    <Toggle
                      on={c.is_active}
                      onChange={() => toggleCoalitionActive(c)}
                      label={c.is_active ? "Deactivate coalition" : "Activate coalition"}
                    />
                  )}
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
                        {canCoalitions && (
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
                        )}
                      </span>
                    ))
                  )}
                </div>

                {canCoalitions && nonMembers.length > 0 && (
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
