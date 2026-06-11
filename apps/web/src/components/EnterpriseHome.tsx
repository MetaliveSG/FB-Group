"use client";
// Enterprise corporate showcase — the landing for an enterprise/group QR (e.g. /t/node/fsg). A premium,
// deal-room-grade page: navy hero + stats, scrollable brand portfolio, "giving back" (CSR), a company
// history timeline, awards, and the outlet footprint. All content is data-driven off the resolved brand
// kit (theme.enterprise_*), so any enterprise node renders its own showcase.
import type { BrandTheme } from "@fbgroup/api-client";

const NAVY = "#16335b";
const card: React.CSSProperties = {
  background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 18,
  boxShadow: "0 1px 2px rgba(0,0,0,0.04), 0 10px 26px rgba(0,0,0,0.05)", overflow: "hidden",
};

const SectionHeader = ({ title, sub }: { title: string; sub?: string }) => (
  <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 12 }}>
    <h2 style={{ margin: 0, fontSize: 19, fontWeight: 900, color: "var(--color-text)" }}>{title}</h2>
    {sub && <span style={{ fontSize: 12.5, color: "var(--color-text-muted)", fontWeight: 600 }}>{sub}</span>}
  </div>
);

const railStyle: React.CSSProperties = { display: "flex", gap: 12, overflowX: "auto", margin: "0 -16px", padding: "2px 16px 6px", scrollbarWidth: "none" };

