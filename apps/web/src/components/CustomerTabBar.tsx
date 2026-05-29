"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { BottomNav, Icons } from "./ui";
import { getCustomerToken } from "@/lib/auth";

type Tab = "menu" | "rewards" | "orders" | "me";

export default function CustomerTabBar({ token, active }: { token: string; active: Tab }) {
  const router = useRouter();
  const t = encodeURIComponent(token);

  // Nudge logged-in diners toward the games on Rewards with a dot — unless
  // they're already on that tab.
  const [loggedIn, setLoggedIn] = useState(false);
  useEffect(() => setLoggedIn(!!getCustomerToken()), []);
  const gamesAvailable = loggedIn && active !== "rewards";

  return (
    <BottomNav
      active={active}
      items={[
        { key: "menu", label: "Menu", icon: Icons.Utensils, onClick: () => router.push(`/t/${t}`) },
        { key: "rewards", label: "Rewards", icon: Icons.Gift, badge: gamesAvailable, onClick: () => router.push(`/t/${t}/rewards`) },
        { key: "orders", label: "Orders", icon: Icons.Receipt, onClick: () => router.push(`/t/${t}/orders`) },
        { key: "me", label: "Me", icon: Icons.User, onClick: () => router.push(`/t/${t}/me`) },
      ]}
    />
  );
}
