"use client";

import { useState, useEffect, useCallback, type CSSProperties } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  resolveQr,
  getLoyalty,
  getMyVouchers,
  getRewardsCatalog,
  redeemReward,
  getWheel,
  spinWheel,
  getJackpot,
  playJackpot,
  getApiBase,
  installAuthHandler,
  AUTH_LOGOUT_EVENT,
} from "@/lib/api";
import { getCustomerToken } from "@/lib/auth";
import { formatSGD, relativeTime, wheelTargetRotation } from "@/lib/format";
import Wheel from "@/components/Wheel";
import {
  Button,
  Card,
  ListItem,
  Badge,
  Skeleton,
  EmptyState,
  CoinBalance,
  TierProgress,
  Icons,
} from "@/components/ui";
import CustomerTabBar from "@/components/CustomerTabBar";
import type {
  QrResolution,
  LoyaltySummary,
  CatalogItem,
  MyVoucher,
  WheelConfig,
  SpinResponse,
  RedeemResponse,
  JackpotConfig,
  JackpotCell,
  JackpotPlay,
} from "@fbgroup/api-client";

// Module-scope so its identity is stable across re-renders. (Defining it inside
// the component made the grand-prize meter's 140ms tick remount the whole tree —
// which restarted the jackpot reels forever.)
function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ maxWidth: 480, margin: "0 auto", minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--color-bg)" }}>
      {children}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2
      style={{
        fontSize: "var(--text-sm)",
        fontWeight: 800,
        letterSpacing: 1,
        textTransform: "uppercase",
        color: "var(--color-text-muted)",
        margin: "var(--space-5) 0 var(--space-3)",
      }}
    >
      {children}
    </h2>
  );
}

const TIER_TONE: Record<string, "gold" | "default" | "warning"> = {
  gold: "gold",
  silver: "default",
  bronze: "warning",
};

