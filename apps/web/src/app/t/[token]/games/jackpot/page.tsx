"use client";

import { useState, useEffect, useCallback, type CSSProperties } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  resolveQr,
  getLoyalty,
  getJackpot,
  playJackpot,
  getApiBase,
  installAuthHandler,
  AUTH_LOGOUT_EVENT,
} from "@/lib/api";
import { getCustomerToken } from "@/lib/auth";
import { formatSGD } from "@/lib/format";
import ArcadeShell from "@/components/ArcadeShell";
import Celebration from "@/components/Celebration";
import { Button, Icons } from "@/components/ui";
import type { LoyaltySummary, JackpotConfig, JackpotCell, JackpotPlay } from "@fbgroup/api-client";

export default function JackpotGamePage() {
  const params = useParams();
  const router = useRouter();
  const token = decodeURIComponent(params.token as string);
  const base = getApiBase();

  const [custToken, setCustToken] = useState<string | null>(null);
  const [merchantId, setMerchantId] = useState<string | null>(null);
  const [loyalty, setLoyalty] = useState<LoyaltySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [loggedOut, setLoggedOut] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [jackpot, setJackpot] = useState<JackpotConfig | null>(null);
  const [jackpotGrid, setJackpotGrid] = useState<JackpotCell[][] | null>(null);
  const [jackpotPlaying, setJackpotPlaying] = useState(false); // busy (checking + spinning)
  const [reelsSpinning, setReelsSpinning] = useState(false);   // reels animate only after server OK
  const [jackpotResult, setJackpotResult] = useState<JackpotPlay | null>(null);
  const [reelsLanded, setReelsLanded] = useState(0);
  const [grandPrize, setGrandPrize] = useState(1000); // seeded from the server pot on load

  const load = useCallback(async (tok: string, mid: string) => {
    const [loy, jp] = await Promise.all([getLoyalty(base, tok, mid), getJackpot(base, tok, mid).catch(() => null)]);
    setLoyalty(loy);
    setJackpot(jp);
    if (jp) setGrandPrize(jp.grand_prize); // real persistent pot (resets to base on a win)
  }, [base]);

  useEffect(() => {
    installAuthHandler();
    function onLogout(e: Event) {
      const detail = (e as CustomEvent).detail as { actor?: string } | undefined;
      if (detail?.actor && detail.actor !== "customer") return;
      setCustToken(null);
      setLoggedOut(true);
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

  // Tick the meter up gently between server reads (matches the server's ~0.5/s
  // growth) so it feels live; the authoritative value comes from the API.
  useEffect(() => {
    const id = window.setInterval(() => setGrandPrize((g) => g + 1), 2000);
    return () => window.clearInterval(id);
  }, []);

  async function handleJackpotPlay() {
    if (!custToken || !merchantId || !jackpot || jackpotPlaying) return;
    setJackpotResult(null);
    setError(null);
    setJackpotPlaying(true); // button → "Checking…"; reels stay idle until the server confirms

    // 1) Ask the backend FIRST — it atomically checks the coin balance and deducts.
    //    Only if it succeeds do the reels actually spin (no spin-then-fail).
    let res;
    try {
      res = await playJackpot(base, custToken, merchantId);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Not enough coins to play");
      setJackpotPlaying(false);
      if (custToken && merchantId) load(custToken, merchantId).catch(() => {}); // refresh real balance
      return;
    }

    // 2) Confirmed + charged → run the reels, then reveal the server's result.
    setJackpotGrid(null);
    setReelsLanded(0);
    setReelsSpinning(true);
    const MIN_SPIN_MS = 3000;
    const REEL_STAGGER_MS = 360;
    setTimeout(() => {
      setJackpotGrid(res.grid);
      setReelsLanded(1);
      setTimeout(() => setReelsLanded(2), REEL_STAGGER_MS);
      setTimeout(() => {
        setReelsLanded(3);
        setReelsSpinning(false);
        setJackpotResult(res);
        setJackpotPlaying(false);
        if (loyalty) setLoyalty({ ...loyalty, points_balance: res.points_balance });
        if (custToken && merchantId) load(custToken, merchantId).catch(() => {});
      }, REEL_STAGGER_MS * 2);
    }, MIN_SPIN_MS);
  }

  if (loading) {
    return <ArcadeShell token={token} title="🎰 Lucky 888 Jackpot"><div style={{ textAlign: "center", color: "#ffd9b0" }}>Loading…</div></ArcadeShell>;
  }
  if (loggedOut) {
    return (
      <ArcadeShell token={token} title="🎰 Lucky 888 Jackpot">
        <div style={{ textAlign: "center", color: "#fff" }}>
          <Icons.Gift size={44} color="#ffd84d" style={{ marginBottom: 8 }} />
          <div style={{ fontWeight: 800, fontSize: "var(--text-xl)", marginBottom: 14 }}>Log in to play</div>
          <Button block variant="accent" size="lg" leftIcon={Icons.ArrowLeft} onClick={() => router.push(`/t/${encodeURIComponent(token)}`)}>Go to Login</Button>
        </div>
      </ArcadeShell>
    );
  }

  if (!jackpot || jackpot.prizes.length === 0) {
    return <ArcadeShell token={token} title="🎰 Lucky 888 Jackpot" coins={loyalty?.points_balance}><div style={{ color: "#ffe9a8", textAlign: "center" }}>Jackpot not available.</div></ArcadeShell>;
  }

  const jackpotPrizes = jackpot.prizes;
  const reelStripEmojis = [...jackpotPrizes, ...jackpotPrizes, ...jackpotPrizes].map((p) => p.emoji);
  const burstCoins = Array.from({ length: 16 }, (_, i) => {
    const angle = (i / 16) * Math.PI * 2;
    const dist = 120 + (i % 4) * 34;
    return {
      isCoin: i % 3 !== 0,
      cx: `${Math.round(Math.cos(angle) * dist)}px`,
      cy: `${Math.round(Math.sin(angle) * dist - 40)}px`,
      cr: `${(i % 2 ? 1 : -1) * (180 + (i % 3) * 90)}deg`,
      delay: `${(i % 5) * 0.05}s`,
    };
  });

  const won = !!jackpotResult?.won && !jackpotPlaying;

  return (
    <ArcadeShell token={token} title="🎰 Lucky 888 Jackpot" coins={loyalty?.points_balance}>
      <Celebration show={won} />
      {error && <div style={{ color: "#ffd9d9", textAlign: "center", marginBottom: "var(--space-3)" }}>{error}</div>}
      <div className={`slot-machine${won ? " win" : ""}`}>
        {jackpotResult?.won && !jackpotPlaying && (
          <div className="slot-burst" aria-hidden>
            {burstCoins.map((c, i) => (
              <span key={i} className={`slot-coin${c.isCoin ? " gold-coin" : ""}`} style={{ "--cx": c.cx, "--cy": c.cy, "--cr": c.cr, animationDelay: c.delay } as CSSProperties}>
                {c.isCoin ? null : "✨"}
              </span>
            ))}
          </div>
        )}
        <div className="slot-marquee">
          <p className="slot-title">GRAND JACKPOT</p>
          <div className="slot-meter">
            <span className="gold-coin slot-meter-coin" aria-hidden />
            <span className="slot-meter-num">{grandPrize.toLocaleString()}</span>
          </div>
          <div className="slot-bulbs">
            {Array.from({ length: 9 }).map((_, i) => <span key={i} className="slot-bulb" style={{ animationDelay: `${(i % 3) * 0.3}s` }} />)}
          </div>
        </div>

        <div className="slot-reels">
          {[0, 1, 2].map((colIdx) => {
            const reelSpinning = reelsSpinning && reelsLanded <= colIdx;
            return (
              <div key={colIdx} className="slot-reel">
                {reelSpinning ? (
                  <div className="slot-strip spinning" style={{ animationDuration: `${0.42 + colIdx * 0.06}s` }}>
                    {reelStripEmojis.map((emoji, i) => <div className="slot-tile" key={i}><span className="slot-cell-emoji">{emoji}</span></div>)}
                  </div>
                ) : jackpotGrid ? (
                  <div className="slot-strip stopping">
                    {[0, 1, 2].map((rowIdx) => {
                      const cell = jackpotGrid[rowIdx]?.[colIdx];
                      return (
                        <div key={`r${rowIdx}`} className={`slot-tile${rowIdx === 1 ? " payline" : ""}`} title={cell?.item_name}>
                          <span className="slot-cell-emoji">{cell ? cell.emoji : "7️⃣"}</span>
                        </div>
                      );
                    })}
                    {reelStripEmojis.slice(0, 4).map((emoji, i) => <div className="slot-tile" key={`d${i}`}><span className="slot-cell-emoji">{emoji}</span></div>)}
                  </div>
                ) : (
                  <div className="slot-strip">
                    {[0, 1, 2].map((rowIdx) => {
                      const p = jackpotPrizes[(rowIdx * 3 + colIdx) % jackpotPrizes.length];
                      return (
                        <div key={rowIdx} className={`slot-tile${rowIdx === 1 ? " payline" : ""}`} title={p?.item_name}>
                          <span className="slot-cell-emoji">{p ? p.emoji : "🍽️"}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
          <div className="slot-payline" />
          <span className="slot-payline-arrow left">▶</span>
          <span className="slot-payline-arrow right">◀</span>
        </div>

        <div className="text-center" style={{ padding: "0 18px" }}>
          <button
            className="slot-play-btn"
            disabled={!custToken || jackpotPlaying || (jackpot.spin_cost > 0 && loyalty != null && loyalty.points_balance < jackpot.spin_cost)}
            onClick={handleJackpotPlay}
          >
            {jackpotPlaying
              ? (reelsSpinning ? "Spinning…" : "Checking…")
              : jackpot.spin_cost > 0 ? `Spin · ${jackpot.spin_cost} coins` : "Spin — Free!"}
          </button>
          {jackpot.spin_cost > 0 && loyalty && loyalty.points_balance < jackpot.spin_cost && !jackpotPlaying && (
            <div style={{ marginTop: 10, fontSize: 13, color: "#ffd9d9" }}>Not enough coins to play.</div>
          )}
          {jackpotResult && !jackpotPlaying && (
            <div style={{ marginTop: 16 }}>
              {jackpotResult.won && jackpotResult.prize ? (
                <div style={{ background: "linear-gradient(180deg,#fff7d6,#ffe9a8)", border: "2px solid #f4c430", borderRadius: 12, padding: 14 }}>
                  <div className="slot-win-banner">🎉 JACKPOT! 🎉</div>
                  <div style={{ marginTop: 4, fontWeight: 800, color: "#7a1f1f" }}>Free {jackpotResult.prize.item_name}</div>
                  <div style={{ marginTop: 6, fontSize: 13, color: "#7a1f1f" }}>Voucher: <code>{jackpotResult.prize.voucher_code}</code></div>
                  <div style={{ marginTop: 2, fontSize: 12, color: "#92400e" }}>Value {formatSGD(jackpotResult.prize.item_price)} · Balance {jackpotResult.points_balance.toLocaleString()} coins</div>
                </div>
              ) : (
                <div style={{ color: "#ffe9a8", fontWeight: 700 }}>
                  So close — spin again!
                  <div style={{ marginTop: 2, fontSize: 12, color: "#ffd9b0", fontWeight: 500 }}>Balance {jackpotResult.points_balance.toLocaleString()} coins</div>
                </div>
              )}
            </div>
          )}
        </div>

        <div style={{ marginTop: 16, padding: "14px 18px 0", borderTop: "1px solid rgba(255,209,102,.25)" }}>
          <div style={{ fontSize: 12, color: "#ffd9b0", marginBottom: 8, textAlign: "center" }}>Match 3 on the payline to win:</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, justifyContent: "center" }}>
            {jackpot.prizes.map((p) => <span key={p.item_name} className="slot-legend-chip">{p.emoji} {p.item_name} · {formatSGD(p.item_price)}</span>)}
          </div>
        </div>
      </div>
    </ArcadeShell>
  );
}
