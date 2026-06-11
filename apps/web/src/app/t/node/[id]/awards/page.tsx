"use client";
// Awards & recognition detail — reached from the enterprise showcase's awards banner. Lists the
// enterprise's award badges with context, themed off the node's resolved brand kit.
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { resolveNodeBrowse, getApiBase } from "@/lib/api";
import BrandTheme from "@/components/BrandTheme";
import type { NodeBrowse } from "@fbgroup/api-client";

const META: Record<string, { title: string; year: string; blurb: string }> = {
  "award-enterprise50": { title: "Enterprise 50 Award", year: "2020", blurb: "Ranked 25th in the 2020 Enterprise 50 Awards — honouring Singapore's top privately-held, locally-grown enterprises." },
  "award-skillsfuture": { title: "SkillsFuture Employer Award", year: "2020", blurb: "Recognised for investing in our people — building skills, careers and lifelong learning across the group." },
};
function metaFor(url: string) {
  const key = url.split("/").pop()?.replace(/\.\w+$/, "") ?? "";
  return META[key] ?? { title: "Award", year: "", blurb: "Recognised for excellence in food & beverage." };
}

const card: React.CSSProperties = {
  background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: 16,
  boxShadow: "0 1px 2px rgba(0,0,0,0.05), 0 12px 28px rgba(0,0,0,0.06)",
};

export default function AwardsPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [data, setData] = useState<NodeBrowse | null>(null);
  useEffect(() => { resolveNodeBrowse(getApiBase(), id).then(setData).catch(() => {}); }, [id]);

  const theme = data?.theme;
  const awards = theme?.enterprise_awards ?? [];
  const primary = theme?.primary || "#cc0001";

  return (
    <main style={{ minHeight: "100vh", background: "var(--color-bg)" }}>
      <BrandTheme theme={theme} />
      <header style={{ background: primary, color: "#fff", padding: "16px 20px 26px", borderBottomLeftRadius: 22, borderBottomRightRadius: 22 }}>
        <button onClick={() => router.back()} aria-label="Back"
          style={{ background: "rgba(255,255,255,0.18)", border: "none", color: "#fff", borderRadius: 999, width: 34, height: 34, fontSize: 20, lineHeight: 1, cursor: "pointer" }}>‹</button>
        <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 1.5, textTransform: "uppercase", opacity: 0.8, marginTop: 16 }}>{data?.name ?? ""}</div>
        <h1 style={{ margin: "4px 0 0", fontSize: 26, fontWeight: 900 }}>Awards &amp; Recognition</h1>
      </header>

      <div style={{ maxWidth: 480, margin: "0 auto", padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>
        {awards.map((a, i) => {
          const m = metaFor(a);
          return (
            <div key={i} style={{ ...card, display: "flex", gap: 16, alignItems: "center", padding: 16 }}>
              <span style={{ background: "var(--color-surface-alt)", borderRadius: 12, padding: "14px 16px", display: "flex", flex: "0 0 auto" }}>
                <img src={a} alt={m.title} style={{ height: 48, display: "block" }} />
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                {m.year && <div style={{ fontSize: 11, fontWeight: 700, color: primary }}>{m.year}</div>}
                <div style={{ fontSize: 16, fontWeight: 800, color: "var(--color-text)" }}>{m.title}</div>
                <p style={{ margin: "4px 0 0", fontSize: 13, lineHeight: 1.5, color: "var(--color-text-muted)" }}>{m.blurb}</p>
              </div>
            </div>
          );
        })}
        {!data && <p style={{ color: "var(--color-text-muted)", textAlign: "center", marginTop: 30 }}>Loading…</p>}
        {data && awards.length === 0 && <p style={{ color: "var(--color-text-muted)", textAlign: "center", marginTop: 30 }}>No awards listed.</p>}
      </div>
    </main>
  );
}
