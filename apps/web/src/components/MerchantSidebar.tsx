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
import {
  ChevronLeft, ChevronRight, ChevronDown, ArrowLeft, Store, LogOut,
} from "lucide-react";
import {
  NAV, NAV_SECTIONS, isNavItemVisible,
  type NavItem, type ActiveKey, type NavModuleSet,
} from "@/lib/merchantNav";

const BY_KEY = Object.fromEntries(NAV.map((i) => [i.key, i])) as Record<string, NavItem>;

const COLLAPSE_KEY = "fbgroup_sidebar_collapsed";
const SECTIONS_KEY = "fbgroup_sidebar_closed_sections";

export default function MerchantSidebar({
  active = null,
  children,
}: {
  active?: ActiveKey | null;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [operator, setOperator] = useState<OperatorMerchant | null>(null);
  const [perms, setPerms] = useState<Set<string> | null>(null);
  const [isSuper, setIsSuper] = useState(false);
  const [pipelineEnabled, setPipelineEnabled] = useState(true);
  const [modules, setModules] = useState<NavModuleSet>({ engagement: true, table_qr: true, pos: true });
  const [collapsed, setCollapsed] = useState(false);
  const [closed, setClosed] = useState<Set<string>>(new Set());

  // Restore the collapse prefs (client-only → set after mount to avoid a hydration mismatch).
  useEffect(() => {
    setCollapsed(localStorage.getItem(COLLAPSE_KEY) === "1");
    try {
      const raw = localStorage.getItem(SECTIONS_KEY);
      if (raw) setClosed(new Set(JSON.parse(raw) as string[]));
    } catch { /* ignore */ }
  }, []);

  function toggleCollapsed() {
    setCollapsed((c) => {
      const next = !c;
      localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
      return next;
    });
  }
  function toggleSection(title: string) {
    setClosed((prev) => {
      const next = new Set(prev);
      if (next.has(title)) next.delete(title); else next.add(title);
      localStorage.setItem(SECTIONS_KEY, JSON.stringify(Array.from(next)));
      return next;
    });
  }

  useEffect(() => {
    const sync = () => setOperator(getOperatorMerchant());
    sync();
    window.addEventListener("fbgroup:operator-changed", sync);
    return () => window.removeEventListener("fbgroup:operator-changed", sync);
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
      // Fetch permissions + nav flags INDEPENDENTLY: at platform scope (operator, no merchant) the
      // nav-flags call has no merchant_id and may 400 — that must NOT swallow the permissions result
      // (which is what tells us the user is a platform operator → show "← Platform Console").
      getMyPermissions(getApiBase(), t, mid)
        .then((caps) => {
          if (cancelled) return;
          setPerms(new Set(caps.permissions));
          setIsSuper(caps.is_super_admin);
        })
        .catch(() => { /* perms unknown → sensitive nav stays hidden */ });
      getNavFlags(getApiBase(), t, mid, getOperatorMerchant()?.nodeId)
        .then((flags) => {
          if (cancelled) return;
          setPipelineEnabled(flags.pipeline_enabled);
          setModules({ engagement: flags.rewards_enabled, table_qr: flags.qr_ordering_enabled, pos: flags.pos_enabled });
        })
        .catch(() => { /* keep modules shown by default */ });
    }
    refresh();
    window.addEventListener("fbgroup:settings-changed", refresh);
    return () => {
      cancelled = true;
      window.removeEventListener("fbgroup:settings-changed", refresh);
    };
  }, []);

  // "Scoped" = drilled into a specific node (a storefront, or a sub-chain narrower than the tenant).
  const storefrontMode = !!operator && (!!operator.outletId || (!!operator.nodeId && operator.nodeId !== operator.id));
  const scopeLabel = operator?.outletName || operator?.nodeName || "";
  // A platform operator can ALWAYS return to the Platform Console — even at platform scope (no merchant
  // entered, e.g. after the platform "Reports" button cleared the context). Keyed off caps, not context.
  const isOperator = isSuper || (perms?.has("platform.merchants.view") ?? false);

  function navVisible(item: NavItem): boolean {
    return isNavItemVisible(item, { modules, pipelineEnabled, perms, isSuper });
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
  function backToGroup() {
    const op = getOperatorMerchant();
    if (op) {
      setOperatorMerchant({ id: op.id, name: op.name });
      setOperator({ id: op.id, name: op.name });
    }
    router.push("/merchant/crm");
  }

  // Self-healing auth: install the 401 → refresh → retry handler; on a failed refresh, go to login.
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

  // A nav row (link or button) — icon always; label only when expanded; title = tooltip when collapsed.
  const rowStyle: React.CSSProperties = {
    background: "none", border: "none", width: "100%", cursor: "pointer",
    justifyContent: collapsed ? "center" : "flex-start",
  };
  function Row({ item }: { item: NavItem }) {
    const Icon = item.icon;
    return (
      <a
        className={`sidebar-link ${active === item.key ? "active" : ""}`}
        href={item.href}
        title={collapsed ? item.label : undefined}
        style={{ justifyContent: collapsed ? "center" : "flex-start" }}
      >
        <Icon size={18} />
        {!collapsed && <span>{item.label}</span>}
      </a>
    );
  }

  return (
    <div className="sidebar-layout">
      <nav className={`sidebar ${collapsed ? "collapsed" : ""}`}>
        <div className="sidebar-logo" style={{ display: "flex", alignItems: "center", justifyContent: collapsed ? "center" : "space-between", gap: 8 }}>
          {!collapsed && <span>FB Group</span>}
          <button
            onClick={toggleCollapsed}
            title={collapsed ? "Expand" : "Collapse"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            style={{ background: "none", border: "none", color: "rgba(255,255,255,0.7)", cursor: "pointer", display: "flex", padding: 2 }}
          >
            {collapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          </button>
        </div>

        <div className="sidebar-nav">
          {/* Context jumps */}
          {(operator || isOperator) && (
            <button className="sidebar-link" onClick={backToOperator} title={collapsed ? "Platform Console" : undefined} style={rowStyle}>
              <ArrowLeft size={18} />{!collapsed && <span>Platform Console</span>}
            </button>
          )}
          {storefrontMode && (
            <button className="sidebar-link" onClick={backToGroup} title={collapsed ? "Back to group" : undefined} style={rowStyle}>
              <ArrowLeft size={18} />{!collapsed && <span>Back to group</span>}
            </button>
          )}

          {/* Grouped, collapsible sections */}
          {NAV_SECTIONS.map((section) => {
            const items = section.keys.map((k) => BY_KEY[k as string]).filter((i) => i && navVisible(i));
            if (items.length === 0) return null;
            const isClosed = !collapsed && closed.has(section.title);
            return (
              <div key={section.title} style={{ marginTop: 8 }}>
                {collapsed ? (
                  <div style={{ height: 1, background: "rgba(255,255,255,0.1)", margin: "8px 6px" }} />
                ) : (
                  <button className="sidebar-section-title" onClick={() => toggleSection(section.title)}>
                    <span>{section.title}</span>
                    <ChevronDown size={14} style={{ transform: isClosed ? "rotate(-90deg)" : "none", transition: "transform 0.15s" }} />
                  </button>
                )}
                {!isClosed && items.map((item) => <Row key={item.key} item={item} />)}
              </div>
            );
          })}

          {!operator && !isOperator && (
            <a className="sidebar-link" href="/" title={collapsed ? "Customer Demo" : undefined} style={{ marginTop: 8, justifyContent: collapsed ? "center" : "flex-start" }}>
              <Store size={18} />{!collapsed && <span>Customer Demo</span>}
            </a>
          )}
        </div>

        <div className="sidebar-footer">
          <button
            onClick={logout}
            title={collapsed ? "Logout" : undefined}
            style={{ background: "none", border: "none", color: "rgba(255,255,255,0.5)", cursor: "pointer", fontSize: 13, padding: 0, display: "flex", alignItems: "center", gap: 8, justifyContent: collapsed ? "center" : "flex-start", width: "100%" }}
          >
            <LogOut size={16} />{!collapsed && <span>Logout</span>}
          </button>
        </div>
      </nav>

      <main className="main-content">
        {operator ? (
          <div style={bannerStyle}>
            <span>
              🛰️ <strong>Operator view</strong> —{" "}
              {storefrontMode ? (
                <>{operator.outletId ? "storefront" : "chain"} <strong>{scopeLabel}</strong> · {operator.name}</>
              ) : (
                <>viewing merchant <strong>{operator.name}</strong></>
              )}
            </span>
            <button onClick={storefrontMode ? backToGroup : backToOperator} style={bannerBtnStyle}>
              {storefrontMode ? "← Back to group" : "← Back to Platform Console"}
            </button>
          </div>
        ) : isOperator ? (
          <div style={bannerStyle}>
            <span>🛰️ <strong>Platform view</strong> — no merchant selected</span>
            <button onClick={backToOperator} style={bannerBtnStyle}>← Back to Platform Console</button>
          </div>
        ) : null}
        {children}
      </main>
    </div>
  );
}

const bannerStyle: React.CSSProperties = {
  background: "#fef3c7", border: "1px solid #fcd34d", borderRadius: 8, padding: "10px 16px",
  marginBottom: 20, display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 14,
};
const bannerBtnStyle: React.CSSProperties = {
  background: "#fff", border: "1px solid #d97706", color: "#b45309", borderRadius: 6,
  padding: "5px 12px", cursor: "pointer", fontSize: 13, fontWeight: 600,
};
