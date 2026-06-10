"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { BottomNav, Icons } from "./ui";
import { getCustomerToken } from "@/lib/auth";
import { getApiBase, resolveQr, getLoyalty, getWheel, getJackpot, getMyOrders } from "@/lib/api";
import { orderNo } from "@/lib/format";
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
  const [popup, setPopup] = useState<MyOrder | null>(null);   // one-time "ready!" overlay
  const popped = useRef<Set<string>>(new Set());              // order ids we've already popped for
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
        if (cancelled) return;
        setReadyOrder(ready ?? null);
        // Pop the overlay ONCE per order the first time we see it ready (not every poll).
        if (ready && !popped.current.has(ready.id)) {
          popped.current.add(ready.id);
          setPopup(ready);
        }
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
      {/* Swinging-bell keyframe — used by the popup + the banner. */}
      <style>{"@keyframes cipBellRing{0%,60%,100%{transform:rotate(0)}5%,25%,45%{transform:rotate(16deg)}15%,35%,55%{transform:rotate(-16deg)}}"}</style>
      {/* One-time full-screen "ready to collect" popup (fires once per order; banner persists after). */}
      {popup && (
        <div
          role="dialog" aria-modal="true"
          onClick={() => setPopup(null)}
          style={{ position: "fixed", inset: 0, zIndex: 100, background: "rgba(2,6,23,0.6)", display: "flex", alignItems: "center", justifyContent: "center", padding: "var(--space-4)" }}
        >
          <div onClick={(e) => e.stopPropagation()}
            style={{ background: "#fff", borderRadius: "var(--radius-xl, 18px)", padding: "var(--space-5)", width: "100%", maxWidth: 360, textAlign: "center", boxShadow: "0 20px 60px rgba(0,0,0,0.35)" }}>
            {/* Swinging bell — rings to grab attention. */}
            <div style={{ fontSize: 48, lineHeight: 1, display: "inline-block", transformOrigin: "50% 12%", animation: "cipBellRing 1.5s ease-in-out infinite" }}>🔔</div>
            <div style={{ fontSize: "var(--text-2xl)", fontWeight: 900, marginTop: "var(--space-2)", color: "var(--color-success, #16a34a)" }}>Ready for collection!</div>
            <p style={{ color: "var(--color-text-muted)", fontSize: "var(--text-sm)", margin: "var(--space-2) 0 var(--space-4)" }}>
              Order #{orderNo(popup.id)}{popup.outlet_name ? ` · ${popup.outlet_name}` : ""} is ready — please collect from the stall.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
              <button onClick={() => { router.push(`/t/${t}/orders`); setPopup(null); }}
                style={{ width: "100%", padding: "12px 0", border: "none", borderRadius: "var(--radius-lg, 12px)", background: "var(--color-success, #16a34a)", color: "#fff", fontWeight: 800, fontSize: "var(--text-md)", cursor: "pointer" }}>
                View order
              </button>
              <button onClick={() => setPopup(null)}
                style={{ width: "100%", padding: "10px 0", border: "none", background: "none", color: "var(--color-text-muted)", fontWeight: 700, fontSize: "var(--text-sm)", cursor: "pointer" }}>
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}
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
          <span style={{ display: "inline-block", transformOrigin: "50% 12%", animation: "cipBellRing 1.5s ease-in-out infinite" }}>🔔</span>
          Order #{orderNo(readyOrder!.id)} is ready
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
