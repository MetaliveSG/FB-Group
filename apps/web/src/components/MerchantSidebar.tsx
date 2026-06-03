"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  clearStaffToken,
  clearOperatorMerchant,
  getOperatorMerchant,
  setOperatorMerchant,
  getStaffToken,
  type OperatorMerchant,
} from "@/lib/auth";
import {
  installAuthHandler,
  AUTH_LOGOUT_EVENT,
  getNavFlags,
  getMyPermissions,
  getApiBase,
} from "@/lib/api";

type ActiveKey =
  | "crm"
  | "insights"
  | "orders"
  | "pipeline"
  | "campaigns"
  | "menu"
  | "tables"
  | "team"
  | "rfm"
  | "settings"
  | "tasks"
  | null;

// Declarative nav manifest — the single source of truth for the merchant sidebar.
// `perm` = permission the page's API requires (server still enforces; this only prunes the menu).
// `flag` = a merchant feature toggle that must be on. `sensitive` = owner-only; stays hidden
// until permissions load (don't flash a link a downline staffer can't use). Add a tab here = one line.
// `scope` = which console mode the item belongs to: "group" (tenant console — CRM, campaigns…),
// "storefront" (a single entered outlet — menu + tables/QR), or "both". Storefront mode shows ONLY
// storefront/both items; group mode shows everything except storefront-only ones.
type NavItem = {
  key: Exclude<ActiveKey, null>;
  label: string;
  href: string;
  perm?: string;
  flag?: "pipeline_enabled";
  sensitive?: boolean;
  scope?: "group" | "storefront" | "both";
};

const NAV: NavItem[] = [
  { key: "crm", label: "CRM & Analytics", href: "/merchant/crm", perm: "crm.view", scope: "group" },
  { key: "orders", label: "Orders", href: "/merchant/orders", perm: "order.view", scope: "group" },
  { key: "insights", label: "✨ AI Insights", href: "/merchant/insights", perm: "report.view", scope: "group" },
  { key: "pipeline", label: "Pipeline", href: "/merchant/pipeline", perm: "crm.view", flag: "pipeline_enabled", scope: "group" },
  { key: "campaigns", label: "Campaigns", href: "/merchant/campaigns", perm: "campaign.manage", scope: "group" },
  { key: "rfm", label: "RFM Analytics", href: "/merchant/rfm", perm: "report.view", scope: "group" },
  { key: "menu", label: "Menu Editor", href: "/merchant/menu", perm: "menu.manage", scope: "both" },
  { key: "tables", label: "Tables & QR", href: "/merchant/tables", perm: "outlet.manage", scope: "storefront" },
  { key: "team", label: "Team", href: "/merchant/team", perm: "user.manage", sensitive: true, scope: "group" },
  { key: "tasks", label: "My Tasks", href: "/merchant/tasks", perm: "crm.view", scope: "group" },
  { key: "settings", label: "Settings", href: "/merchant/settings", perm: "merchant.manage", sensitive: true, scope: "group" },
];

