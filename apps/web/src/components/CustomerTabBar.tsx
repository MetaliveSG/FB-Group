"use client";

import { useRouter } from "next/navigation";
import { BottomNav, Icons } from "./ui";

type Tab = "menu" | "rewards" | "orders" | "me";

export default function CustomerTabBar({ token, active }: { token: string; active: Tab }) {
  const router = useRouter();
  const t = encodeURIComponent(token);
  return (
    <BottomNav
      active={active}
      items={[
        { key: "menu", label: "Menu", icon: Icons.Utensils, onClick: () => router.push(`/t/${t}`) },
        { key: "rewards", label: "Rewards", icon: Icons.Gift, onClick: () => router.push(`/t/${t}/rewards`) },
        { key: "orders", label: "Orders", icon: Icons.Receipt, onClick: () => router.push(`/t/${t}/orders`) },
        { key: "me", label: "Me", icon: Icons.User, onClick: () => router.push(`/t/${t}/me`) },
      ]}
    />
  );
}
