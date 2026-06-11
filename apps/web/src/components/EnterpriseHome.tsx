"use client";
// Enterprise corporate showcase (e.g. /t/node/fsg) — art-directed, deal-room grade. Photography-led:
// a full-bleed heritage hero, a brand-coloured "by the numbers" band, an auto-scrolling brand strip,
// a feature-led CSR section, a slideshow "Our story" that expands to the full timeline, and an awards
// banner that links onward. All content is data-driven off the brand kit (theme.enterprise_*).
import { useEffect, useRef, useState } from "react";
import type { BrandTheme } from "@fbgroup/api-client";

const GOLD = "#e6b54e";
const SERIF = 'Georgia, "Times New Roman", serif';
const reduceMotion = () => typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

function darken(hex: string, f: number): string {
  const m = hex.replace("#", "");
  if (m.length !== 6) return hex;
  const n = parseInt(m, 16);
  if (Number.isNaN(n)) return hex;
  const c = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((x) => Math.round(x * f));
  return "#" + c.map((x) => x.toString(16).padStart(2, "0")).join("");
}

const Kicker = ({ children, light }: { children: React.ReactNode; light?: boolean }) => (
  <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 2, textTransform: "uppercase", color: light ? "rgba(255,255,255,0.7)" : GOLD }}>{children}</div>
);
const Title = ({ children }: { children: React.ReactNode }) => (
  <h2 style={{ margin: "5px 0 0", fontFamily: SERIF, fontSize: 25, fontWeight: 700, lineHeight: 1.12, color: "var(--color-text)" }}>{children}</h2>
);
const Band = ({ children, bg, pad = "30px 20px" }: { children: React.ReactNode; bg?: string; pad?: string }) => (
  <section style={{ background: bg ?? "transparent", padding: pad }}>
    <div style={{ maxWidth: 480, margin: "0 auto" }}>{children}</div>
  </section>
);
const card: React.CSSProperties = {
  background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 16,
  boxShadow: "0 1px 2px rgba(0,0,0,0.05), 0 14px 30px rgba(0,0,0,0.06)", overflow: "hidden",
};
const rail: React.CSSProperties = { display: "flex", gap: 12, overflowX: "auto", margin: "0 -20px", padding: "0 20px 6px", scrollbarWidth: "none" };

