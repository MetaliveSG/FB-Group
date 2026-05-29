"use client";

import { useRouter } from "next/navigation";
import { CoinBalance, Icons } from "./ui";

// Immersive full-screen game shell (dark casino backdrop, back button + coins,
// no tab bar). Module-scope component → stable identity (won't remount the game
// when the jackpot meter ticks every 140ms).
export default function ArcadeShell({
  token,
  title,
  coins,
  children,
}: {
  token: string;
  title: string;
  coins?: number | null;
  children: React.ReactNode;
}) {
  const router = useRouter();
  return (
    <div className="app-viewport" style={{ background: "radial-gradient(125% 90% at 50% 0%, #3a1414 0%, #1a0a0a 60%, #0d0606 100%)", display: "flex", flexDirection: "column" }}>
      <div style={{ maxWidth: 480, margin: "0 auto", width: "100%", flex: 1, display: "flex", flexDirection: "column" }}>
        <header style={{ padding: "var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
          <button
            onClick={() => router.push(`/t/${encodeURIComponent(token)}/rewards`)}
            aria-label="Back to rewards"
            style={{ background: "rgba(255,255,255,0.12)", border: "none", borderRadius: "var(--radius-pill)", width: 36, height: 36, display: "grid", placeItems: "center", color: "#fff", cursor: "pointer" }}
          >
            <Icons.ArrowLeft size={20} />
          </button>
          <div style={{ flex: 1, fontSize: "var(--text-lg)", fontWeight: 900, color: "#ffe066", letterSpacing: 1 }}>{title}</div>
          {coins != null && <CoinBalance coins={coins} />}
        </header>
        <main style={{ flex: 1, padding: "0 var(--space-4) calc(var(--space-6) + env(safe-area-inset-bottom))", display: "flex", flexDirection: "column", justifyContent: "flex-start" }}>
          {children}
        </main>
      </div>
    </div>
  );
}
