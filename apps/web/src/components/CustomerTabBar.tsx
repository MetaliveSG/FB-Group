"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BottomNav, Icons } from "./ui";
import { getCustomerToken } from "@/lib/auth";
import { getApiBase, resolveQr, getLoyalty, getWheel, getJackpot, getMyOrders } from "@/lib/api";
import type { MyOrder } from "@fbgroup/api-client";

type Tab = "menu" | "rewards" | "orders" | "me";

export default function CustomerTabBar({ token, active }: { token: string; active: Tab }) {
  const router = useRouter();
  const t = encodeURIComponent(token);

  // Badge the Rewards tab ONLY when the diner can actually play a game right now —
  // i.e. their coin balance covers the cheapest of the wheel/jackpot spin costs.
  // (Previously it badged on login alone, so users with too few coins still saw it.)
  const [canPlay, setCanPlay] = useState(false);
  // Adapt tabs to the storefront's resolved modules: Table QR off → no Menu; Engagement off → no Rewards.
  const [showMenu, setShowMenu] = useState(true);
  const [showRewards, setShowRewards] = useState(true);
  useEffect(() => {
    let cancelled = false;
    resolveQr(getApiBase(), token)
      .then((qr) => { if (!cancelled) { setShowMenu(qr.ordering_enabled !== false); setShowRewards(qr.rewards_enabled !== false); } })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [token]);
  useEffect(() => {
    const tok = getCustomerToken();
    if (!tok) return;
    let cancelled = false;
    const base = getApiBase();
    (async () => {
      try {
        const qr = await resolveQr(base, token);
        const mid = qr.merchant.id;
        const [loy, wheel, jackpot] = await Promise.all([
          getLoyalty(base, tok, mid),
          getWheel(base, tok, mid).catch(() => null),
          getJackpot(base, tok, mid).catch(() => null),
        ]);
        // Cheapest spin the diner could afford. A missing/unconfigured game is
        // un-playable (cost = Infinity), so it never triggers the badge.
        const costs = [
          wheel ? wheel.spin_cost : Infinity,
          jackpot ? jackpot.spin_cost : Infinity,
        ];
        const cheapest = Math.min(...costs);
        if (!cancelled) setCanPlay(loy.points_balance >= cheapest);
      } catch {
        if (!cancelled) setCanPlay(false);
      }
    })();
    return () => { cancelled = true; };
  }, [token]);

  // App-wide "ready to collect" notification: because this bar is on every customer page, poll the
  // diner's orders here and surface a ready SELF-PICKUP order anywhere in the app (banner + tab badge).
  const [readyOrder, setReadyOrder] = useState<MyOrder | null>(null);
  useEffect(() => {
    const tok = getCustomerToken();
    if (!tok) return;
    let cancelled = false;
    const base = getApiBase();
    const poll = async () => {
      try {
        const qr = await resolveQr(base, token);
        const orders = await getMyOrders(base, tok, qr.merchant.id);
        const ready = orders.find(
          (o) => o.status === "completed" && o.hand_off === "self_pickup" && o.fulfilment_status === "ready",
        );
        if (!cancelled) setReadyOrder(ready ?? null);
      } catch { /* transient */ }
    };
    poll();
    const iv = setInterval(poll, 12000);
    return () => { cancelled = true; clearInterval(iv); };
  }, [token]);

  // Only nudge when there's a playable game AND they're not already on Rewards.
  const showBadge = canPlay && active !== "rewards";
  const notifyReady = readyOrder && active !== "orders";   // on Orders they already see it

  return (
    <>
      {notifyReady && (
        <button
          onClick={() => router.push(`/t/${t}/orders`)}
          style={{
            position: "fixed", left: 0, right: 0, bottom: "calc(var(--bottomnav-h, 64px) + env(safe-area-inset-bottom, 0px))",
            zIndex: 60, margin: "0 auto", maxWidth: 520, width: "92%",
            background: "var(--color-success, #16a34a)", color: "#fff", border: "none", borderRadius: "var(--radius-lg, 12px)",
            padding: "12px 16px", fontWeight: 800, fontSize: "var(--text-sm)", cursor: "pointer",
            boxShadow: "0 6px 20px rgba(0,0,0,0.18)", display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
          }}
        >
          🔔 Order #{readyOrder!.id.slice(0, 8).toUpperCase()} is ready — tap to collect
        </button>
      )}
      <BottomNav
        active={active}
        items={[
          ...(showMenu ? [{ key: "menu", label: "Menu", icon: Icons.Utensils, onClick: () => router.push(`/t/${t}`) }] : []),
          ...(showRewards ? [{ key: "rewards", label: "Rewards", icon: Icons.Gift, badge: showBadge, onClick: () => router.push(`/t/${t}/rewards`) }] : []),
          { key: "orders", label: "Orders", icon: Icons.Receipt, badge: !!notifyReady, onClick: () => router.push(`/t/${t}/orders`) },
          { key: "me", label: "Me", icon: Icons.User, onClick: () => router.push(`/t/${t}/me`) },
        ]}
      />
    </>
  );
}
