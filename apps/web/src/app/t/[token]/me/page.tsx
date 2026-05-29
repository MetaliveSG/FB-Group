"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { getMyProfile, updateMyProfile, getApiBase, installAuthHandler } from "@/lib/api";
import { getCustomerToken, getCustomerData, setCustomerData, clearCustomerToken } from "@/lib/auth";
import { Card, Button, Skeleton, Icons } from "@/components/ui";
import CustomerTabBar from "@/components/CustomerTabBar";
import type { MyProfile } from "@fbgroup/api-client";

const GENDERS = [
  { value: "", label: "Prefer not to say" },
  { value: "male", label: "Male" },
  { value: "female", label: "Female" },
  { value: "other", label: "Other" },
];

function maskPhone(p: string | null): string {
  if (!p) return "—";
  const last4 = p.slice(-4);
  return `•••• •••• ${last4}`;
}

function Shell({ token, children }: { token: string; children: React.ReactNode }) {
  return (
    <div style={{ maxWidth: 480, margin: "0 auto", minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--color-bg)" }}>
      {children}
      <CustomerTabBar token={token} active="me" />
    </div>
  );
}

export default function MePage() {
  const params = useParams();
  const router = useRouter();
  const token = decodeURIComponent(params.token as string);
  const base = getApiBase();

  const [profile, setProfile] = useState<MyProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [loggedOut, setLoggedOut] = useState(false);

  // editable fields
  const [phone, setPhone] = useState("");
  const [editingPhone, setEditingPhone] = useState(false);
  const [birthday, setBirthday] = useState("");
  const [gender, setGender] = useState("");
  const [fullName, setFullName] = useState("");

  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    installAuthHandler();
    const tok = getCustomerToken();
    if (!tok) {
      setLoggedOut(true);
      setLoading(false);
      return;
    }
    getMyProfile(base, tok)
      .then((p) => {
        setProfile(p);
        setPhone(p.phone ?? "");
        setBirthday(p.birthday ?? "");
        setGender(p.gender ?? "");
        setFullName(p.full_name ?? "");
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load profile"))
      .finally(() => setLoading(false));
  }, [base]);

  async function save() {
    const tok = getCustomerToken();
    if (!tok) return;
    if (!phone.trim()) {
      setEditingPhone(true);
      setError("Mobile number is required.");
      return;
    }
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const updated = await updateMyProfile(base, tok, {
        phone: phone.trim(),
        birthday: birthday || null,
        gender: gender || null,
        full_name: fullName || undefined,
      });
      setProfile(updated);
      setEditingPhone(false);
      setSaved(true);
      // keep local cache (name/phone) in sync for other screens
      const data = getCustomerData() ?? {};
      setCustomerData({ ...data, full_name: updated.full_name, phone: updated.phone });
      setTimeout(() => setSaved(false), 2500);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Could not save changes");
    } finally {
      setSaving(false);
    }
  }

  function logout() {
    clearCustomerToken();
    router.push(`/t/${encodeURIComponent(token)}`);
  }

  if (loading) {
    return (
      <Shell token={token}>
        <header style={{ padding: "var(--space-4)", background: "linear-gradient(180deg, var(--brand-600), var(--brand-700))", color: "#fff" }}>
          <div style={{ fontSize: "var(--text-lg)", fontWeight: 900 }}>Account</div>
        </header>
        <main style={{ flex: 1, padding: "var(--space-4)" }}>
          <Skeleton width="100%" height={220} radius={12} />
        </main>
      </Shell>
    );
  }

  if (loggedOut) {
    return (
      <Shell token={token}>
        <header style={{ padding: "var(--space-4)", background: "linear-gradient(180deg, var(--brand-600), var(--brand-700))", color: "#fff" }}>
          <div style={{ fontSize: "var(--text-lg)", fontWeight: 900 }}>Account</div>
        </header>
        <main style={{ flex: 1, display: "flex", alignItems: "center", padding: "var(--space-5)" }}>
          <Card pad style={{ width: "100%", textAlign: "center" }}>
            <Icons.User size={44} color="var(--color-primary)" style={{ marginBottom: 8 }} />
            <div style={{ fontWeight: 800, fontSize: "var(--text-lg)", marginBottom: 6 }}>You&apos;re not logged in</div>
            <Button block variant="primary" size="lg" leftIcon={Icons.ArrowLeft} onClick={() => router.push(`/t/${encodeURIComponent(token)}`)}>
              Go to Menu
            </Button>
          </Card>
        </main>
      </Shell>
    );
  }

  return (
    <Shell token={token}>
      <header style={{ padding: "var(--space-4)", background: "linear-gradient(180deg, var(--brand-600), var(--brand-700))", color: "#fff" }}>
        <div style={{ fontSize: "var(--text-lg)", fontWeight: 900 }}>Account</div>
        <div style={{ fontSize: "var(--text-xs)", opacity: 0.85 }}>{fullName || "Guest"}</div>
      </header>

      <main style={{ flex: 1, padding: "var(--space-4)" }}>
        <Card pad>
          <div style={{ fontSize: "var(--text-lg)", fontWeight: 800, marginBottom: "var(--space-4)" }}>My Profile</div>

          {/* Full name */}
          <div className="form-group">
            <label>Name</label>
            <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Your name" />
          </div>

          {/* Mobile number — required, masked by default, country-code-ready (E.164) */}
          <div className="form-group">
            <label>Mobile Number <span style={{ color: "var(--color-danger)" }}>*</span></label>
            {editingPhone ? (
              <>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+65 9123 4567"
                  required
                  autoFocus
                />
                <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: 4 }}>
                  Include your country code (e.g. +65). Used to log in.
                </div>
              </>
            ) : (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "var(--space-2)" }}>
                <span style={{ fontWeight: 700, letterSpacing: 1 }}>{maskPhone(profile?.phone ?? phone)}</span>
                <button
                  type="button"
                  onClick={() => setEditingPhone(true)}
                  style={{ background: "none", border: "none", color: "var(--color-primary)", fontWeight: 700, cursor: "pointer", fontSize: "var(--text-sm)" }}
                >
                  Change
                </button>
              </div>
            )}
          </div>

          {/* Birthday — optional */}
          <div className="form-group">
            <label>Birthday <span style={{ color: "var(--color-text-muted)", fontWeight: 400 }}>(optional)</span></label>
            <input type="date" value={birthday} onChange={(e) => setBirthday(e.target.value)} />
            <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginTop: 4 }}>
              Get a coins bonus on your birthday 🎂
            </div>
          </div>

          {/* Gender — optional */}
          <div className="form-group">
            <label>Gender <span style={{ color: "var(--color-text-muted)", fontWeight: 400 }}>(optional)</span></label>
            <select
              value={gender}
              onChange={(e) => setGender(e.target.value)}
              style={{ width: "100%", padding: "10px 12px", borderRadius: "var(--radius)", border: "1.5px solid var(--color-border-strong)", fontSize: "var(--text-base)", background: "var(--color-surface)" }}
            >
              {GENDERS.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
            </select>
          </div>

          {error && <div style={{ color: "var(--color-danger)", fontSize: "var(--text-sm)", marginBottom: "var(--space-2)" }}>{error}</div>}
          {saved && <div style={{ color: "var(--color-success)", fontSize: "var(--text-sm)", marginBottom: "var(--space-2)", fontWeight: 700 }}>✓ Saved</div>}

          <Button block variant="primary" size="lg" leftIcon={Icons.Check} loading={saving} onClick={save}>
            Save Changes
          </Button>
        </Card>

        <div style={{ marginTop: "var(--space-4)" }}>
          <Button block variant="ghost" leftIcon={Icons.X} onClick={logout}>Log out</Button>
        </div>
      </main>
    </Shell>
  );
}
