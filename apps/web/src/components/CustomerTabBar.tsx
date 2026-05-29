"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BottomNav, Icons } from "./ui";
import { getCustomerToken } from "@/lib/auth";
import { getApiBase, resolveQr, getLoyalty, getWheel, getJackpot } from "@/lib/api";

type Tab = "menu" | "rewards" | "orders" | "me";

export default function CustomerTabBar({ token, active }: { token: string; active: Tab }) {
  const router = useRouter();
  const t = encodeURIComponent(token);

  // Badge the Rewards tab ONLY when the diner can actually play a game right now —
  // i.e. their coin balance covers the cheapest of the wheel/jackpot spin costs.
  // (Previously it badged on login alone, so users with too few coins still saw it.)
  const [canPlay, setCanPlay] = useState(false);
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

  // Only nudge when there's a playable game AND they're not already on Rewards.
  const showBadge = canPlay && active !== "rewards";

  return (
    <BottomNav
      active={active}
      items={[
        { key: "menu", label: "Menu", icon: Icons.Utensils, onClick: () => router.push(`/t/${t}`) },
        { key: "rewards", label: "Rewards", icon: Icons.Gift, badge: showBadge, onClick: () => router.push(`/t/${t}/rewards`) },
        { key: "orders", label: "Orders", icon: Icons.Receipt, onClick: () => router.push(`/t/${t}/orders`) },
        { key: "me", label: "Me", icon: Icons.User, onClick: () => router.push(`/t/${t}/me`) },
      ]}
    />
  );
}