export default function EnterpriseHome({ theme, name, onOpenBrand }: {
  theme: BrandTheme; name: string; onOpenBrand?: (brand: string) => void;
}) {
  const stats = theme.enterprise_stats ?? [];
  const brands = theme.enterprise_brands ?? [];
  const csr = theme.enterprise_csr ?? [];
  const history = theme.enterprise_history ?? [];
  const awards = theme.enterprise_awards ?? [];

  return (
    <main style={{ minHeight: "100vh", background: "var(--color-bg)" }}>
      {/* HERO — navy corporate, logo on a white chip, headline + stats. */}
      <header style={{ position: "relative", color: "#fff", overflow: "hidden", paddingBottom: 4,
        background: `linear-gradient(162deg, #2b5688 0%, ${NAVY} 58%, #0e2747 100%)` }}>
        <div style={{ maxWidth: 480, margin: "0 auto", padding: "30px 20px 20px", textAlign: "center" }}>
          {theme.enterprise_logo_url
            ? <span style={{ display: "inline-block", background: "#fff", borderRadius: 16, padding: "10px 16px", boxShadow: "0 6px 18px rgba(0,0,0,0.25)" }}>
                <img src={theme.enterprise_logo_url} alt={name} style={{ height: 54, display: "block" }} />
              </span>
            : <h1 style={{ margin: 0, fontSize: 28, fontWeight: 900 }}>{name}</h1>}
          <p style={{ margin: "14px auto 0", fontSize: 14.5, fontWeight: 600, opacity: 0.95, maxWidth: 320, lineHeight: 1.5 }}>
            One of Singapore’s leading homegrown F&amp;B groups — quality, affordable local hawker fare.
          </p>
          {stats.length > 0 && (
            <div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 18, flexWrap: "wrap" }}>
              {stats.map((s, i) => (
                <div key={i} style={{ background: "rgba(255,255,255,0.12)", border: "1px solid rgba(255,255,255,0.18)",
                  borderRadius: 12, padding: "8px 12px", minWidth: 66 }}>
                  <div style={{ fontSize: 18, fontWeight: 900, lineHeight: 1 }}>{s.value}</div>
                  <div style={{ fontSize: 10.5, opacity: 0.85, marginTop: 3, textTransform: "uppercase", letterSpacing: 0.3 }}>{s.label}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </header>

      {/* Curved content panel overlapping the hero. */}
      <div style={{ position: "relative", zIndex: 2, marginTop: -22, background: "var(--color-bg)",
        borderTopLeftRadius: 26, borderTopRightRadius: 26, paddingTop: 22, paddingBottom: 40 }}>
        <div style={{ maxWidth: 480, margin: "0 auto", padding: "0 16px", display: "flex", flexDirection: "column", gap: 26 }}>

          {/* ABOUT */}
          {theme.enterprise_story && (
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.6, color: "var(--color-text)" }}>{theme.enterprise_story}</p>
          )}

          {/* OUR BRANDS — scrollable */}
          {brands.length > 0 && (
            <section>
              <SectionHeader title="Our brands" sub={`${brands.length}+ brands`} />
              <div style={railStyle}>
                {brands.map((b, i) => {
                  const tappable = !!onOpenBrand && !!b.node;
                  return (
                    <button key={i} type="button" disabled={!tappable}
                      onClick={() => tappable && onOpenBrand!(b.node!)}
                      style={{ ...card, flex: "0 0 116px", padding: 0, cursor: tappable ? "pointer" : "default",
                        outline: tappable ? `2px solid ${NAVY}` : "none" }}>
                      <div style={{ height: 78, display: "flex", alignItems: "center", justifyContent: "center", padding: 10, background: "#fff" }}>
                        <img src={b.logo} alt={b.name} loading="lazy" style={{ maxWidth: "100%", maxHeight: 58, objectFit: "contain" }} />
                      </div>
                      <div style={{ padding: "7px 8px", borderTop: "1px solid var(--color-border)", fontSize: 11.5, fontWeight: 700,
                        color: "var(--color-text)", textAlign: "center", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {b.name}{tappable && " ›"}
                      </div>
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          {/* GIVING BACK — CSR, scrollable cards */}
          {csr.length > 0 && (
            <section>
              <SectionHeader title="Giving back" sub="Community" />
              {theme.enterprise_csr_headline && (
                <p style={{ margin: "-4px 0 12px", fontSize: 14, fontWeight: 700, color: "var(--color-primary)" }}>{theme.enterprise_csr_headline}</p>
              )}
              <div style={railStyle}>
                {csr.map((c, i) => (
                  <article key={i} style={{ ...card, flex: "0 0 248px" }}>
                    <img src={c.image} alt={c.title} loading="lazy" style={{ width: "100%", height: 132, objectFit: "cover", display: "block", background: "var(--color-surface-alt)" }} />
                    <div style={{ padding: 12 }}>
                      <div style={{ fontSize: 11, fontWeight: 700, color: "var(--color-text-muted)" }}>{c.date}</div>
                      <div style={{ fontSize: 14.5, fontWeight: 800, color: "var(--color-text)", margin: "2px 0 5px", lineHeight: 1.25 }}>{c.title}</div>
                      <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.5, color: "var(--color-text-muted)",
                        display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{c.body}</p>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          )}

          {/* OUR HISTORY — vertical timeline */}
          {history.length > 0 && (
            <section>
              <SectionHeader title="Our story" sub="Since 1995" />
              <div style={{ position: "relative" }}>
                {history.map((h, i) => (
                  <div key={i} style={{ display: "flex", gap: 14, paddingBottom: i === history.length - 1 ? 0 : 18 }}>
                    {/* rail */}
                    <div style={{ position: "relative", flex: "0 0 52px", textAlign: "right" }}>
                      <span style={{ fontSize: 15, fontWeight: 900, color: NAVY }}>{h.year}</span>
                    </div>
                    <div style={{ position: "relative", flex: "0 0 14px" }}>
                      <span style={{ position: "absolute", top: 4, left: 3, width: 10, height: 10, borderRadius: "50%", background: NAVY, boxShadow: "0 0 0 3px rgba(22,51,91,0.15)" }} />
                      {i !== history.length - 1 && <span style={{ position: "absolute", top: 16, left: 7, bottom: -18, width: 2, background: "var(--color-border)" }} />}
                    </div>
                    {/* content */}
                    <div style={{ flex: 1, minWidth: 0, ...card, padding: 0 }}>
                      <img src={h.image} alt={h.year} loading="lazy" style={{ width: "100%", height: 116, objectFit: "cover", display: "block", background: "var(--color-surface-alt)" }} />
                      <p style={{ margin: 0, padding: "10px 12px", fontSize: 13, lineHeight: 1.5, color: "var(--color-text)" }}>{h.text}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* AWARDS */}
          {awards.length > 0 && (
            <section style={{ ...card, padding: "14px 16px" }}>
              <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 0.5, textTransform: "uppercase", color: "var(--color-text-muted)", marginBottom: 10 }}>Awards &amp; recognition</div>
              <div style={{ display: "flex", gap: 18, alignItems: "center", overflowX: "auto", scrollbarWidth: "none" }}>
                {awards.map((a, i) => <img key={i} src={a} alt="award" style={{ height: 44, flex: "0 0 auto", objectFit: "contain" }} />)}
              </div>
            </section>
          )}

          {/* FOOTPRINT */}
          {theme.enterprise_image_url && (
            <section style={card}>
              <div style={{ padding: "14px 16px 8px" }}>
                <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 0.5, textTransform: "uppercase", color: "var(--color-text-muted)" }}>Our footprint</div>
                <div style={{ fontSize: 15, fontWeight: 800, color: "var(--color-text)", marginTop: 2 }}>205+ outlets across Singapore</div>
              </div>
              <img src={theme.enterprise_image_url} alt="Outlet map" style={{ width: "100%", display: "block", background: "var(--color-surface-alt)" }} />
            </section>
          )}

          {/* FOOTER */}
          <div style={{ textAlign: "center", padding: "8px 0 4px", color: "var(--color-text-muted)" }}>
            <div style={{ fontSize: 12.5, fontWeight: 700 }}>{name} · A Taste of Home</div>
            <div style={{ fontSize: 11, opacity: 0.7, marginTop: 3 }}>Powered by CIP</div>
          </div>
        </div>
      </div>
    </main>
  );
}