export default function RewardsPage() {
  const params = useParams();
  const router = useRouter();
  const token = decodeURIComponent(params.token as string);
  const base = getApiBase();

  const [custToken, setCustToken] = useState<string | null>(null);
  const [merchantId, setMerchantId] = useState<string | null>(null);
  const [qr, setQr] = useState<QrResolution | null>(null);

  const [loyalty, setLoyalty] = useState<LoyaltySummary | null>(null);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]);
  const [vouchers, setVouchers] = useState<MyVoucher[]>([]);
  const [wheel, setWheel] = useState<WheelConfig | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loggedOut, setLoggedOut] = useState(false);

  // Redeem state
  const [redeemingId, setRedeemingId] = useState<string | null>(null);
  const [lastVoucher, setLastVoucher] = useState<RedeemResponse | null>(null);

  // Wheel state
  const [rotation, setRotation] = useState(0);
  const [spinning, setSpinning] = useState(false);
  const [spinResult, setSpinResult] = useState<SpinResponse | null>(null);

  // Jackpot state
  const [jackpot, setJackpot] = useState<JackpotConfig | null>(null);
  const [jackpotGrid, setJackpotGrid] = useState<JackpotCell[][] | null>(null);
  const [jackpotPlaying, setJackpotPlaying] = useState(false);
  const [jackpotResult, setJackpotResult] = useState<JackpotPlay | null>(null);
  // How many reels have decelerated and stopped (0..3) — reels stop left-to-right.
  const [reelsLanded, setReelsLanded] = useState(0);
  // Decorative "grand jackpot" meter that ticks upward from 10,000 coins.
  const [grandPrize, setGrandPrize] = useState(10000);

  const loadAll = useCallback(
    async (tok: string, mid: string) => {
      const [loy, cat, vch, wh, jp] = await Promise.all([
        getLoyalty(base, tok, mid),
        getRewardsCatalog(base, tok, mid),
        getMyVouchers(base, tok, mid).catch(() => []),
        getWheel(base, tok, mid),
        // Jackpot is optional — not every merchant configures one.
        getJackpot(base, tok, mid).catch(() => null),
      ]);
      setLoyalty(loy);
      setCatalog(cat);
      setVouchers(vch);
      setWheel(wh);
      setJackpot(jp);
    },
    [base]
  );

  useEffect(() => {
    installAuthHandler();

    // A failed refresh clears the customer session — show a clean re-login
    // prompt instead of an error + empty data.
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
        setQr(data);
        setMerchantId(data.merchant.id);
        if (!tok) {
          setLoggedOut(true);
          setLoading(false);
          return;
        }
        try {
          await loadAll(tok, data.merchant.id);
        } catch (e: unknown) {
          setError(e instanceof Error ? e.message : "Failed to load rewards");
        } finally {
          setLoading(false);
        }
      })
      .catch((e) => {
        setError(e.message ?? "Invalid QR token");
        setLoading(false);
      });

    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, onLogout);
  }, [base, token, loadAll]);

  // Tick the grand-jackpot meter upward so it feels "live" (purely cosmetic).
  useEffect(() => {
    const id = window.setInterval(() => {
      setGrandPrize((g) => g + 1 + Math.floor(Math.random() * 7));
    }, 140);
    return () => window.clearInterval(id);
  }, []);

  async function handleRedeem(item: CatalogItem) {
    if (!custToken || !merchantId) return;
    setRedeemingId(item.id);
    setError(null);
    try {
      const res = await redeemReward(base, custToken, merchantId, item.id);
      setLastVoucher(res);
      // refresh loyalty + catalog affordability
      await loadAll(custToken, merchantId);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Redemption failed");
    } finally {
      setRedeemingId(null);
    }
  }

  async function handleJackpotPlay() {
    if (!custToken || !merchantId || !jackpot || jackpotPlaying) return;
    setJackpotResult(null);
    setError(null);
    setReelsLanded(0);
    setJackpotPlaying(true);

    // Kick off both: the API call and a UX-min full-speed spin.
    const playStart = Date.now();
    const MIN_SPIN_MS = 3000;     // full-speed wheeling before reels start stopping
    const REEL_STAGGER_MS = 360;  // gap between each reel decelerating to a stop
    try {
      const res = await playJackpot(base, custToken, merchantId);
      const elapsed = Date.now() - playStart;
      const wait = Math.max(0, MIN_SPIN_MS - elapsed);

      setTimeout(() => {
        // Lock in the real result, then stop the reels left-to-right. Each reel
        // decelerates (ease-out) as it lands — classic slot-machine feel.
        setJackpotGrid(res.grid);
        setReelsLanded(1);                                   // reel 1 slows & stops
        setTimeout(() => setReelsLanded(2), REEL_STAGGER_MS); // reel 2
        setTimeout(() => {
          setReelsLanded(3);                                  // reel 3 — last to stop
          setJackpotResult(res);
          setJackpotPlaying(false);
          if (loyalty) setLoyalty({ ...loyalty, points_balance: res.points_balance });
          if (custToken && merchantId) loadAll(custToken, merchantId).catch(() => {});
        }, REEL_STAGGER_MS * 2);
      }, wait);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Jackpot play failed");
      setJackpotPlaying(false);
    }
  }

  async function handleSpin() {
    if (!custToken || !merchantId || !wheel || spinning) return;
    setSpinResult(null);
    setError(null);
    setSpinning(true);
    try {
      const res = await spinWheel(base, custToken, merchantId);
      // Compute target rotation so winning_index lands under the pointer.
      const target = wheelTargetRotation(res.winning_index, wheel.segments.length, 5, rotation);
      setRotation(target);
      // Reveal after the CSS animation (4s) completes.
      setTimeout(() => {
        setSpinResult(res);
        setSpinning(false);
        if (loyalty) setLoyalty({ ...loyalty, points_balance: res.points_balance });
        // refresh loyalty (visit/recent may update) + catalog
        if (custToken && merchantId) loadAll(custToken, merchantId).catch(() => {});
      }, 4100);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Spin failed");
      setSpinning(false);
    }
  }

  const tabBar = <CustomerTabBar token={token} active="rewards" />;

  // ── Loading: skeleton in the real layout shape ──
  if (loading) {
    return (
      <Shell>
        <header style={{ padding: "var(--space-5) var(--space-4) var(--space-4)", background: "linear-gradient(180deg, var(--brand-600), var(--brand-700))" }}>
          <Skeleton width={160} height={22} style={{ background: "rgba(255,255,255,0.25)" }} />
        </header>
        <main style={{ flex: 1, padding: "var(--space-4)" }}>
          <Card pad style={{ marginBottom: "var(--space-4)" }}>
            <Skeleton width="50%" height={14} style={{ marginBottom: 10 }} />
            <Skeleton width="40%" height={36} style={{ marginBottom: 12 }} />
            <Skeleton width="100%" height={10} />
          </Card>
          <Skeleton width="100%" height={120} radius={12} style={{ marginBottom: 12 }} />
          <Skeleton width="100%" height={280} radius={12} />
        </main>
        {tabBar}
      </Shell>
    );
  }

  // ── Logged out ──
  if (loggedOut) {
    return (
      <Shell>
        <main style={{ flex: 1, display: "flex", alignItems: "center", padding: "var(--space-5)" }}>
          <Card pad style={{ width: "100%", textAlign: "center" }}>
            <Icons.Gift size={44} color="var(--color-primary)" style={{ marginBottom: 8 }} />
            <div style={{ fontWeight: 800, fontSize: "var(--text-xl)", marginBottom: 6 }}>
              Log in to view rewards
            </div>
            <p style={{ color: "var(--color-text-muted)", marginBottom: "var(--space-4)" }}>
              Your session has expired. Log in again from the ordering page to see your coins,
              redeem rewards, and play the games.
            </p>
            <Button block variant="primary" size="lg" leftIcon={Icons.ArrowLeft} onClick={() => router.push(`/t/${encodeURIComponent(token)}`)}>
              Go to Login
            </Button>
          </Card>
        </main>
        {tabBar}
      </Shell>
    );
  }

  const progressPct =
    loyalty && loyalty.next_tier && loyalty.points_to_next_tier > 0
      ? Math.min(
          100,
          Math.round(
            (loyalty.lifetime_points /
              (loyalty.lifetime_points + loyalty.points_to_next_tier)) *
              100
          )
        )
      : 100;

  const canSpin =
    !!wheel && !!loyalty && loyalty.points_balance >= wheel.spin_cost && !spinning;

  // Jackpot reel strip: repeat the prize pool 3× so the CSS scroll loops
  // seamlessly (translating up by one third lands on an identical frame).
  const jackpotPrizes = jackpot?.prizes ?? [];
  const reelStripEmojis = [...jackpotPrizes, ...jackpotPrizes, ...jackpotPrizes].map(
    (p) => p.emoji
  );
  // Fixed trajectories for the win coin-burst (deterministic — no hydration risk).
  const burstCoins = Array.from({ length: 16 }, (_, i) => {
    const angle = (i / 16) * Math.PI * 2;
    const dist = 120 + (i % 4) * 34;
    return {
      isCoin: i % 3 !== 0, // 2/3 gold coins, 1/3 sparkles
      cx: `${Math.round(Math.cos(angle) * dist)}px`,
      cy: `${Math.round(Math.sin(angle) * dist - 40)}px`, // bias upward
      cr: `${(i % 2 ? 1 : -1) * (180 + (i % 3) * 90)}deg`,
      delay: `${(i % 5) * 0.05}s`,
    };
  });

  return (
    <Shell>
      {/* App header */}
      <header
        style={{
          padding: "var(--space-4)",
          background: "linear-gradient(180deg, var(--brand-600), var(--brand-700))",
          color: "#fff",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          <button
            onClick={() => router.push(`/t/${encodeURIComponent(token)}`)}
            aria-label="Back to menu"
            style={{ background: "rgba(255,255,255,0.18)", border: "none", borderRadius: "var(--radius-pill)", width: 36, height: 36, display: "grid", placeItems: "center", color: "#fff", cursor: "pointer" }}
          >
            <Icons.ArrowLeft size={20} />
          </button>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: "var(--text-lg)", fontWeight: 900, lineHeight: 1.1 }}>Rewards & Games</div>
            <div style={{ fontSize: "var(--text-xs)", opacity: 0.85, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {qr ? `${qr.merchant.name} · ${qr.outlet.name} · Table ${qr.table.label}` : ""}
            </div>
          </div>
          {loyalty && <CoinBalance coins={loyalty.points_balance} />}
        </div>
      </header>

      <main style={{ flex: 1, padding: "var(--space-4)", paddingBottom: "var(--space-6)" }}>
        {error && (
          <Card pad style={{ borderColor: "var(--color-danger)", color: "var(--color-danger)", marginBottom: "var(--space-3)" }}>
            {error}
          </Card>
        )}

        {/* Loyalty / coins card */}
        {loyalty && (
          <Card pad>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "var(--space-3)" }}>
              <div>
                <div style={{ fontSize: "var(--text-xs)", textTransform: "uppercase", letterSpacing: 1, color: "var(--color-text-muted)", fontWeight: 700 }}>
                  Coins Balance
                </div>
                <div style={{ fontSize: "var(--text-5xl)", fontWeight: 900, color: "var(--color-primary)", lineHeight: 1 }}>
                  {loyalty.points_balance.toLocaleString()}
                </div>
                <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginTop: 4 }}>
                  Lifetime {loyalty.lifetime_points.toLocaleString()} · {loyalty.visit_count} visits
                </div>
              </div>
              <Badge tone={TIER_TONE[loyalty.tier] ?? "warning"}>
                {loyalty.tier.charAt(0).toUpperCase() + loyalty.tier.slice(1)} Tier
              </Badge>
            </div>

            <div style={{ marginTop: "var(--space-4)" }}>
              {loyalty.next_tier ? (
                <TierProgress
                  pct={progressPct}
                  fromLabel={`${loyalty.points_to_next_tier.toLocaleString()} coins to ${loyalty.next_tier}`}
                  toLabel={`${progressPct}%`}
                />
              ) : (
                <Badge tone="success">🎉 You&apos;ve reached the top tier!</Badge>
              )}
            </div>
          </Card>
        )}

        {/* Rewards catalog */}
        <SectionTitle>Rewards Catalog</SectionTitle>

        {lastVoucher && (
          <Card pad style={{ background: "var(--color-success-bg)", borderColor: "var(--color-success)", marginBottom: "var(--space-3)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", color: "var(--color-success)", fontWeight: 700 }}>
              <Icons.Ticket size={18} /> Redeemed {lastVoucher.reward_name}!
            </div>
            <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginTop: 4 }}>
              Voucher: <code>{lastVoucher.voucher_code}</code>
            </div>
          </Card>
        )}

        {catalog.length === 0 ? (
          <Card flush>
            <EmptyState icon={Icons.Gift} title="No rewards yet">
              Earn coins on every order to unlock free treats.
            </EmptyState>
          </Card>
        ) : (
          <Card flush>
            {catalog.map((item) => (
              <ListItem
                key={item.id}
                icon={Icons.Gift}
                title={item.name}
                meta={
                  <span style={{ color: "var(--color-primary)", fontWeight: 700 }}>
                    {item.cost_points.toLocaleString()} coins
                    {item.description ? ` · ${item.description}` : ""}
                  </span>
                }
                right={
                  <Button
                    size="sm"
                    variant="accent"
                    disabled={item.can_afford === false || redeemingId === item.id}
                    onClick={() => handleRedeem(item)}
                  >
                    {redeemingId === item.id ? "…" : item.can_afford === false ? "Locked" : "Redeem"}
                  </Button>
                }
              />
            ))}
          </Card>
        )}

        {/* My Vouchers — kept with the catalog so redeem → voucher is one place */}
        {vouchers.length > 0 && (
          <>
            <SectionTitle>My Vouchers</SectionTitle>
            <Card flush>
              {vouchers.map((v) => (
                <ListItem
                  key={v.voucher_code}
                  icon={Icons.Ticket}
                  title={v.reward_name}
                  meta={<><code>{v.voucher_code}</code> · {relativeTime(v.created_at)}</>}
                  right={<Badge tone={v.status === "active" ? "success" : "default"}>{v.status}</Badge>}
                />
              ))}
            </Card>
          </>
        )}

        {/* Recent activity */}
        {loyalty && loyalty.recent.length > 0 && (
          <>
            <SectionTitle>Recent Coins Activity</SectionTitle>
            <Card flush>
              {loyalty.recent.map((txn, i) => (
                <ListItem
                  key={i}
                  icon={txn.points >= 0 ? Icons.Sparkles : Icons.Ticket}
                  title={txn.reason || txn.txn_type}
                  meta={relativeTime(txn.created_at)}
                  right={
                    <span style={{ fontWeight: 800, color: txn.points >= 0 ? "var(--color-success)" : "var(--color-danger)" }}>
                      {txn.points >= 0 ? "+" : ""}
                      {txn.points}
                    </span>
                  }
                />
              ))}
            </Card>
          </>
        )}

        {/* Spin the Wheel — matched gold cabinet, same theme as the jackpot */}
        <SectionTitle>🎡 Spin the Wheel</SectionTitle>
        <div className="game-cabinet">
          {wheel ? (
            <>
              <div className="game-cabinet-title">SPIN &amp; WIN</div>
              <Wheel segments={wheel.segments} rotation={rotation} spinning={spinning} size={300} />
              <div style={{ marginTop: "var(--space-4)" }}>
                <button className="slot-play-btn" disabled={!canSpin} onClick={handleSpin}>
                  {spinning ? "Spinning…" : `Spin · ${wheel.spin_cost} coins`}
                </button>
                {loyalty && loyalty.points_balance < wheel.spin_cost && !spinning && (
                  <div style={{ marginTop: "var(--space-2)", fontSize: "var(--text-sm)", color: "#ffd9d9" }}>
                    Not enough coins to spin.
                  </div>
                )}
              </div>
              {spinResult && (
                <div style={{ background: "linear-gradient(180deg,#fff7d6,#ffe9a8)", border: "2px solid #f4c430", borderRadius: 12, padding: 14, marginTop: "var(--space-4)", color: "#7a1f1f" }}>
                  <div style={{ fontSize: "var(--text-lg)", fontWeight: 900 }}>{spinResult.prize.label}</div>
                  {spinResult.prize.points > 0 && <div style={{ marginTop: 4, fontWeight: 700 }}>+{spinResult.prize.points} coins!</div>}
                  {spinResult.prize.voucher_code && (
                    <div style={{ marginTop: 4, fontSize: "var(--text-sm)" }}>Voucher: <code>{spinResult.prize.voucher_code}</code></div>
                  )}
                  <div style={{ marginTop: 4, fontSize: "var(--text-xs)", color: "#92400e" }}>
                    New balance: {spinResult.points_balance.toLocaleString()} coins
                  </div>
                </div>
              )}
            </>
          ) : (
            <div style={{ color: "#ffe9a8", padding: "var(--space-5)", textAlign: "center" }}>Wheel not available.</div>
          )}
        </div>

        {/* 888 Jackpot slot machine — match 3 on the middle payline to win */}
        {jackpot && jackpot.prizes.length > 0 && (
          <>
            <SectionTitle>🎰 Lucky 888 Jackpot</SectionTitle>
            <div className={`slot-machine${jackpotResult?.won && !jackpotPlaying ? " win" : ""}`}>
              {/* Coin/sparkle burst on a win */}
              {jackpotResult?.won && !jackpotPlaying && (
                <div className="slot-burst" aria-hidden>
                  {burstCoins.map((c, i) => (
                    <span
                      key={i}
                      className={`slot-coin${c.isCoin ? " gold-coin" : ""}`}
                      style={
                        {
                          "--cx": c.cx,
                          "--cy": c.cy,
                          "--cr": c.cr,
                          animationDelay: c.delay,
                        } as CSSProperties
                      }
                    >
                      {c.isCoin ? null : "✨"}
                    </span>
                  ))}
                </div>
              )}
              {/* Marquee */}
              <div className="slot-marquee">
                <p className="slot-title">GRAND JACKPOT</p>
                <div className="slot-meter">
                  <span className="gold-coin slot-meter-coin" aria-hidden />
                  <span className="slot-meter-num">{grandPrize.toLocaleString()}</span>
                </div>
                <div className="slot-bulbs">
                  {Array.from({ length: 9 }).map((_, i) => (
                    <span key={i} className="slot-bulb" style={{ animationDelay: `${(i % 3) * 0.3}s` }} />
                  ))}
                </div>
              </div>

              {/* Reels — each wheels at full speed, then decelerates to a stop
                  left-to-right (reelsLanded grows 0→3). Middle row is the payline. */}
              <div className="slot-reels">
                {[0, 1, 2].map((colIdx) => {
                  const reelSpinning = jackpotPlaying && reelsLanded <= colIdx;
                  return (
                    <div key={colIdx} className="slot-reel">
                      {reelSpinning ? (
                        <div className="slot-strip spinning" style={{ animationDuration: `${0.42 + colIdx * 0.06}s` }}>
                          {reelStripEmojis.map((emoji, i) => (
                            <div className="slot-tile" key={i}>
                              <span className="slot-cell-emoji">{emoji}</span>
                            </div>
                          ))}
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
                          {reelStripEmojis.slice(0, 4).map((emoji, i) => (
                            <div className="slot-tile" key={`d${i}`}>
                              <span className="slot-cell-emoji">{emoji}</span>
                            </div>
                          ))}
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

              {/* Play button */}
              <div className="text-center" style={{ padding: "0 18px" }}>
                <button
                  className="slot-play-btn"
                  disabled={
                    !custToken ||
                    jackpotPlaying ||
                    (jackpot.spin_cost > 0 && loyalty != null && loyalty.points_balance < jackpot.spin_cost)
                  }
                  onClick={handleJackpotPlay}
                >
                  {jackpotPlaying
                    ? "Spinning…"
                    : jackpot.spin_cost > 0
                    ? `Spin · ${jackpot.spin_cost} coins`
                    : "Spin — Free!"}
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
                        <div style={{ marginTop: 2, fontSize: 12, color: "#92400e" }}>
                          Value {formatSGD(jackpotResult.prize.item_price)} · Balance {jackpotResult.points_balance.toLocaleString()} coins
                        </div>
                      </div>
                    ) : (
                      <div style={{ color: "#ffe9a8", fontWeight: 700 }}>
                        So close — spin again!
                        <div style={{ marginTop: 2, fontSize: 12, color: "#ffd9b0", fontWeight: 500 }}>
                          Balance {jackpotResult.points_balance.toLocaleString()} coins
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Prize legend */}
              <div style={{ marginTop: 16, padding: "14px 18px 0", borderTop: "1px solid rgba(255,209,102,.25)" }}>
                <div style={{ fontSize: 12, color: "#ffd9b0", marginBottom: 8, textAlign: "center" }}>
                  Match 3 on the payline to win:
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, justifyContent: "center" }}>
                  {jackpot.prizes.map((p) => (
                    <span key={p.item_name} className="slot-legend-chip">
                      {p.emoji} {p.item_name} · {formatSGD(p.item_price)}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}
      </main>

      {tabBar}
    </Shell>
  );
}
