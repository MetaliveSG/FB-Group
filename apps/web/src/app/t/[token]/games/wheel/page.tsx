"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  resolveQr,
  getLoyalty,
  getWheel,
  spinWheel,
  getApiBase,
  installAuthHandler,
  AUTH_LOGOUT_EVENT,
} from "@/lib/api";
import { getCustomerToken } from "@/lib/auth";
import { wheelTargetRotation } from "@/lib/format";
import Wheel from "@/components/Wheel";
import ArcadeShell from "@/components/ArcadeShell";
import Celebration from "@/components/Celebration";
import { Button, Icons } from "@/components/ui";
import type { LoyaltySummary, WheelConfig, SpinResponse } from "@fbgroup/api-client";

export default function WheelGamePage() {
  const params = useParams();
  const router = useRouter();
  const token = decodeURIComponent(params.token as string);
  const base = getApiBase();

  const [custToken, setCustToken] = useState<string | null>(null);
  const [merchantId, setMerchantId] = useState<string | null>(null);
  const [loyalty, setLoyalty] = useState<LoyaltySummary | null>(null);
  const [wheel, setWheel] = useState<WheelConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [loggedOut, setLoggedOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [rotation, setRotation] = useState(0);
  const [spinning, setSpinning] = useState(false);
  const [spinResult, setSpinResult] = useState<SpinResponse | null>(null);

  const load = useCallback(async (tok: string, mid: string) => {
    const [loy, wh] = await Promise.all([getLoyalty(base, tok, mid), getWheel(base, tok, mid)]);
    setLoyalty(loy);
    setWheel(wh);
  }, [base]);

  useEffect(() => {
    installAuthHandler();
    function onLogout(e: Event) {
      const detail = (e as CustomEvent).detail as { actor?: string } | undefined;
      if (detail?.actor && detail.actor !== "customer") return;
      setCustToken(null);
      setLoggedOut(true);
      setSpinning(false);
    }
    window.addEventListener(AUTH_LOGOUT_EVENT, onLogout);
    const tok = getCustomerToken();
    setCustToken(tok);
    resolveQr(base, token)
      .then(async (data) => {
        setMerchantId(data.merchant.id);
        if (!tok) { setLoggedOut(true); setLoading(false); return; }
        try { await load(tok, data.merchant.id); }
        catch (e: unknown) { setError(e instanceof Error ? e.message : "Failed to load"); }
        finally { setLoading(false); }
      })
      .catch((e) => { setError(e.message ?? "Invalid QR token"); setLoading(false); });
    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, onLogout);
  }, [base, token, load]);

  async function handleSpin() {
    if (!custToken || !merchantId || !wheel || spinning) return;
    setSpinResult(null);
    setError(null);
    setSpinning(true);
    try {
      const res = await spinWheel(base, custToken, merchantId);
      setRotation(wheelTargetRotation(res.winning_index, wheel.segments.length, 5, rotation));
      setTimeout(() => {
        setSpinResult(res);
        setSpinning(false);
        if (loyalty) setLoyalty({ ...loyalty, points_balance: res.points_balance });
        if (custToken && merchantId) load(custToken, merchantId).catch(() => {});
      }, 4100);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Spin failed");
      setSpinning(false);
    }
  }

  if (loading) {
    return <ArcadeShell token={token} title="🎡 Spin the Wheel"><div style={{ textAlign: "center", color: "#ffd9b0" }}>Loading…</div></ArcadeShell>;
  }
  if (loggedOut) {
    return (
      <ArcadeShell token={token} title="🎡 Spin the Wheel">
        <div style={{ textAlign: "center", color: "#fff" }}>
          <Icons.Gift size={44} color="#ffd84d" style={{ marginBottom: 8 }} />
          <div style={{ fontWeight: 800, fontSize: "var(--text-xl)", marginBottom: 14 }}>Log in to play</div>
          <Button block variant="accent" size="lg" leftIcon={Icons.ArrowLeft} onClick={() => router.push(`/t/${encodeURIComponent(token)}`)}>Go to Login</Button>
        </div>
      </ArcadeShell>
    );
  }

  const canSpin = !!wheel && !!loyalty && loyalty.points_balance >= wheel.spin_cost && !spinning;
  // A win = landed on a coins/voucher segment (not "Try again").
  const won = !!spinResult && !spinning && (spinResult.prize.points > 0 || !!spinResult.prize.voucher_code);

  return (
    <ArcadeShell token={token} title="🎡 Spin the Wheel" coins={loyalty?.points_balance}>
      <Celebration show={won} />
      {error && <div style={{ color: "#ffd9d9", textAlign: "center", marginBottom: "var(--space-3)" }}>{error}</div>}
      <div className="game-cabinet">
        {wheel ? (
          <>
            <div className="game-cabinet-title">SPIN &amp; WIN</div>
            <Wheel segments={wheel.segments} rotation={rotation} spinning={spinning} size={320} />
            <div style={{ marginTop: "var(--space-4)" }}>
              <button className="slot-play-btn" disabled={!canSpin} onClick={handleSpin}>
                {spinning ? "Spinning…" : `Spin · ${wheel.spin_cost} coins`}
              </button>
              {loyalty && loyalty.points_balance < wheel.spin_cost && !spinning && (
                <div style={{ marginTop: "var(--space-2)", fontSize: "var(--text-sm)", color: "#ffd9d9" }}>Not enough coins to spin.</div>
              )}
            </div>
            {spinResult && (
              <div style={{ background: "linear-gradient(180deg,#fff7d6,#ffe9a8)", border: "2px solid #f4c430", borderRadius: 12, padding: 14, marginTop: "var(--space-4)", color: "#7a1f1f" }}>
                <div style={{ fontSize: "var(--text-lg)", fontWeight: 900 }}>{spinResult.prize.label}</div>
                {spinResult.prize.points > 0 && <div style={{ marginTop: 4, fontWeight: 700 }}>+{spinResult.prize.points} coins!</div>}
                {spinResult.prize.voucher_code && <div style={{ marginTop: 4, fontSize: "var(--text-sm)" }}>Voucher: <code>{spinResult.prize.voucher_code}</code></div>}
                <div style={{ marginTop: 4, fontSize: "var(--text-xs)", color: "#92400e" }}>New balance: {spinResult.points_balance.toLocaleString()} coins</div>
              </div>
            )}
          </>
        ) : (
          <div style={{ color: "#ffe9a8", padding: "var(--space-5)", textAlign: "center" }}>Wheel not available.</div>
        )}
      </div>
    </ArcadeShell>
  );
}
