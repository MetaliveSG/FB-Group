"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  clearStaffToken,
  clearOperatorMerchant,
  getOperatorMerchant,
  getStaffToken,
  type OperatorMerchant,
} from "@/lib/auth";
import { installAuthHandler, AUTH_LOGOUT_EVENT, getSettings, getApiBase } from "@/lib/api";

type ActiveKey =
  | "crm"
  | "insights"
  | "pipeline"
  | "campaigns"
  | "org"
  | "menu"
  | "team"
  | "rfm"
  | "settings"
  | "tasks"
  | null;

export default function MerchantSidebar({
  active = null,
  children,
}: {
  active?: ActiveKey;
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [operator, setOperator] = useState<OperatorMerchant | null>(null);
  // Default to showing Pipeline until settings load (avoids a flicker-hide).
  const [pipelineEnabled, setPipelineEnabled] = useState(true);

  useEffect(() => {
    setOperator(getOperatorMerchant());
  }, []);

  // Fetch merchant settings to decide whether the Pipeline nav link shows.
  useEffect(() => {
    const tok = getStaffToken();
    if (!tok) return;
    let cancelled = false;
    function refresh() {
      const t = getStaffToken();
      if (!t) return;
      getSettings(getApiBase(), t, getOperatorMerchant()?.id)
        .then((s) => {
          if (!cancelled) setPipelineEnabled(s.pipeline_enabled);
        })
        .catch(() => {
          /* keep default (shown) on error */
        });
    }
    refresh();
    window.addEventListener("fbgroup:settings-changed", refresh);
    return () => {
      cancelled = true;
      window.removeEventListener("fbgroup:settings-changed", refresh);
    };
  }, []);

  function logout() {
    clearOperatorMerchant();
    clearStaffToken();
    router.push("/merchant/login");
  }

  function backToOperator() {
    clearOperatorMerchant();
    router.push("/operator");
  }

  // Self-healing auth: install the 401 → refresh → retry handler, and on a
  // failed refresh (session cleared) redirect to login.
  useEffect(() => {
    installAuthHandler();
    function onLogout(e: Event) {
      const detail = (e as CustomEvent).detail as { actor?: string } | undefined;
      if (detail?.actor && detail.actor !== "staff") return;
      router.push(getOperatorMerchant() ? "/operator/login" : "/merchant/login");
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
              ← Operator Console
            </button>
          )}
          <a className={`sidebar-link ${active === "crm" ? "active" : ""}`} href="/merchant/crm">
            CRM &amp; Analytics
          </a>
          <a className={`sidebar-link ${active === "insights" ? "active" : ""}`} href="/merchant/insights">
            ✨ AI Insights
          </a>
          {pipelineEnabled && (
            <a
              className={`sidebar-link ${active === "pipeline" ? "active" : ""}`}
              href="/merchant/pipeline"
            >
              Pipeline
            </a>
          )}
          <a
            className={`sidebar-link ${active === "campaigns" ? "active" : ""}`}
            href="/merchant/campaigns"
          >
            Campaigns
          </a>
          <a
            className={`sidebar-link ${active === "rfm" ? "active" : ""}`}
            href="/merchant/rfm"
          >
            RFM Analytics
          </a>
          <a
            className={`sidebar-link ${active === "org" ? "active" : ""}`}
            href="/merchant/org"
          >
            Brands &amp; Outlets
          </a>
          <a
            className={`sidebar-link ${active === "menu" ? "active" : ""}`}
            href="/merchant/menu"
          >
            Menu Editor
          </a>
          <a
            className={`sidebar-link ${active === "team" ? "active" : ""}`}
            href="/merchant/team"
          >
            Team
          </a>
          <a
            className={`sidebar-link ${active === "tasks" ? "active" : ""}`}
            href="/merchant/tasks"
          >
            My Tasks
          </a>
          <a
            className={`sidebar-link ${active === "settings" ? "active" : ""}`}
            href="/merchant/settings"
          >
            Settings
          </a>
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
              🛰️ <strong>Operator view</strong> — viewing merchant{" "}
              <strong>{operator.name}</strong>
            </span>
            <button
              onClick={backToOperator}
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
              ← Back to Operator Console
            </button>
          </div>
        )}
        {children}
      </main>
    </div>
  );
}
