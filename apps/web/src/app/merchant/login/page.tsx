"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { staffLogin } from "@/lib/api";
import { setStaffToken, setStaffRefreshToken, setStaffUser } from "@/lib/auth";
import { getApiBase } from "@/lib/api";

export default function MerchantLoginPage() {
  const router = useRouter();
  const base = getApiBase();
  const [email, setEmail] = useState("owner@makan.sg");
  const [password, setPassword] = useState("Password123!");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await staffLogin(base, email, password);
      setStaffToken(res.access_token);
      setStaffRefreshToken(res.refresh_token);
      if (res.user) {
        setStaffUser({
          id: res.user.id,
          email: res.user.email,
          full_name: res.user.full_name,
        });
      }
      router.push("/merchant/crm");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed. Check credentials.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--color-bg)",
        padding: "24px",
      }}
    >
      <div style={{ width: "100%", maxWidth: 420 }}>
        <div style={{ textAlign: "center", marginBottom: 32 }}>
          <h1
            style={{
              fontSize: 28,
              fontWeight: 900,
              color: "var(--color-primary)",
              margin: "0 0 6px",
            }}
          >
            FB Group
          </h1>
          <p style={{ color: "var(--color-text-muted)", margin: 0 }}>
            Merchant Dashboard — Staff Login
          </p>
        </div>

        <div className="card">
          {error && <div className="alert alert-error">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </div>

            <div
              style={{
                fontSize: 13,
                color: "var(--color-text-muted)",
                background: "#f9fafb",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius)",
                padding: "10px 12px",
                marginBottom: 16,
              }}
            >
              <strong>Demo credentials:</strong>
              <br />
              Owner: <code>owner@makan.sg</code> / <code>Password123!</code>
              <br />
              Manager: <code>manager.orchard@makan.sg</code> / <code>Password123!</code>
            </div>

            <button
              type="submit"
              className="btn btn-primary btn-block btn-lg"
              disabled={loading}
            >
              {loading ? "Signing in…" : "Sign In"}
            </button>
          </form>
        </div>

        <p style={{ textAlign: "center", marginTop: 20, fontSize: 14 }}>
          <a href="/">← Back to Home</a>
        </p>
      </div>
    </div>
  );
}
