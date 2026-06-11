"use client";
// Enterprise corporate showcase (e.g. /t/node/fsg) — art-directed, deal-room grade. Photography-led, not
// gradient-led: a full-bleed heritage hero, a dark "by the numbers" band, editorial type, and alternating
// section tones for rhythm. All content is data-driven off the brand kit (theme.enterprise_*).
import type { BrandTheme } from "@fbgroup/api-client";

const NAVY = "#16335b";
const NAVY_DEEP = "#0e2747";
const GOLD = "#d6a44c";
const SERIF = 'Georgia, "Times New Roman", serif';

const Kicker = ({ children, light }: { children: React.ReactNode; light?: boolean }) => (
  <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 2, textTransform: "uppercase", color: light ? "rgba(255,255,255,0.7)" : GOLD }}>{children}</div>
);
const Title = ({ children, light }: { children: React.ReactNode; light?: boolean }) => (
  <h2 style={{ margin: "5px 0 0", fontFamily: SERIF, fontSize: 25, fontWeight: 700, lineHeight: 1.12, color: light ? "#fff" : "var(--color-text)" }}>{children}</h2>
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

export default function EnterpriseHome({ theme, name, onOpenBrand }: {
  theme: BrandTheme; name: string; onOpenBrand?: (brand: string) => void;
}) {
  const stats = theme.enterprise_stats ?? [];
  const brands = theme.enterprise_brands ?? [];
  const csr = theme.enterprise_csr ?? [];
  const history = theme.enterprise_history ?? [];
  const awards = theme.enterprise_awards ?? [];
  const heroPhoto = history[0]?.image ?? theme.enterprise_image_url;
  const feature = csr[0];
  const restCsr = csr.slice(1);

  return (
    <main style={{ minHeight: "100vh", background: "var(--color-bg)" }}>
      {/* ── HERO — full-bleed heritage photo, cinematic gradient, editorial headline ───────────── */}
      <header style={{ position: "relative", color: "#fff", overflow: "hidden", minHeight: 420 }}>
        {heroPhoto && <div style={{ position: "absolute", inset: 0, backgroundImage: `url('${heroPhoto}')`, backgroundSize: "cover", backgroundPosition: "center", filter: "saturate(0.92)" }} />}
        <div style={{ position: "absolute", inset: 0, background: `linear-gradient(180deg, rgba(8,20,38,0.45) 0%, rgba(8,20,38,0.30) 38%, rgba(10,30,58,0.78) 78%, ${NAVY_DEEP} 100%)` }} />
        <div style={{ position: "relative", maxWidth: 480, margin: "0 auto", minHeight: 420, padding: "26px 22px 30px", display: "flex", flexDirection: "column" }}>
          {theme.enterprise_logo_url && (
            <span style={{ alignSelf: "flex-start", background: "#fff", borderRadius: 12, padding: "7px 11px", boxShadow: "0 6px 18px rgba(0,0,0,0.3)" }}>
              <img src={theme.enterprise_logo_url} alt={name} style={{ height: 40, display: "block" }} />
            </span>
          )}
          <div style={{ marginTop: "auto" }}>
            <Kicker light>Est. 1995 · Singapore</Kicker>
            <h1 style={{ margin: "8px 0 0", fontFamily: SERIF, fontSize: 34, fontWeight: 700, lineHeight: 1.08, textShadow: "0 2px 14px rgba(0,0,0,0.5)" }}>
              A homegrown<br />hawker story
            </h1>
            <p style={{ margin: "12px 0 0", fontSize: 14.5, fontWeight: 500, opacity: 0.92, maxWidth: 320, lineHeight: 1.55, textShadow: "0 1px 8px rgba(0,0,0,0.5)" }}>
              From one fishball-noodle stall to one of Singapore’s leading F&amp;B groups.
            </p>
          </div>
        </div>
      </header>

      {/* ── BY THE NUMBERS — dark band ─────────────────────────────────────────────────────────── */}
      {stats.length > 0 && (
        <section style={{ background: NAVY_DEEP, color: "#fff" }}>
          <div style={{ maxWidth: 480, margin: "0 auto", padding: "22px 20px", display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
            {stats.map((s, i) => (
              <div key={i} style={{ textAlign: "center" }}>
                <div style={{ fontFamily: SERIF, fontSize: 26, fontWeight: 700, lineHeight: 1, color: "#fff" }}>{s.value}</div>
                <div style={{ fontSize: 9.5, opacity: 0.7, marginTop: 5, textTransform: "uppercase", letterSpacing: 0.5 }}>{s.label}</div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ── ABOUT ──────────────────────────────────────────────────────────────────────────────── */}
      {theme.enterprise_story && (
        <Band pad="28px 20px 6px">
          <Kicker>Who we are</Kicker>
          <p style={{ margin: "8px 0 0", fontSize: 15, lineHeight: 1.62, color: "var(--color-text)" }}>{theme.enterprise_story}</p>
        </Band>
      )}

      {/* ── OUR BRANDS — tinted band, scrollable ───────────────────────────────────────────────── */}
      {brands.length > 0 && (
        <Band bg="var(--color-surface-alt)" pad="26px 20px">
          <Kicker>{brands.length}+ brands, one family</Kicker>
          <Title>Our brands</Title>
          <div style={{ ...rail, marginTop: 16 }}>
            {brands.map((b, i) => {
              const tappable = !!onOpenBrand && !!b.node;
              return (
                <button key={i} type="button" disabled={!tappable} onClick={() => tappable && onOpenBrand!(b.node!)}
                  style={{ ...card, flex: "0 0 124px", padding: 0, cursor: tappable ? "pointer" : "default", borderColor: tappable ? NAVY : "var(--color-border)" }}>
                  <div style={{ height: 92, display: "flex", alignItems: "center", justifyContent: "center", padding: 14, background: "#fff" }}>
                    <img src={b.logo} alt={b.name} loading="lazy" style={{ maxWidth: "100%", maxHeight: 64, objectFit: "contain" }} />
                  </div>
                  {tappable && (
                    <div style={{ padding: "8px", background: NAVY, color: "#fff", fontSize: 11.5, fontWeight: 800, textAlign: "center" }}>Order now ›</div>
                  )}
                </button>
              );
            })}
          </div>
        </Band>
      )}

      {/* ── GIVING BACK — a large feature card + the rest ──────────────────────────────────────── */}
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

      {/* ── OUR STORY — editorial timeline (big year numerals) ─────────────────────────────────── */}
      {history.length > 0 && (
        <Band bg="var(--color-surface-alt)" pad="30px 20px">
          <Kicker>Since 1995</Kicker>
          <Title>Our story</Title>
          <div style={{ marginTop: 18 }}>
            {history.map((h, i) => (
              <div key={i} style={{ display: "flex", gap: 14, paddingBottom: i === history.length - 1 ? 0 : 20 }}>
                <div style={{ flex: "0 0 46px", position: "relative" }}>
                  <div style={{ fontFamily: SERIF, fontSize: 21, fontWeight: 700, color: NAVY, lineHeight: 1 }}>{h.year}</div>
                  {i !== history.length - 1 && <span style={{ position: "absolute", top: 26, left: 5, bottom: -20, width: 2, background: "rgba(22,51,91,0.18)" }} />}
                  <span style={{ position: "absolute", top: 5, left: 1, width: 9, height: 9, borderRadius: "50%", background: NAVY, display: i === 0 ? "none" : "block" }} />
                </div>
                <div style={{ flex: 1, minWidth: 0, ...card }}>
                  <img src={h.image} alt={h.year} loading="lazy" style={{ width: "100%", height: 132, objectFit: "cover", display: "block", background: "#fff" }} />
                  <p style={{ margin: 0, padding: "11px 13px", fontSize: 13, lineHeight: 1.55, color: "var(--color-text)" }}>{h.text}</p>
                </div>
              </div>
            ))}
          </div>
        </Band>
      )}

      {/* ── AWARDS ─────────────────────────────────────────────────────────────────────────────── */}
      {awards.length > 0 && (
        <Band pad="26px 20px 10px">
          <Kicker>Awards &amp; recognition</Kicker>
          <div style={{ display: "flex", gap: 22, alignItems: "center", overflowX: "auto", marginTop: 14, scrollbarWidth: "none" }}>
            {awards.map((a, i) => <img key={i} src={a} alt="award" style={{ height: 46, flex: "0 0 auto", objectFit: "contain" }} />)}
          </div>
        </Band>
      )}

      {/* ── FOOTPRINT — dark band with the outlet map ──────────────────────────────────────────── */}
      {theme.enterprise_image_url && (
        <section style={{ background: NAVY, color: "#fff" }}>
          <div style={{ maxWidth: 480, margin: "0 auto", padding: "28px 20px 8px" }}>
            <Kicker light>Our footprint</Kicker>
            <Title light>205+ outlets, island-wide</Title>
          </div>
          <div style={{ maxWidth: 480, margin: "0 auto", padding: "16px 12px 26px" }}>
            <img src={theme.enterprise_image_url} alt="Outlet map" style={{ width: "100%", display: "block", borderRadius: 14, background: "rgba(255,255,255,0.04)" }} />
          </div>
        </section>
      )}

      {/* ── FOOTER ─────────────────────────────────────────────────────────────────────────────── */}
      <div style={{ textAlign: "center", padding: "26px 0 30px", color: "var(--color-text-muted)" }}>
        <div style={{ fontSize: 12.5, fontWeight: 700 }}>{name} · A Taste of Home</div>
        <div style={{ fontSize: 11, opacity: 0.7, marginTop: 3 }}>Powered by CIP</div>
      </div>
    </main>
  );
}
