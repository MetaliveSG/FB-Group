"use client";

import { useRouter } from "next/navigation";

// The "games menu" — entry cards (one per game) that sit below the coins balance
// on the Rewards page and route to each game's own full-screen page.
const GAMES = [
  { key: "wheel", emoji: "🎡", title: "Spin the Wheel", sub: "Win coins & treats" },
  { key: "jackpot", emoji: "🎰", title: "888 Jackpot", sub: "Match 3 to win" },
];

export default function GamesMenu({ token }: { token: string }) {
  const router = useRouter();
  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "var(--space-3)" }}>
      {GAMES.map((g) => (
        <button
          key={g.key}
          onClick={() => router.push(`/t/${encodeURIComponent(token)}/games/${g.key}`)}
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 4,
            padding: "var(--space-4) var(--space-3)",
            borderRadius: "var(--radius-lg)",
            cursor: "pointer",
            color: "#fff",
            textAlign: "center",
            background: "radial-gradient(120% 100% at 50% 0%, #8e2a2a, #5a1414)",
            border: "2px solid transparent",
            backgroundClip: "padding-box",
            boxShadow: "0 0 0 2px #c8961f, 0 6px 16px rgba(0,0,0,0.3)",
          }}
        >
          <span style={{ fontSize: 36, lineHeight: 1 }}>{g.emoji}</span>
          <span style={{ fontWeight: 800, fontSize: "var(--text-base)", color: "#ffe066" }}>{g.title}</span>
          <span style={{ fontSize: "var(--text-xs)", color: "#ffd9b0" }}>{g.sub}</span>
        </button>
      ))}
    </div>
  );
}