export default function MerchantSidebar({
  active = null,
  children,
}: {
  active?: ActiveKey;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [operator, setOperator] = useState<OperatorMerchant | null>(null);
  // Capabilities (null = not loaded yet) + feature flags drive which nav items render.
  const [perms, setPerms] = useState<Set<string> | null>(null);
  const [isSuper, setIsSuper] = useState(false);
  const [pipelineEnabled, setPipelineEnabled] = useState(true);

  useEffect(() => {
    setOperator(getOperatorMerchant());
  }, []);

  // Fetch the caller's permissions + feature flags to render the nav (the server still
  // enforces every route — this only hides links the user couldn't use anyway).
  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) return;
    let cancelled = false;
    function refresh() {
      const t = getStaffToken();
      if (!t) return;
      const mid = getOperatorMerchant()?.id;
      Promise.all([getMyPermissions(getApiBase(), t, mid), getNavFlags(getApiBase(), t, mid)])
        .then(([caps, flags]) => {
          if (cancelled) return;
          setPerms(new Set(caps.permissions));
          setIsSuper(caps.is_super_admin);
          setPipelineEnabled(flags.pipeline_enabled);
        })
        .catch(() => {
          /* keep defaults on error: perms unknown (sensitive nav stays hidden), pipeline shown */
        });
    }
    refresh();
    window.addEventListener("fbgroup:settings-changed", refresh);
    return () => {
      cancelled = true;
      window.removeEventListener("fbgroup:settings-changed", refresh);
    };
  }, []);

  // "Scoped" = drilled into a specific node (a storefront, or a sub-chain narrower than the tenant).
  // Entering the bare tenant (nodeId == merchant id, no outlet) is NOT scoped — that's the group home.
  const storefrontMode = !!operator && (!!operator.outletId || (!!operator.nodeId && operator.nodeId !== operator.id));
  const scopeLabel = operator?.outletName || operator?.nodeName || "";

  function navVisible(item: NavItem): boolean {
    // Full console nav in BOTH modes — entering a storefront only SCOPES Menu/Tables to that outlet
    // (and adds the context chip + "back to group"); it never hides the group tools (CRM, settings…).
    if (item.flag === "pipeline_enabled" && !pipelineEnabled) return false;
    if (!item.perm) return true;
    if (isSuper) return true;
    // Pre-load (perms unknown): show the broad tabs optimistically, but keep owner-only
    // (sensitive) tabs hidden so a downline staffer never sees a link they'd 403 on.
    if (perms === null) return !item.sensitive;
    return perms.has(item.perm);
  }

  function logout() {
    clearOperatorMerchant();
    clearStaffToken();
    router.push("/merchant/login");
  }

  function backToOperator() {
    clearOperatorMerchant();
    router.push("/platform");
  }

  // Leave the scoped view → the tenant/group console (same merchant, drop the node/outlet scope).
  function backToGroup() {
    const op = getOperatorMerchant();
    if (op) {
      setOperatorMerchant({ id: op.id, name: op.name });
      setOperator({ id: op.id, name: op.name });
    }
    router.push("/merchant/crm");
  }

  // Self-healing auth: install the 401 → refresh → retry handler, and on a
  // failed refresh (session cleared) redirect to login.
  useEffect(() => {
    installAuthHandler();
    function onLogout(e: Event) {
      const detail = (e as CustomEvent).detail as { actor?: string } | undefined;
      if (detail?.actor && detail.actor !== "staff") return;
      router.push(getOperatorMerchant() ? "/platform/login" : "/merchant/login");
    }
    window.addEventListener(AUTH_LOGOUT_EVENT, onLogout);
    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, onLogout);
  }, [router]);

  return (
    <div className="sidebar-layout">
      <nav className="sidebar">
        <div className="sidebar-logo">FB Group</div>
        <div className="sidebar-nav">
          {operator && (
            <button className="sidebar-link" onClick={backToOperator}
                    style={{ background: "none", border: "none", textAlign: "left", cursor: "pointer", width: "100%" }}>
              ← Platform Console
            </button>
          )}
          {storefrontMode && (
            <button className="sidebar-link" onClick={backToGroup}
                    style={{ background: "none", border: "none", textAlign: "left", cursor: "pointer", width: "100%" }}>
              ← Back to group
            </button>
          )}
          {NAV.filter(navVisible).map((item) => (
            <a
              key={item.key}
              className={`sidebar-link ${active === item.key ? "active" : ""}`}
              href={item.href}
            >
              {item.label}
            </a>
          ))}
          {!operator && (
            <a className="sidebar-link" href="/">
              ← Customer Demo
            </a>
          )}
        </div>
        <div className="sidebar-footer">
          <button
            onClick={logout}
            style={{
              background: "none",
              border: "none",
              color: "rgba(255,255,255,0.5)",
              cursor: "pointer",
              fontSize: 13,
              padding: 0,
            }}
          >
            Logout
          </button>
        </div>
      </nav>
      <main className="main-content">
        {operator && (
          <div
            style={{
              background: "#fef3c7",
              border: "1px solid #fcd34d",
              borderRadius: 8,
              padding: "10px 16px",
              marginBottom: 20,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: 14,
            }}
          >
            <span>
              🛰️ <strong>Operator view</strong> —{" "}
              {storefrontMode ? (
                <>{operator.outletId ? "storefront" : "chain"} <strong>{scopeLabel}</strong> · {operator.name}</>
              ) : (
                <>viewing merchant <strong>{operator.name}</strong></>
              )}
            </span>
            <button
              onClick={storefrontMode ? backToGroup : backToOperator}
              style={{
                background: "#fff",
                border: "1px solid #d97706",
                color: "#b45309",
                borderRadius: 6,
                padding: "5px 12px",
                cursor: "pointer",
                fontSize: 13,
                fontWeight: 600,
              }}
            >
              {storefrontMode ? "← Back to group" : "← Back to Platform Console"}
            </button>
          </div>
        )}
        {children}
      </main>
    </div>
  );
}