export default function EnterpriseHome({ theme, name, nodeId, onOpenBrand }: {
  theme: BrandTheme; name: string; nodeId: string; onOpenBrand?: (brand: string) => void;
}) {
  const stats = theme.enterprise_stats ?? [];
  const brands = theme.enterprise_brands ?? [];
  const csr = theme.enterprise_csr ?? [];
  const history = theme.enterprise_history ?? [];
  const awards = theme.enterprise_awards ?? [];
  const heroArt = theme.enterprise_hero_image ?? history[0]?.image ?? theme.enterprise_image_url;
  const feature = csr[0];
  const restCsr = csr.slice(1);
  const primary = theme.primary || "#cc0001";
  const deep = darken(primary, 0.55);

  // Auto-scroll the brand strip (ping-pong; pauses on touch; reduced-motion safe).
  const brandsRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = brandsRef.current;
    if (!el || reduceMotion() || brands.length <= 2) return;
    let dir = 1, paused = false, resume: ReturnType<typeof setTimeout>;
    const hold = () => { paused = true; clearTimeout(resume); resume = setTimeout(() => (paused = false), 2500); };
    el.addEventListener("pointerdown", hold);
    el.addEventListener("wheel", hold, { passive: true });
    const t = setInterval(() => {
      if (paused) return;
      const max = el.scrollWidth - el.clientWidth;
      if (max <= 0) return;
      if (el.scrollLeft >= max - 1) dir = -1; else if (el.scrollLeft <= 0) dir = 1;
      el.scrollLeft += dir;
    }, 28);
    return () => { clearInterval(t); clearTimeout(resume); el.removeEventListener("pointerdown", hold); el.removeEventListener("wheel", hold); };
  }, [brands.length]);

  // "Our story" — a slideshow banner that expands to the full timeline.
  const [storyOpen, setStoryOpen] = useState(false);
  const [storyIdx, setStoryIdx] = useState(0);
  useEffect(() => {
    if (storyOpen || history.length <= 1 || reduceMotion()) return;
    const t = setInterval(() => setStoryIdx((p) => (p + 1) % history.length), 3500);
    return () => clearInterval(t);
  }, [storyOpen, history.length]);
  const story = history[storyIdx] ?? history[0];

  return (
    <main style={{ minHeight: "100vh", background: "var(--color-bg)" }}>
      {/* ── HERO — compact light editorial masthead: text + FSG illustration + stats as one unit ── */}
      <header style={{ background: "#fff", color: "var(--color-text)", overflow: "hidden" }}>
        <div style={{ maxWidth: 480, margin: "0 auto", padding: "16px 20px 0", textAlign: "center" }}>
          {theme.enterprise_logo_url && <img src={theme.enterprise_logo_url} alt={name} style={{ height: 38, margin: "0 auto", display: "block" }} />}
          <div style={{ marginTop: 9, fontSize: 10.5, fontWeight: 800, letterSpacing: 1.8, textTransform: "uppercase", color: primary }}>Est. 1995 · Singapore</div>
          <h1 style={{ margin: "5px 0 0", fontFamily: SERIF, fontSize: 25, fontWeight: 700, lineHeight: 1.1, color: "var(--color-text)" }}>A homegrown hawker story</h1>
        </div>
        {heroArt && <img src={heroArt} alt="" style={{ width: "100%", display: "block", marginTop: 2 }} />}
        {/* stats fused directly onto the hero (no gap) → one masthead */}
        {stats.length > 0 && (
          <div style={{ background: deep, color: "#fff" }}>
            <div style={{ maxWidth: 480, margin: "0 auto", padding: "13px 18px", display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
              {stats.map((s, i) => (
                <div key={i} style={{ textAlign: "center" }}>
                  <div style={{ fontFamily: SERIF, fontSize: 21, fontWeight: 700, lineHeight: 1 }}>{s.value}</div>
                  <div style={{ fontSize: 9, opacity: 0.7, marginTop: 4, textTransform: "uppercase", letterSpacing: 0.4 }}>{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </header>

      {/* ── OUR BRANDS — auto-scroll, edge-to-edge logo tiles ─────────────────────────────────── */}
      {brands.length > 0 && (
        <Band bg="var(--color-surface-alt)" pad="26px 20px">
          <Kicker>{brands.length}+ brands, one family</Kicker>
          <Title>Our brands</Title>
          <div ref={brandsRef} style={{ ...rail, marginTop: 16 }}>
            {brands.map((b, i) => {
              const tappable = !!onOpenBrand && !!b.node;
              return (
                <button key={i} type="button" disabled={!tappable} onClick={() => tappable && onOpenBrand!(b.node!)}
                  style={{ ...card, flex: "0 0 120px", padding: 0, cursor: tappable ? "pointer" : "default", borderColor: tappable ? primary : "var(--color-border)" }}>
                  <div style={{ height: 96, background: "#fff", display: "block" }}>
                    <img src={b.logo} alt={b.name} loading="lazy" style={{ width: "100%", height: "100%", objectFit: "contain", display: "block" }} />
                  </div>
                  {tappable && <div style={{ padding: 7, background: primary, color: "#fff", fontSize: 11.5, fontWeight: 800, textAlign: "center" }}>Order now ›</div>}
                </button>
              );
            })}
          </div>
        </Band>
      )}

      {/* ── GIVING BACK — feature + rest ──────────────────────────────────────────────────────── */}
      {csr.length > 0 && (
        <Band pad="30px 20px">
          <Kicker>Community</Kicker>
          <Title>{theme.enterprise_csr_headline ?? "Giving back"}</Title>
          {feature && (
            <div style={{ ...card, marginTop: 16, position: "relative" }}>
              <img src={feature.image} alt={feature.title} loading="lazy" style={{ width: "100%", height: 196, objectFit: "cover", display: "block" }} />
              <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, padding: "26px 16px 14px", color: "#fff",
                background: "linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.78) 100%)" }}>
                <div style={{ fontSize: 11, fontWeight: 700, opacity: 0.85 }}>{feature.date}</div>
                <div style={{ fontSize: 17, fontWeight: 800, marginTop: 2 }}>{feature.title}</div>
                <p style={{ margin: "4px 0 0", fontSize: 12.5, lineHeight: 1.5, opacity: 0.92 }}>{feature.body}</p>
              </div>
            </div>
          )}
          {restCsr.length > 0 && (
            <div style={{ ...rail, marginTop: 12 }}>
              {restCsr.map((c, i) => (
                <article key={i} style={{ ...card, flex: "0 0 230px" }}>
                  <img src={c.image} alt={c.title} loading="lazy" style={{ width: "100%", height: 118, objectFit: "cover", display: "block", background: "var(--color-surface-alt)" }} />
                  <div style={{ padding: 12 }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)" }}>{c.date}</div>
                    <div style={{ fontSize: 14, fontWeight: 800, color: "var(--color-text)", margin: "2px 0 4px", lineHeight: 1.25 }}>{c.title}</div>
                    <p style={{ margin: 0, fontSize: 12, lineHeight: 1.5, color: "var(--color-text-muted)", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{c.body}</p>
                  </div>
                </article>
              ))}
            </div>
          )}
        </Band>
      )}

      {/* ── OUR STORY — slideshow banner → tap to expand the full timeline ─────────────────────── */}
      {history.length > 0 && (
        <Band bg="var(--color-surface-alt)" pad="30px 20px">
          <Kicker>Since 1995</Kicker>
          <Title>Our story</Title>
          {!storyOpen ? (
            <button type="button" onClick={() => setStoryOpen(true)}
              style={{ ...card, position: "relative", width: "100%", height: 232, padding: 0, marginTop: 16, cursor: "pointer", color: "#fff", display: "block", textAlign: "left" }}>
              {history.map((h, i) => (
                <div key={i} aria-hidden style={{ position: "absolute", inset: 0, backgroundImage: `url('${h.image}')`, backgroundSize: "cover", backgroundPosition: "center", opacity: i === storyIdx ? 1 : 0, transition: "opacity 0.8s ease" }} />
              ))}
              <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, rgba(0,0,0,0) 32%, rgba(0,0,0,0.82) 100%)" }} />
              <span style={{ position: "absolute", top: 12, right: 12, background: "rgba(0,0,0,0.45)", borderRadius: 999, padding: "5px 11px", fontSize: 11, fontWeight: 700 }}>Tap to explore ›</span>
              <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, padding: "24px 16px 18px" }}>
                <div style={{ fontFamily: SERIF, fontSize: 26, fontWeight: 700 }}>{story.year}</div>
                <p style={{ margin: "3px 0 0", fontSize: 13, lineHeight: 1.45, opacity: 0.95, display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{story.text}</p>
              </div>
              <div style={{ position: "absolute", bottom: 7, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 5 }}>
                {history.map((_, i) => <span key={i} style={{ width: i === storyIdx ? 14 : 5, height: 5, borderRadius: 3, background: i === storyIdx ? "#fff" : "rgba(255,255,255,0.5)", transition: "width 0.3s" }} />)}
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
              <button type="button" onClick={() => setStoryOpen(false)}
                style={{ marginTop: 16, width: "100%", padding: "11px 0", borderRadius: 12, border: "1px solid var(--color-border)", background: "var(--color-surface)", color: "var(--color-text-muted)", fontWeight: 700, fontSize: 13, cursor: "pointer" }}>
                Show less
              </button>
            </>
          )}
        </Band>
      )}

      {/* ── AWARDS — a banner that links onward ───────────────────────────────────────────────── */}
      {awards.length > 0 && (
        <Band pad="24px 20px 30px">
          <a href={`/t/node/${encodeURIComponent(nodeId)}/awards`}
            style={{ display: "flex", alignItems: "center", gap: 14, padding: "16px 18px", borderRadius: 16, textDecoration: "none", color: "#fff",
              background: `linear-gradient(120deg, ${primary}, ${darken(primary, 0.78)})`, boxShadow: `0 10px 26px ${darken(primary, 0.5)}44` }}>
            <div style={{ display: "flex", gap: 8 }}>
              {awards.slice(0, 2).map((a, i) => (
                <span key={i} style={{ background: "#fff", borderRadius: 9, padding: "6px 8px", display: "flex", alignItems: "center" }}>
                  <img src={a} alt="award" style={{ height: 28, display: "block" }} />
                </span>
              ))}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 15.5, fontWeight: 800 }}>Awards &amp; recognition</div>
              <div style={{ fontSize: 12, opacity: 0.9, marginTop: 2 }}>Enterprise 50 · SkillsFuture · more</div>
            </div>
            <span style={{ fontSize: 24, opacity: 0.9 }}>›</span>
          </a>
        </Band>
      )}

      {/* ── FOOTER ────────────────────────────────────────────────────────────────────────────── */}
      <div style={{ textAlign: "center", padding: "4px 0 30px", color: "var(--color-text-muted)" }}>
        <div style={{ fontSize: 12.5, fontWeight: 700 }}>{name} · A Taste of Home</div>
        <div style={{ fontSize: 11, opacity: 0.7, marginTop: 3 }}>Powered by CIP</div>
      </div>
    </main>
  );
}
