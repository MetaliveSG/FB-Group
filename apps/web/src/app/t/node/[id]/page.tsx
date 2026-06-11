"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { resolveNodeBrowse, resolveNodeMenu, getApiBase } from "@/lib/api";
import BrandTheme from "@/components/BrandTheme";
import type { NodeBrowse, StallRef, Menu } from "@fbgroup/api-client";

/**
 * Node-scoped customer browse — the foodcourt "home". A content-rich landing (Chagee/Luckin-grade):
 * hero slideshow → promo → segmented cuisine filter → recommended row → all stalls → brand story →
 * get-to-know-the-enterprise → awards → footer. Everything is driven by the resolved brand kit
 * (NodeBrowse.theme), so generic nodes still render a clean default. Read-only browse.
 */

const reduceMotion = () =>
  typeof window !== "undefined" && !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

function cuisineTag(s: StallRef): string {
  const t = `${s.cuisine ?? ""} ${s.stall_name}`.toLowerCase();
  if (/noodle|mee|kway teow|pan mee|ban mee/.test(t)) return "Noodles";
  if (/bak kut teh|soup|herbal/.test(t)) return "Soups";
  if (/claypot|rice/.test(t)) return "Rice";
  if (/chendol|kacang|dessert|kopi|teh|drink|sweet/.test(t)) return "Sweets";
  return "More";
}

// ── Hero slideshow (auto-rotating; dots; reduced-motion safe) ────────────────────────────────
function HeroCarousel({ images, logo, tagline, subline, name }: {
  images: string[]; logo?: string; tagline?: string; subline?: string; name: string;
}) {
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    if (images.length <= 1 || reduceMotion()) return;
    const t = setInterval(() => setIdx((p) => (p + 1) % images.length), 4200);
    return () => clearInterval(t);
  }, [images.length]);

  return (
    <header style={{ position: "relative", color: "#fff", overflow: "hidden", height: 252 }}>
      {images.length ? images.map((src, i) => (
        <div key={i} aria-hidden style={{ position: "absolute", inset: 0, backgroundImage: `url('${src}')`,
          backgroundSize: "cover", backgroundPosition: "center 68%", opacity: i === idx ? 1 : 0, transition: "opacity 0.9s ease" }} />
      )) : <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, var(--brand-600), var(--brand-700))" }} />}
      <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, rgba(0,0,0,0.16) 0%, rgba(0,0,0,0.30) 44%, rgba(0,0,0,0.76) 100%)" }} />
      <div style={{ position: "relative", height: "100%", maxWidth: 480, margin: "0 auto", padding: "0 20px 34px",
        display: "flex", flexDirection: "column", justifyContent: "flex-end", gap: 6 }}>
        {logo
          ? <img src={logo} alt={name} style={{ height: 44, alignSelf: "flex-start", maxWidth: "64%", objectFit: "contain", filter: "drop-shadow(0 1px 5px rgba(0,0,0,0.6))" }} />
          : <h1 style={{ margin: 0, fontSize: 28, fontWeight: 900, textShadow: "0 2px 6px rgba(0,0,0,0.6)" }}>{name}</h1>}
        {tagline && <div style={{ fontSize: 14.5, fontWeight: 700, opacity: 0.97, textShadow: "0 1px 4px rgba(0,0,0,0.7)" }}>{tagline}</div>}
        {subline && <div style={{ fontSize: 12.5, opacity: 0.92, fontWeight: 600 }}>{subline}</div>}
      </div>
      {images.length > 1 && (
        <div style={{ position: "absolute", bottom: 12, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 6 }}>
          {images.map((_, i) => (
            <span key={i} style={{ width: i === idx ? 18 : 6, height: 6, borderRadius: 3, transition: "width 0.3s",
              background: i === idx ? "#fff" : "rgba(255,255,255,0.5)" }} />
          ))}
        </div>
      )}
    </header>
  );
}

// ── iOS-style segmented control ────────────────────────────────────────────────────────────
function Segmented({ options, value, onChange }: { options: string[]; value: string; onChange: (v: string) => void }) {
  return (
    <div style={{ display: "flex", gap: 4, background: "var(--color-surface-alt)", padding: 4, borderRadius: 999, overflowX: "auto" }}>
      {options.map((o) => {
        const on = value === o;
        return (
          <button key={o} type="button" onClick={() => onChange(o)}
            style={{ flex: "1 0 auto", padding: "8px 16px", borderRadius: 999, border: "none", cursor: "pointer",
              fontWeight: 700, fontSize: 13, whiteSpace: "nowrap",
              background: on ? "var(--color-surface)" : "transparent",
              color: on ? "var(--color-primary)" : "var(--color-text-muted)",
              boxShadow: on ? "0 1px 3px rgba(0,0,0,0.14)" : "none" }}>
            {o}
          </button>
        );
      })}
    </div>
  );
}

