"use client";
// Kitchen Display (KDS) — a back-of-house screen showing the outlet's PAID, not-yet-collected
// orders as tickets, oldest-first. The kitchen advances each: Start → Ready for pick-up → Collected.
// READY = ready for the customer to collect from the stall. Preview runs in the merchant/operator
// session; the per-outlet station token is the hardening step (see CLAUDE.md "Kitchen display").
import { useCallback, useEffect, useState } from "react";
import { listKitchenOrders, advanceFulfilment, getApiBase } from "@/lib/api";
import { getStaffToken, getOperatorMerchant } from "@/lib/auth";
import type { KitchenOrder, FulfilmentStatus } from "@fbgroup/api-client";

const STATUS_STYLE: Record<FulfilmentStatus, { bg: string; bar: string; label: string }> = {
  queued: { bg: "#0f172a", bar: "#64748b", label: "NEW" },
  preparing: { bg: "#7c2d12", bar: "#f59e0b", label: "PREPARING" },
  ready: { bg: "#14532d", bar: "#22c55e", label: "READY • PICK-UP" },
  collected: { bg: "#1e293b", bar: "#334155", label: "COLLECTED" },
};

function waited(created: string): string {
  const mins = Math.max(0, Math.floor((Date.now() - new Date(created).getTime()) / 60000));
  return mins < 1 ? "just now" : `${mins} min`;
}

export default function KdsPage() {
  const base = getApiBase();
  const [mounted, setMounted] = useState(false);
  const [outletId, setOutletId] = useState<string | null>(null);
  const [orders, setOrders] = useState<KitchenOrder[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("outlet_id");
    setOutletId(q || getOperatorMerchant()?.outletId || null);
    setMounted(true);
  }, []);

  const refresh = useCallback(async () => {
    const tok = getStaffToken();
    if (!tok || !outletId) return;
    try {
      setOrders(await listKitchenOrders(base, tok, outletId));
      setErr(null);
    } catch {
      setErr("Could not load the kitchen queue.");
    }
  }, [base, outletId]);

  // Poll every 5s (a kitchen screen is always live).
  useEffect(() => {
    if (!mounted || !outletId) return;
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [mounted, outletId, refresh]);

  async function advance(o: KitchenOrder, to: FulfilmentStatus) {
    const tok = getStaffToken();
    if (!tok) return;
    setBusy(o.id);
    try {
      await advanceFulfilment(base, tok, o.id, to);
      await refresh();
    } catch {
      setErr("Could not update the ticket.");
    } finally {
      setBusy(null);
    }
  }

  if (!mounted) return null;
  if (!outletId) {
    return (
      <div style={{ minHeight: "100vh", background: "#020617", color: "#e2e8f0", display: "flex", alignItems: "center", justifyContent: "center", padding: 40, textAlign: "center" }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>Kitchen screen</h1>
          <p style={{ color: "#94a3b8", marginTop: 8 }}>Open this from a storefront — the Platform directory’s “Open Kitchen”,
            or after entering a storefront — so it knows which outlet’s orders to show.</p>
        </div>
      </div>
    );
  }

  // Two-tap flow: NEW → Ready → done. Wording follows the order's mode — a pick-up order is
  // COLLECTED by the diner; a dine-in order is SERVED by a waiter. (PREPARING still exists in the
  // model for kitchens that want a "Start" step — re-add a button to use it.)
  const nextAction = (o: KitchenOrder): { to: FulfilmentStatus; label: string } | null => {
    const pickup = o.hand_off === "self_pickup";
    switch (o.fulfilment_status) {
      case "queued":
      case "preparing": return { to: "ready", label: pickup ? "Ready for pick-up" : "Ready to serve" };
      case "ready": return { to: "collected", label: pickup ? "Collected" : "Served" };
      default: return null;
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#020617", color: "#e2e8f0", padding: "16px 18px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
        <h1 style={{ fontSize: 20, fontWeight: 800, letterSpacing: 0.3 }}>🍳 Kitchen — {orders.length} open</h1>
        <span style={{ fontSize: 12, color: "#64748b" }}>auto-refreshes · oldest first</span>
      </div>
      {err && <div style={{ background: "#7f1d1d", color: "#fecaca", padding: "8px 12px", borderRadius: 8, marginBottom: 12, fontSize: 13 }}>{err}</div>}
      {orders.length === 0 ? (
        <div style={{ color: "#64748b", padding: "60px 0", textAlign: "center", fontSize: 16 }}>No open orders. New paid orders appear here automatically.</div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
          {orders.map((o) => {
            const s = STATUS_STYLE[o.fulfilment_status];
            const adv = nextAction(o);
            const isPickup = o.hand_off === "self_pickup";
            return (
              <div key={o.id} style={{ background: s.bg, borderRadius: 12, overflow: "hidden", border: `1px solid ${s.bar}55`, display: "flex", flexDirection: "column" }}>
                <div style={{ height: 4, background: s.bar }} />
                <div style={{ padding: "10px 12px", display: "flex", flexDirection: "column", gap: 8, flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ fontWeight: 800, fontSize: 16 }}>
                      {/* 📦 package (takeaway) vs 🍽 plate (dine-in); served shows the table, self-collect the hand-off. */}
                      {o.order_type === "takeaway"
                        ? "📦 Takeaway"
                        : isPickup
                          ? "🍽 Dine-in · collect"
                          : `🍽 Table ${o.table_label ?? "—"}`}
                    </span>
                    <span style={{ fontSize: 10, fontWeight: 800, color: s.bar, letterSpacing: 0.5 }}>
                      {o.fulfilment_status === "ready" ? (isPickup ? "READY • PICK-UP" : "READY • SERVE") : s.label}
                    </span>
                  </div>
                  <div style={{ fontSize: 12, color: "#94a3b8", display: "flex", justifyContent: "space-between" }}>
                    <span>{o.customer_name ?? "Guest"}</span>
                    <span>⏱ {waited(o.created_at)}</span>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", gap: 4, paddingTop: 2 }}>
                    {o.items.map((it, i) => (
                      <div key={i} style={{ fontSize: 14 }}>
                        <span style={{ fontWeight: 800 }}>{it.quantity}×</span> {it.name_snapshot}
                        {it.modifiers.length > 0 && (
                          <div style={{ fontSize: 11, color: "#94a3b8", paddingLeft: 18 }}>
                            {it.modifiers.map((m) => m.name).join(", ")}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                  {adv && (
                    <button
                      onClick={() => advance(o, adv.to)}
                      disabled={busy === o.id}
                      style={{ marginTop: "auto", padding: "10px 0", borderRadius: 8, border: "none", fontWeight: 800, fontSize: 14,
                        background: adv.to === "ready" ? "#16a34a" : adv.to === "collected" ? "#334155" : "#f59e0b",
                        color: adv.to === "collected" ? "#e2e8f0" : "#0b1220",
                        cursor: busy === o.id ? "default" : "pointer", opacity: busy === o.id ? 0.6 : 1 }}
                    >
                      {adv.label}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
