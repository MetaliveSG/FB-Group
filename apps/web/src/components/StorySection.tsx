"use client";
// "Since 1995 · Our story" — a slideshow banner that expands to the full timeline. Reused by the
// enterprise showcase AND the foodcourt home (which inherits enterprise_history via the theme cascade).
// Renders just the content (header + slideshow/timeline); the caller provides the surrounding layout.
import { useEffect, useRef, useState } from "react";
import type { BrandTheme } from "@fbgroup/api-client";

const SERIF = 'Georgia, "Times New Roman", serif';
const GOLD = "#e6b54e";
const reduceMotion = () => typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
const card: React.CSSProperties = {
  background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 16,
  boxShadow: "0 1px 2px rgba(0,0,0,0.05), 0 14px 30px rgba(0,0,0,0.06)", overflow: "hidden",
};

export default function StorySection({ theme }: { theme: BrandTheme }) {
  const history = theme.enterprise_history ?? [];
  const primary = theme.primary || "#cc0001";
  const [open, setOpen] = useState(false);
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    if (open || history.length <= 1 || reduceMotion()) return;
    const t = setInterval(() => setIdx((p) => (p + 1) % history.length), 3500);
    return () => clearInterval(t);
  }, [open, history.length]);
  const storyRef = useRef<HTMLDivElement>(null);
  const collapse = () => { setOpen(false); requestAnimationFrame(() => storyRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })); };

  if (!history.length) return null;
  const cur = history[idx] ?? history[0];

  return (
    <div ref={storyRef} style={{ scrollMarginTop: 6 }}>
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 2, textTransform: "uppercase", color: GOLD }}>Since 1995</div>
          <h2 style={{ margin: "5px 0 0", fontFamily: SERIF, fontSize: 25, fontWeight: 700, lineHeight: 1.12, color: "var(--color-text)" }}>Our story</h2>
        </div>
        {open && (
          <button type="button" onClick={collapse}
            style={{ flexShrink: 0, padding: "7px 14px", borderRadius: 999, border: "1px solid var(--color-border)", background: "var(--color-surface)", color: "var(--color-text-muted)", fontWeight: 700, fontSize: 12.5, cursor: "pointer", whiteSpace: "nowrap" }}>
            Show less ▲
          </button>
        )}
      </div>

      {!open ? (
        <button type="button" onClick={() => setOpen(true)}
          style={{ ...card, position: "relative", width: "100%", height: 232, padding: 0, marginTop: 16, cursor: "pointer", color: "#fff", display: "block", textAlign: "left" }}>
          {history.map((h, i) => (
            <div key={i} aria-hidden style={{ position: "absolute", inset: 0, backgroundImage: `url('${h.image}')`, backgroundSize: "cover", backgroundPosition: h.focus ?? "center top", opacity: i === idx ? 1 : 0, transition: "opacity 0.8s ease" }} />
          ))}
          <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, rgba(0,0,0,0) 32%, rgba(0,0,0,0.82) 100%)" }} />
          <span style={{ position: "absolute", top: 12, right: 12, background: "rgba(0,0,0,0.45)", borderRadius: 999, padding: "5px 11px", fontSize: 11, fontWeight: 700 }}>Tap to explore ›</span>
          <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, padding: "24px 16px 18px" }}>
            <div style={{ fontFamily: SERIF, fontSize: 26, fontWeight: 700 }}>{cur.year}</div>
            <p style={{ margin: "3px 0 0", fontSize: 13, lineHeight: 1.45, opacity: 0.95, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{cur.text}</p>
          </div>
          <div style={{ position: "absolute", bottom: 7, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 5 }}>
            {history.map((_, i) => <span key={i} style={{ width: i === idx ? 14 : 5, height: 5, borderRadius: 3, background: i === idx ? "#fff" : "rgba(255,255,255,0.5)", transition: "width 0.3s" }} />)}
          </div>
        </button>
      ) : (
        <>
          <div style={{ marginTop: 16 }}>
            {history.map((h, i) => (
              <div key={i} style={{ display: "flex", gap: 14, paddingBottom: i === history.length - 1 ? 0 : 20 }}>
                <div style={{ flex: "0 0 46px", position: "relative" }}>
                  <div style={{ fontFamily: SERIF, fontSize: 21, fontWeight: 700, color: primary, lineHeight: 1 }}>{h.year}</div>
                  {i !== history.length - 1 && <span style={{ position: "absolute", top: 26, left: 5, bottom: -20, width: 2, background: "var(--color-border)" }} />}
                </div>
                <div style={{ flex: 1, minWidth: 0, ...card }}>
                  <img src={h.image} alt={h.year} loading="lazy" style={{ width: "100%", height: 132, objectFit: "cover", display: "block", background: "#fff" }} />
                  <p style={{ margin: 0, padding: "11px 13px", fontSize: 13, lineHeight: 1.55, color: "var(--color-text)" }}>{h.text}</p>
                </div>
              </div>
            ))}
          </div>
          <button type="button" onClick={collapse}
            style={{ marginTop: 16, width: "100%", padding: "11px 0", borderRadius: 12, border: "1px solid var(--color-border)", background: "var(--color-surface)", color: "var(--color-text-muted)", fontWeight: 700, fontSize: 13, cursor: "pointer" }}>
            Show less ▲
          </button>
        </>
      )}
    </div>
  );
}