const SectionHeader = ({ title, sub }: { title: string; sub?: string }) => (
  <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 10 }}>
    <h2 style={{ margin: 0, fontSize: 18, fontWeight: 800, color: "var(--color-text)" }}>{title}</h2>
    {sub && <span style={{ fontSize: 12.5, color: "var(--color-text-muted)", fontWeight: 600 }}>{sub}</span>}
  </div>
);

const card: React.CSSProperties = {
  background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 18,
  boxShadow: "0 1px 2px rgba(0,0,0,0.04), 0 10px 26px rgba(0,0,0,0.05)", overflow: "hidden",
};

export default function NodeBrowsePage() {
  const { id } = useParams<{ id: string }>();
  const base = getApiBase();
  const [data, setData] = useState<NodeBrowse | null>(null);
  const [error, setError] = useState(false);
  const [seg, setSeg] = useState("All");
  const [openStall, setOpenStall] = useState<StallRef | null>(null);
  const [menu, setMenu] = useState<Menu | null>(null);
  const [menuLoading, setMenuLoading] = useState(false);

  useEffect(() => {
    resolveNodeBrowse(base, id)
      .then((d) => {
        setData(d);
        if (d.stalls.length === 1) selectStall(d.stalls[0]);   // single stall → straight into it
      })
      .catch(() => setError(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [base, id]);

  function selectStall(stall: StallRef) {
    if (stall.order_path) { window.location.href = stall.order_path; return; }
    setOpenStall(stall); setMenu(null); setMenuLoading(true);
    resolveNodeMenu(base, id, stall.menu_id).then(setMenu).catch(() => setMenu(null)).finally(() => setMenuLoading(false));
  }

  const theme = data?.theme;
  const heroImages = useMemo(
    () => (theme?.hero_images?.length ? theme.hero_images : theme?.hero_image_url ? [theme.hero_image_url] : []),
    [theme],
  );
  const stalls = data?.stalls ?? [];
  const segments = useMemo(() => {
    const tags = Array.from(new Set(stalls.map(cuisineTag)));
    return tags.length > 1 ? ["All", ...tags] : [];
  }, [stalls]);
  const filtered = seg === "All" ? stalls : stalls.filter((s) => cuisineTag(s) === seg);
  const recommended = useMemo(() => [...stalls].sort((a, b) => b.item_count - a.item_count).slice(0, 6), [stalls]);

  const stallRow = (s: StallRef) => (
    <button key={s.menu_id} onClick={() => selectStall(s)}
      style={{ ...card, display: "flex", alignItems: "center", gap: 14, width: "100%", textAlign: "left", padding: 12, cursor: "pointer" }}>
      {s.signboard_url
        ? <img src={s.signboard_url} alt={s.stall_name} loading="lazy" style={{ width: 64, height: 56, flexShrink: 0, objectFit: "contain", borderRadius: 12, background: "#fff", padding: 4, border: "1px solid var(--color-border)" }} />
        : <span style={{ fontSize: 30, width: 56, height: 56, borderRadius: 12, background: "var(--color-surface-alt)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{s.logo || "🍽️"}</span>}
      <span style={{ flex: 1, minWidth: 0 }}>
        <span style={{ display: "block", fontSize: 16, fontWeight: 800, color: "var(--color-text)" }}>{s.stall_name}</span>
        <span style={{ display: "block", fontSize: 13, color: "var(--color-text-muted)", marginTop: 2 }}>{s.cuisine || "Food"} · {s.item_count} item{s.item_count === 1 ? "" : "s"}</span>
      </span>
      <span style={{ fontSize: 20, color: "var(--color-text-muted)" }}>›</span>
    </button>
  );

  return (
    <main style={{ minHeight: "100vh", background: "var(--color-bg)" }}>
      <BrandTheme theme={theme} />

      <HeroCarousel images={heroImages} logo={theme?.logo_url} tagline={theme?.tagline} name={data?.name ?? "Loading…"}
        subline={data ? `${stalls.length} stall${stalls.length === 1 ? "" : "s"} · order ahead, skip the queue` : ""} />

      {/* Curved content panel overlapping the hero (the Chagee curvature). */}
      <div style={{ position: "relative", zIndex: 2, marginTop: -26, background: "var(--color-bg)",
        borderTopLeftRadius: 26, borderTopRightRadius: 26, paddingTop: 20, paddingBottom: 40 }}>
        <div style={{ maxWidth: 480, margin: "0 auto", padding: "0 16px", display: "flex", flexDirection: "column", gap: 22 }}>

          {error ? (
            <p style={{ color: "var(--color-text-muted)", textAlign: "center", marginTop: 24 }}>This location isn’t available.</p>
          ) : !data ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {[0, 1, 2].map((i) => <div key={i} style={{ height: 80, borderRadius: 16, background: "var(--color-surface-alt)" }} />)}
            </div>
          ) : (
            <>
              {/* PROMO — coins + games (our differentiator; none of the benchmarks have it) */}
              <div style={{ position: "relative", overflow: "hidden", borderRadius: 18, padding: "16px 18px", color: "#fff",
                background: "linear-gradient(120deg, var(--color-primary), #ff7a18)", boxShadow: "0 8px 22px rgba(204,0,1,0.28)" }}>
                <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 0.6, opacity: 0.92, textTransform: "uppercase" }}>Rewards</div>
                <div style={{ fontSize: 19, fontWeight: 900, marginTop: 2 }}>Earn coins &amp; spin to win 🎰</div>
                <div style={{ fontSize: 13, opacity: 0.95, marginTop: 4, maxWidth: "78%" }}>Coins at every stall · play for free vouchers &amp; the 888 jackpot.</div>
                <div aria-hidden style={{ position: "absolute", right: -8, bottom: -18, fontSize: 86, opacity: 0.18 }}>🎁</div>
              </div>

              {/* SEGMENT — cuisine filter */}
              {segments.length > 0 && <Segmented options={segments} value={seg} onChange={setSeg} />}

              {/* RECOMMENDED — horizontal scroll (only on the full list) */}
              {seg === "All" && recommended.length > 2 && (
                <section>
                  <SectionHeader title="Recommended for you" />
                  <div style={{ display: "flex", gap: 12, overflowX: "auto", margin: "0 -16px", padding: "2px 16px 4px", scrollbarWidth: "none" }}>
                    {recommended.map((s) => (
                      <button key={s.menu_id} onClick={() => selectStall(s)}
                        style={{ ...card, flex: "0 0 150px", textAlign: "left", padding: 0, cursor: "pointer" }}>
                        <div style={{ height: 96, background: "var(--color-surface-alt)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                          {s.signboard_url
                            ? <img src={s.signboard_url} alt={s.stall_name} loading="lazy" style={{ maxWidth: "82%", maxHeight: 72, objectFit: "contain" }} />
                            : <span style={{ fontSize: 40 }}>{s.logo || "🍽️"}</span>}
                        </div>
                        <div style={{ padding: "10px 12px 12px" }}>
                          <div style={{ fontSize: 14, fontWeight: 800, color: "var(--color-text)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.stall_name}</div>
                          <div style={{ fontSize: 12, color: "var(--color-text-muted)", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.cuisine || "Food"}</div>
                        </div>
                      </button>
                    ))}
                  </div>
                </section>
              )}

              {/* ALL STALLS — filtered by segment */}
              <section>
                <SectionHeader title={seg === "All" ? "All stalls" : seg} sub={`${filtered.length} stall${filtered.length === 1 ? "" : "s"}`} />
                {filtered.length === 0 ? (
                  <p style={{ color: "var(--color-text-muted)", textAlign: "center", padding: "20px 0" }}>No stalls in this category.</p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>{filtered.map(stallRow)}</div>
                )}
              </section>

              {/* BRAND STORY */}
              {theme?.story && (
                <section style={card}>
                  {theme.about_image_url && <img src={theme.about_image_url} alt="" style={{ width: "100%", height: 168, objectFit: "cover", display: "block" }} />}
                  <div style={{ padding: 16 }}>
                    <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 0.5, textTransform: "uppercase", color: "var(--color-primary)" }}>Our story</div>
                    <h3 style={{ margin: "4px 0 6px", fontSize: 18, fontWeight: 900, color: "var(--color-text)" }}>{theme.tagline || data.name}</h3>
                    <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.55, color: "var(--color-text-muted)" }}>{theme.story}</p>
                  </div>
                </section>
              )}

              {/* GET TO KNOW THE ENTERPRISE */}
              {theme?.enterprise_name && (
                <section style={card}>
                  <div style={{ padding: 16 }}>
                    <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 0.5, textTransform: "uppercase", color: "var(--color-text-muted)" }}>Get to know</div>
                    {theme.enterprise_logo_url
                      ? <img src={theme.enterprise_logo_url} alt={theme.enterprise_name} style={{ height: 36, margin: "6px 0 8px", objectFit: "contain" }} />
                      : <h3 style={{ margin: "4px 0 8px", fontSize: 18, fontWeight: 900 }}>{theme.enterprise_name}</h3>}
                    {theme.enterprise_story && <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.55, color: "var(--color-text-muted)" }}>{theme.enterprise_story}</p>}
                  </div>
                  {theme.enterprise_image_url && <img src={theme.enterprise_image_url} alt={`${theme.enterprise_name} outlets`} style={{ width: "100%", display: "block", background: "var(--color-surface-alt)" }} />}
                  {theme.enterprise_awards?.length ? (
                    <div style={{ padding: "12px 16px 16px" }}>
                      <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 0.5, textTransform: "uppercase", color: "var(--color-text-muted)", marginBottom: 8 }}>Awards &amp; recognition</div>
                      <div style={{ display: "flex", gap: 14, overflowX: "auto", alignItems: "center", scrollbarWidth: "none" }}>
                        {theme.enterprise_awards.map((a, i) => (
                          <img key={i} src={a} alt="award" style={{ height: 40, flex: "0 0 auto", objectFit: "contain", filter: "grayscale(0.1)" }} />
                        ))}
                      </div>
                    </div>
                  ) : null}
                </section>
              )}

              {/* FOOTER */}
              <div style={{ textAlign: "center", padding: "10px 0 4px", color: "var(--color-text-muted)" }}>
                <div style={{ fontSize: 12.5, fontWeight: 700 }}>🇲🇾 {stalls.length} hawker favourites · {theme?.tagline ?? "Order ahead"}</div>
                <div style={{ fontSize: 11, opacity: 0.7, marginTop: 3 }}>Powered by CIP</div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Stall menu sheet (shared-outlet stall with no dedicated page) */}
      {openStall && (
        <>
          <div onClick={() => setOpenStall(null)} style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", zIndex: 40 }} />
          <div style={{ position: "fixed", left: 0, right: 0, bottom: 0, zIndex: 41, background: "#fff",
            borderTopLeftRadius: 20, borderTopRightRadius: 20, maxHeight: "82vh", overflowY: "auto",
            boxShadow: "0 -8px 28px rgba(0,0,0,0.18)", maxWidth: 480, margin: "0 auto" }}>
            <div style={{ position: "sticky", top: 0, background: "#fff", padding: "16px 18px 10px",
              borderBottom: "1px solid var(--color-border)", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 24 }}>{openStall.logo || "🍽️"}</span>
              <span style={{ flex: 1, fontSize: 17, fontWeight: 800 }}>{openStall.stall_name}</span>
              <button onClick={() => setOpenStall(null)} aria-label="Close" style={{ background: "none", border: "none", fontSize: 24, cursor: "pointer", color: "#94a3b8", lineHeight: 1 }}>×</button>
            </div>
            <div style={{ padding: "12px 18px 28px" }}>
              {menuLoading ? <p style={{ color: "var(--color-text-muted)" }}>Loading menu…</p>
                : !menu || menu.categories.length === 0 ? <p style={{ color: "var(--color-text-muted)" }}>Menu coming soon.</p>
                : menu.categories.map((c) => (
                  <div key={c.id} style={{ marginBottom: 18 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.4, color: "var(--color-text-muted)", marginBottom: 8 }}>{c.name}</div>
                    {c.items.map((it) => (
                      <div key={it.id} style={{ display: "flex", justifyContent: "space-between", gap: 12, padding: "8px 0", borderBottom: "1px solid var(--color-border)" }}>
                        <span style={{ fontSize: 15, color: it.is_available ? "var(--color-text)" : "#94a3b8" }}>{it.name}{!it.is_available && " (sold out)"}</span>
                        <span style={{ fontSize: 15, fontWeight: 700, whiteSpace: "nowrap" }}>S${it.price.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                ))}
            </div>
          </div>
        </>
      )}
    </main>
  );
}
