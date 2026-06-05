"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

// Demo launcher content. These reflect the LIVE UI-onboarded merchants (Breadtalk Group + Pepper Lunch
// Group); they're live-DB accounts/tokens, not seeded, so they change if the data is wiped + re-onboarded.
const DEMO_PW = "Password123!";
const MERCHANT_LOGINS: { email: string; scope: string }[] = [
  { email: "owner@breadtalk.sg", scope: "Breadtalk Group — full group (Bakery + Toast Box outlets)" },
  { email: "owner@pepperlunch.sg", scope: "Pepper Lunch Group — full group (all outlets)" },
  { email: "manager@toastbox.sg", scope: "Toast Box @ Orchard — single storefront" },
];

const CUSTOMER_LINKS: { label: string; path: string }[] = [
  { label: "Toast Box @ Orchard (scan a table)", path: "/t/toast-box-orchard-f1878dd3" },
  { label: "Pepper Lunch @ TPY (scan a table)", path: "/t/pepper-lunch-tpy-0ab5b283" },
  { label: "Pepper Lunch Group (browse outlets)", path: "/t/node/9a05bb10711a47bbb1712302b23a33a5" },
];

export default function HomePage() {
  const router = useRouter();
  const [qrToken, setQrToken] = useState("toast-box-orchard-f1878dd3");

  function handleGo(e: React.FormEvent) {
    e.preventDefault();
    const token = qrToken.trim();
    if (token) router.push(`/t/${encodeURIComponent(token)}`);
  }

  // Click a merchant → the login page with its credentials pre-filled.
  function loginAs(email: string) {
    router.push(`/merchant/login?email=${encodeURIComponent(email)}&pw=${encodeURIComponent(DEMO_PW)}`);
  }

  return (
    <div className="home-container">
      <div className="home-hero">
        <h1>FB Group F&amp;B Platform</h1>
        <p className="tagline">
          Singapore F&amp;B CRM, QR ordering &amp; loyalty — multi-tenant member tree
        </p>
      </div>

      {/* Merchant dashboards — the live UI-onboarded groups */}
      <div className="home-demo-box">
        <h2>Merchant Dashboards</h2>
        <p style={{ color: "var(--color-text-muted)", fontSize: 14, marginBottom: 16 }}>
          Staff CRM, reports, orders, menu, tables &amp; QR — scoped to each login&apos;s place in the
          member tree. All passwords <code>Password123!</code>.
        </p>

        <div style={{ display: "grid", gap: 8, marginBottom: 16 }}>
          {MERCHANT_LOGINS.map((m) => (
            <button
              key={m.email}
              type="button"
              onClick={() => loginAs(m.email)}
              style={{
                background: "#f9fafb",
                border: "1px solid #e5e7eb",
                borderRadius: 8,
                padding: "10px 14px",
                fontSize: 14,
                textAlign: "left",
                cursor: "pointer",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: 12,
              }}
            >
              <span>
                <code>{m.email}</code>
                <span style={{ display: "block", color: "var(--color-text-muted)", fontSize: 13, marginTop: 2 }}>
                  {m.scope}
                </span>
              </span>
              <span aria-hidden style={{ color: "var(--color-primary)", fontWeight: 700, whiteSpace: "nowrap" }}>
                Log in →
              </span>
            </button>
          ))}
        </div>

        <p style={{ fontSize: 13, color: "var(--color-text-muted)", margin: 0 }}>
          Click a merchant to open the login with its credentials pre-filled.
        </p>
      </div>

      {/* Customer QR ordering */}
      <div className="home-demo-box">
        <h2>Customer Demo — QR Ordering</h2>
        <p style={{ color: "var(--color-text-muted)", fontSize: 14, marginBottom: 16 }}>
          Open a storefront the way a diner would (scan a table) or browse a group. OTP login phone{" "}
          <code>+6580000000</code> (DEBUG returns the code).
        </p>

        <div style={{ display: "grid", gap: 8, marginBottom: 16 }}>
          {CUSTOMER_LINKS.map((c) => (
            <a key={c.path} href={c.path} className="btn btn-secondary" style={{ display: "flex", justifyContent: "space-between" }}>
              <span>{c.label}</span>
              <span aria-hidden>→</span>
            </a>
          ))}
        </div>

        <form onSubmit={handleGo}>
          <div className="form-group">
            <label htmlFor="qr-token">…or paste any QR token</label>
            <input
              id="qr-token"
              type="text"
              value={qrToken}
              onChange={(e) => setQrToken(e.target.value)}
              placeholder="e.g. toast-box-orchard-f1878dd3"
            />
          </div>
          <button type="submit" className="btn btn-primary btn-block">
            Open Table Ordering
          </button>
        </form>
      </div>

      {/* Platform console */}
      <div className="home-demo-box">
        <h2>Platform Console</h2>
        <p style={{ color: "var(--color-text-muted)", fontSize: 14, marginBottom: 16 }}>
          Platform super-admin — ecosystem-wide view, onboard merchants, manage the member tree, and
          drill into any node (reports + per-merchant management).
        </p>

        <div style={{ fontSize: 14, marginBottom: 16, background: "#f9fafb", padding: "12px 14px", borderRadius: 8, border: "1px solid #e5e7eb" }}>
          <strong>Demo credentials:</strong>
          <br />
          Email: <code>superadmin@platform.sg</code>
          <br />
          Password: <code>Password123!</code>
        </div>

        <a href="/platform/login" className="btn btn-secondary btn-block" style={{ display: "flex" }}>
          Go to Platform Console
        </a>
      </div>

      <div className="home-demo-box">
        <h2>About this platform</h2>
        <div style={{ fontSize: 14, color: "var(--color-text-muted)", lineHeight: 1.8 }}>
          <p>A Singapore F&amp;B loyalty &amp; CRM platform built on a multi-tenant member tree:</p>
          <ul style={{ paddingLeft: 20 }}>
            <li>QR-code table ordering with modifiers, coins, tiers &amp; games</li>
            <li>Member tree: Chains nest Storefronts; node-scoped roles (Manager/Cashier/Staff/Finance)</li>
            <li>Multiple payment methods (Cash, Card, NETS, PayWave, PayNow)</li>
            <li>Staff CRM with segments, churn prediction &amp; customer profiles</li>
            <li>Node-scoped sales analytics, forecasting, top-item reports &amp; AI insights</li>
          </ul>
          <p>
            <strong>Onboarded via the Platform Console:</strong> Breadtalk Group &amp; Pepper Lunch Group.
          </p>
        </div>
      </div>
    </div>
  );
}
