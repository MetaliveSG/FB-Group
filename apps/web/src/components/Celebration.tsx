"use client";

import { useEffect, useState, type CSSProperties } from "react";

// Full-screen win celebration — staggered firework bursts + falling confetti.
// Pure CSS (no library), pointer-events:none, auto-dismisses after ~4.5s.
const COLORS = ["#ffd84d", "#ff5252", "#4dd0ff", "#7CFC00", "#ff9f1c", "#ffffff"];
const BURSTS = [
  { x: "26%", y: "32%", d: 0 },
  { x: "72%", y: "26%", d: 0.3 },
  { x: "50%", y: "46%", d: 0.6 },
  { x: "38%", y: "20%", d: 0.95 },
  { x: "82%", y: "52%", d: 1.25 },
];
const PARTICLES = 16;
const CONFETTI = 26;

export default function Celebration({ show }: { show: boolean }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (!show) {
      setVisible(false);
      return;
    }
    setVisible(true);
    const id = window.setTimeout(() => setVisible(false), 4500);
    return () => window.clearTimeout(id);
  }, [show]);

  if (!visible) return null;

  return (
    <div className="celebration" aria-hidden>
      {BURSTS.map((b, bi) => (
        <div key={bi} className="fw" style={{ left: b.x, top: b.y }}>
          {Array.from({ length: PARTICLES }).map((_, i) => (
            <span
              key={i}
              className="fw__p"
              style={{
                "--a": `${(i / PARTICLES) * 360}deg`,
                background: COLORS[(bi + i) % COLORS.length],
                animationDelay: `${b.d}s`,
              } as CSSProperties}
            />
          ))}
        </div>
      ))}
      {Array.from({ length: CONFETTI }).map((_, i) => (
        <span
          key={`c${i}`}
          className="confetti"
          style={{
            left: `${(i * 3.9) % 100}%`,
            background: COLORS[i % COLORS.length],
            animationDelay: `${(i % 6) * 0.25}s`,
            animationDuration: `${2.4 + (i % 4) * 0.5}s`,
          } as CSSProperties}
        />
      ))}
    </div>
  );
}
