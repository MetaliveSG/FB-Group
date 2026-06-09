"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { resolveNodeBrowse, resolveNodeMenu, getApiBase } from "@/lib/api";
import type { NodeBrowse, StallRef, Menu } from "@fbgroup/api-client";

/**
 * Node-scoped customer browse — the "brand / group app" view. Point a QR at any member-tree node
 * (a chain/group) and see all its orderable leaf stalls; tap one to view its menu. Mobile-first,
 * thumb-friendly, token-driven. Read-only browse (the demo's group landing).
 */
export default function NodeBrowsePage() {
  const { id } = useParams<{ id: string }>();
  const base = getApiBase();
  const [data, setData] = useState<NodeBrowse | null>(null);
  const [error, setError] = useState(false);
  const [openStall, setOpenStall] = useState<StallRef | null>(null);
  const [menu, setMenu] = useState<Menu | null>(null);
  const [menuLoading, setMenuLoading] = useState(false);

  useEffect(() => {
    resolveNodeBrowse(base, id)
      .then((d) => {
        setData(d);
        // Auto-enter a lone stall ONLY when the node itself is a storefront — a GROUP/CHAIN must always
        // list its stalls (even a single child), else its QR Menu looks empty (bug: sub-group skipped its
        // one child straight into an empty menu).
        if (d.stalls.length === 1 && !d.is_group) selectStall(d.stalls[0]);
      })
      .catch(() => setError(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [base, id]);

  function selectStall(stall: StallRef) {
    // A dedicated storefront venue → go to its OWN full-ordering page (cart/checkout), the same
    // screen the storefront's QR button opens. A shared-outlet foodcourt stall (no order_path) →
    // open the read-only menu sheet in place.
    if (stall.order_path) {
      window.location.href = stall.order_path;
      return;
    }
    openMenu(stall);
  }

  function openMenu(stall: StallRef) {
    setOpenStall(stall);
    setMenu(null);
    setMenuLoading(true);
    resolveNodeMenu(base, id, stall.menu_id)
      .then(setMenu)
      .catch(() => setMenu(null))
      .finally(() => setMenuLoading(false));
  }

  return (
    <main style={{ minHeight: "100vh", background: "var(--color-bg, #f8fafc)", paddingBottom: 40 }}>
      {/* Header */}
      <header style={{ background: "var(--color-primary, #ea580c)", color: "#fff", padding: "28px 20px 22px",
                       borderBottomLeftRadius: 20, borderBottomRightRadius: 20 }}>
        <div style={{ fontSize: 12, fontWeight: 600, opacity: 0.85, letterSpacing: 0.4, textTransform: "uppercase" }}>
          {data && data.is_group && data.stalls.length > 1 ? "Group Menu" : "Menu"}
        </div>
        <h1 style={{ margin: "4px 0 0", fontSize: 24, fontWeight: 800 }}>{data?.name ?? "Loading…"}</h1>
        {data && (
          <div style={{ marginTop: 6, fontSize: 13, opacity: 0.9 }}>
            {data.stalls.length} location{data.stalls.length === 1 ? "" : "s"} · tap to order
          </div>
        )}
      </header>

      <div style={{ padding: 16, maxWidth: 480, margin: "0 auto" }}>
        {error ? (
          <p style={{ color: "var(--color-text-muted, #64748b)", textAlign: "center", marginTop: 40 }}>
            This location isn’t available.
          </p>
        ) : !data ? (
          // Skeletons
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {[0, 1, 2].map((i) => (
              <div key={i} style={{ height: 76, borderRadius: 14, background: "#e2e8f0", opacity: 0.6 }} />
            ))}
          </div>
        ) : data.stalls.length === 0 ? (
          <p style={{ color: "var(--color-text-muted, #64748b)", textAlign: "center", marginTop: 40 }}>
            No stalls open here yet.
          </p>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {data.stalls.map((s) => (
              <button
                key={s.menu_id}
                onClick={() => selectStall(s)}
                style={{
                  display: "flex", alignItems: "center", gap: 14, width: "100%", textAlign: "left",
                  background: "#fff", border: "1px solid var(--color-border, #e5e7eb)", borderRadius: 14,
                  padding: 14, cursor: "pointer", boxShadow: "0 1px 2px rgba(0,0,0,0.04)",
                }}
              >
                <span style={{ fontSize: 30, width: 48, height: 48, borderRadius: 12, background: "#f1f5f9",
                               display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  {s.logo || "🍽️"}
                </span>
                <span style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ display: "block", fontSize: 16, fontWeight: 700, color: "var(--color-text, #0f172a)" }}>
                    {s.stall_name}
                  </span>
                  <span style={{ display: "block", fontSize: 13, color: "var(--color-text-muted, #64748b)", marginTop: 2 }}>
                    {s.cuisine || "Food"} · {s.item_count} item{s.item_count === 1 ? "" : "s"}
                  </span>
                </span>
                <span style={{ fontSize: 20, color: "var(--color-text-muted, #94a3b8)" }}>›</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Stall menu sheet */}
      {openStall && (
        <>
          <div onClick={() => setOpenStall(null)}
               style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", zIndex: 40 }} />
          <div style={{ position: "fixed", left: 0, right: 0, bottom: 0, zIndex: 41, background: "#fff",
                        borderTopLeftRadius: 20, borderTopRightRadius: 20, maxHeight: "82vh", overflowY: "auto",
                        boxShadow: "0 -8px 28px rgba(0,0,0,0.18)", maxWidth: 480, margin: "0 auto" }}>
            <div style={{ position: "sticky", top: 0, background: "#fff", padding: "16px 18px 10px",
                          borderBottom: "1px solid var(--color-border,#eef2f7)", display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontSize: 24 }}>{openStall.logo || "🍽️"}</span>
              <span style={{ flex: 1, fontSize: 17, fontWeight: 800 }}>{openStall.stall_name}</span>
              <button onClick={() => setOpenStall(null)} aria-label="Close"
                      style={{ background: "none", border: "none", fontSize: 24, cursor: "pointer", color: "#94a3b8", lineHeight: 1 }}>×</button>
            </div>
            <div style={{ padding: "12px 18px 28px" }}>
              {menuLoading ? (
                <p style={{ color: "var(--color-text-muted,#64748b)" }}>Loading menu…</p>
              ) : !menu || menu.categories.length === 0 ? (
                <p style={{ color: "var(--color-text-muted,#64748b)" }}>Menu coming soon.</p>
              ) : (
                menu.categories.map((c) => (
                  <div key={c.id} style={{ marginBottom: 18 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: 0.4,
                                  color: "var(--color-text-muted,#64748b)", marginBottom: 8 }}>{c.name}</div>
                    {c.items.map((it) => (
                      <div key={it.id} style={{ display: "flex", justifyContent: "space-between", gap: 12,
                                                padding: "8px 0", borderBottom: "1px solid #f1f5f9" }}>
                        <span style={{ fontSize: 15, color: it.is_available ? "var(--color-text,#0f172a)" : "#94a3b8" }}>
                          {it.name}{!it.is_available && " (sold out)"}
                        </span>
                        <span style={{ fontSize: 15, fontWeight: 600, whiteSpace: "nowrap" }}>
                          S${it.price.toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </main>
  );
}
