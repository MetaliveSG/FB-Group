"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  resolveQr,
  getLoyalty,
  getMyVouchers,
  getRewardsCatalog,
  redeemReward,
  getApiBase,
  installAuthHandler,
  AUTH_LOGOUT_EVENT,
} from "@/lib/api";
import { getCustomerToken } from "@/lib/auth";
import { relativeTime } from "@/lib/format";
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
import GamesMenu from "@/components/GamesMenu";
import type {
  QrResolution,
  LoyaltySummary,
  CatalogItem,
  MyVoucher,
  RedeemResponse,
} from "@fbgroup/api-client";

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ maxWidth: 480, margin: "0 auto", minHeight: "100vh", display: "flex", flexDirection: "column", background: "var(--color-bg)" }}>
      {children}
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 style={{ fontSize: "var(--text-sm)", fontWeight: 800, letterSpacing: 1, textTransform: "uppercase", color: "var(--color-text-muted)", margin: "var(--space-5) 0 var(--space-3)" }}>
      {children}
    </h2>
  );
}

const TIER_TONE: Record<string, "gold" | "default" | "warning"> = { gold: "gold", silver: "default", bronze: "warning" };

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

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loggedOut, setLoggedOut] = useState(false);
  const [redeemingId, setRedeemingId] = useState<string | null>(null);
  const [lastVoucher, setLastVoucher] = useState<RedeemResponse | null>(null);

  const loadAll = useCallback(
    async (tok: string, mid: string) => {
      const [loy, cat, vch] = await Promise.all([
        getLoyalty(base, tok, mid),
        getRewardsCatalog(base, tok, mid),
        getMyVouchers(base, tok, mid).catch(() => []),
      ]);
      setLoyalty(loy);
      setCatalog(cat);
      setVouchers(vch);
    },
    [base]
  );

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
        setQr(data);
        setMerchantId(data.merchant.id);
        if (!tok) { setLoggedOut(true); setLoading(false); return; }
        try { await loadAll(tok, data.merchant.id); }
        catch (e: unknown) { setError(e instanceof Error ? e.message : "Failed to load rewards"); }
        finally { setLoading(false); }
      })
      .catch((e) => { setError(e.message ?? "Invalid QR token"); setLoading(false); });

    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, onLogout);
  }, [base, token, loadAll]);

  async function handleRedeem(item: CatalogItem) {
    if (!custToken || !merchantId) return;
    setRedeemingId(item.id);
    setError(null);
    try {
      const res = await redeemReward(base, custToken, merchantId, item.id);
      setLastVoucher(res);
      await loadAll(custToken, merchantId);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Redemption failed");
    } finally {
      setRedeemingId(null);
    }
  }

  const tabBar = <CustomerTabBar token={token} active="rewards" />;

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
          <Skeleton width="100%" height={96} radius={12} style={{ marginBottom: 12 }} />
          <Skeleton width="100%" height={180} radius={12} />
        </main>
        {tabBar}
      </Shell>
    );
  }

  if (loggedOut) {
    return (
      <Shell>
        <main style={{ flex: 1, display: "flex", alignItems: "center", padding: "var(--space-5)" }}>
          <Card pad style={{ width: "100%", textAlign: "center" }}>
            <Icons.Gift size={44} color="var(--color-primary)" style={{ marginBottom: 8 }} />
            <div style={{ fontWeight: 800, fontSize: "var(--text-xl)", marginBottom: 6 }}>Log in to view rewards</div>
            <p style={{ color: "var(--color-text-muted)", marginBottom: "var(--space-4)" }}>
              Log in from the ordering page to see your coins, redeem rewards, and play the games.
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
      ? Math.min(100, Math.round((loyalty.lifetime_points / (loyalty.lifetime_points + loyalty.points_to_next_tier)) * 100))
      : 100;

  return (
    <Shell>
      <header style={{ padding: "var(--space-4)", background: "linear-gradient(180deg, var(--brand-600), var(--brand-700))", color: "#fff" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          <button
            onClick={() => router.push(`/t/${encodeURIComponent(token)}`)}
            aria-label="Back to menu"
            style={{ background: "rgba(255,255,255,0.18)", border: "none", borderRadius: "var(--radius-pill)", width: 36, height: 36, display: "grid", placeItems: "center", color: "#fff", cursor: "pointer" }}
          >
            <Icons.ArrowLeft size={20} />
          </button>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: "var(--text-lg)", fontWeight: 900, lineHeight: 1.1 }}>Rewards</div>
            <div style={{ fontSize: "var(--text-xs)", opacity: 0.85, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {qr ? `${qr.merchant.name} · ${qr.outlet.name} · Table ${qr.table.label}` : ""}
            </div>
          </div>
          {loyalty && <CoinBalance coins={loyalty.points_balance} />}
        </div>
      </header>

      <main style={{ flex: 1, padding: "var(--space-4)", paddingBottom: "var(--space-6)" }}>
        {error && (
          <Card pad style={{ borderColor: "var(--color-danger)", color: "var(--color-danger)", marginBottom: "var(--space-3)" }}>{error}</Card>
        )}

        {/* Coins balance */}
        {loyalty && (
          <Card pad>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "var(--space-3)" }}>
              <div>
                <div style={{ fontSize: "var(--text-xs)", textTransform: "uppercase", letterSpacing: 1, color: "var(--color-text-muted)", fontWeight: 700 }}>Coins Balance</div>
                <div style={{ fontSize: "var(--text-5xl)", fontWeight: 900, color: "var(--color-primary)", lineHeight: 1 }}>{loyalty.points_balance.toLocaleString()}</div>
                <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginTop: 4 }}>Lifetime {loyalty.lifetime_points.toLocaleString()} · {loyalty.visit_count} visits</div>
              </div>
              <Badge tone={TIER_TONE[loyalty.tier] ?? "warning"}>{loyalty.tier.charAt(0).toUpperCase() + loyalty.tier.slice(1)} Tier</Badge>
            </div>
            <div style={{ marginTop: "var(--space-4)" }}>
              {loyalty.next_tier ? (
                <TierProgress pct={progressPct} fromLabel={`${loyalty.points_to_next_tier.toLocaleString()} coins to ${loyalty.next_tier}`} toLabel={`${progressPct}%`} />
              ) : (
                <Badge tone="success">🎉 You&apos;ve reached the top tier!</Badge>
              )}
            </div>
          </Card>
        )}

        {/* Games menu — directly below the coins balance, links to each game's page */}
        <SectionTitle>🎮 Play &amp; Win</SectionTitle>
        <GamesMenu token={token} />

        {/* Rewards catalog */}
        <SectionTitle>Rewards Catalog</SectionTitle>
        {lastVoucher && (
          <Card pad style={{ background: "var(--color-success-bg)", borderColor: "var(--color-success)", marginBottom: "var(--space-3)" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", color: "var(--color-success)", fontWeight: 700 }}>
              <Icons.Ticket size={18} /> Redeemed {lastVoucher.reward_name}!
            </div>
            <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginTop: 4 }}>Voucher: <code>{lastVoucher.voucher_code}</code></div>
          </Card>
        )}
        {catalog.length === 0 ? (
          <Card flush>
            <EmptyState icon={Icons.Gift} title="No rewards yet">Earn coins on every order to unlock free treats.</EmptyState>
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
                    {item.cost_points.toLocaleString()} coins{item.description ? ` · ${item.description}` : ""}
                  </span>
                }
                right={
                  <Button size="sm" variant="accent" disabled={item.can_afford === false || redeemingId === item.id} onClick={() => handleRedeem(item)}>
                    {redeemingId === item.id ? "…" : item.can_afford === false ? "Locked" : "Redeem"}
                  </Button>
                }
              />
            ))}
          </Card>
        )}

        {/* My Vouchers */}
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
                      {txn.points >= 0 ? "+" : ""}{txn.points}
                    </span>
                  }
                />
              ))}
            </Card>
          </>
        )}
      </main>

      {tabBar}
    </Shell>
  );
}
