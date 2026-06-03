"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();
  const [qrToken, setQrToken] = useState("orchard-01");

  function handleGo(e: React.FormEvent) {
    e.preventDefault();
    const token = qrToken.trim();
    if (token) {
      router.push(`/t/${encodeURIComponent(token)}`);
    }
  }

  return (
    <div className="home-container">
      <div className="home-hero">
        <h1>FB Group F&amp;B Platform</h1>
        <p className="tagline">
          Singapore F&amp;B CRM &amp; QR Ordering PoC — Makan Express &amp; Kopi Culture
        </p>
      </div>

      <div className="home-demo-box">
        <h2>Customer Demo — QR Ordering</h2>
        <p style={{ color: "var(--color-text-muted)", fontSize: 14, marginBottom: 16 }}>
          Paste a QR token to open the table ordering experience. Use the sample token below
          (Makan Express, Orchard outlet, Table 1) or any token from the seeded demo data.
        </p>

        <form onSubmit={handleGo}>
          <div className="form-group">
            <label htmlFor="qr-token">QR Token</label>
            <input
              id="qr-token"
              type="text"
              value={qrToken}
              onChange={(e) => setQrToken(e.target.value)}
              placeholder="e.g. orchard-01"
            />
            <p className="demo-token-hint">
              Sample token: <code>orchard-01</code> (Orchard outlet, Table 1)
            </p>
          </div>
          <button type="submit" className="btn btn-primary btn-block">
            Open Table Ordering
          </button>
        </form>
      </div>

      <div className="home-demo-box">
        <h2>Merchant Dashboard</h2>
        <p style={{ color: "var(--color-text-muted)", fontSize: 14, marginBottom: 16 }}>
          Access the staff CRM, analytics, and customer insights dashboard.
        </p>

        <div style={{ fontSize: 14, marginBottom: 16, background: "#f9fafb", padding: "12px 14px", borderRadius: 8, border: "1px solid #e5e7eb" }}>
          <strong>Demo credentials:</strong>
          <br />
          Email: <code>owner@makan.sg</code>
          <br />
          Password: <code>Password123!</code>
        </div>

        <a href="/merchant/login" className="btn btn-secondary btn-block" style={{ display: "flex" }}>
          Go to Merchant Login
        </a>
      </div>

      <div className="home-demo-box">
        <h2>Platform Console</h2>
        <p style={{ color: "var(--color-text-muted)", fontSize: 14, marginBottom: 16 }}>
          Platform super-admin — ecosystem-wide view across all merchants, onboarding,
          coalitions, and drill-down into any merchant.
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
        <h2>About this PoC</h2>
        <div style={{ fontSize: 14, color: "var(--color-text-muted)", lineHeight: 1.8 }}>
          <p>This is a proof-of-concept for a Singapore F&amp;B loyalty and CRM platform featuring:</p>
          <ul style={{ paddingLeft: 20 }}>
            <li>QR-code table ordering with modifier selection</li>
            <li>Customer loyalty (OTP login, coins, tiers)</li>
            <li>Multiple payment methods (Cash, Card, NETS, PayWave, PayNow)</li>
            <li>Staff CRM with segments, churn prediction, and customer profiles</li>
            <li>Sales analytics, forecasting, and top-item reports</li>
          </ul>
          <p>
            <strong>Merchants:</strong> Makan Express &amp; Kopi Culture
            <br />
            <strong>Customers:</strong> 25 seeded customers (<code>cust0@example.sg</code> … <code>cust24@example.sg</code>, pw: <code>Customer123!</code>)
          </p>
        </div>
      </div>
    </div>
  );
}
