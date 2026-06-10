"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { resolveQr, getMyOrders, getOrder, getApiBase, installAuthHandler } from "@/lib/api";
import { getCustomerToken } from "@/lib/auth";
import { formatSGD, relativeTime } from "@/lib/format";
import { Card, Badge, Skeleton, EmptyState, Button, Icons } from "@/components/ui";
import CustomerTabBar from "@/components/CustomerTabBar";
import type { MyOrder, OrderOut } from "@fbgroup/api-client";

// The badge a DINER sees: once an order is paid (status=completed), show the KITCHEN/pick-up state
// (so "completed" payment doesn't masquerade as "done") — otherwise show the payment state.
function pickupBadge(o: { status: string; fulfilment_status?: string; hand_off?: string }):
  { label: string; tone: "success" | "warning" | "danger" | "default" } {
  if (o.status === "completed") {
    // Served (waiter brings it) → the diner tracks nothing → just "Paid". Self-pickup → show the journey.
    if (o.hand_off !== "self_pickup") return { label: "Paid", tone: "success" };
    // Pick-up: surface the collection journey so the diner knows when to collect.
    switch (o.fulfilment_status) {
      case "ready": return { label: "🔔 Ready for pick-up", tone: "success" };
      case "collected": return { label: "Collected", tone: "default" };
      case "preparing": return { label: "Preparing", tone: "warning" };
      default: return { label: "Order received", tone: "warning" };  // queued
    }
  }
  return { label: o.status, tone: STATUS_TONE[o.status] ?? "default" };
}

const STATUS_TONE: Record<string, "success" | "warning" | "danger" | "default"> = {
  completed: "success",
  paid: "success",
  ready: "success",
  preparing: "warning",
  accepted: "warning",
  pending: "default",
  cancelled: "danger",
  declined: "danger",
};

export default function OrdersPage() {
  const params = useParams();
  const router = useRouter();
  const token = decodeURIComponent(params.token as string);
  const base = getApiBase();

  const [orders, setOrders] = useState<MyOrder[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [loggedOut, setLoggedOut] = useState(false);
  const [merchantId, setMerchantId] = useState<string | null>(null);
  // Expand-a-card → lazily fetch its full detail (line items + cost breakdown).
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [details, setDetails] = useState<Record<string, OrderOut | "loading" | "error">>({});

  const toggleOrder = useCallback((orderId: string) => {
    setExpandedId((cur) => (cur === orderId ? null : orderId));
    setDetails((cur) => {
      if (cur[orderId]) return cur; // already fetched/loading
      const tok = getCustomerToken();
      if (!tok) return cur;
      getOrder(base, tok, orderId)
        .then((d) => setDetails((c) => ({ ...c, [orderId]: d })))
        .catch(() => setDetails((c) => ({ ...c, [orderId]: "error" })));
      return { ...cur, [orderId]: "loading" };
    });
  }, [base]);

  useEffect(() => {
    installAuthHandler();
    const tok = getCustomerToken();
    resolveQr(base, token)
      .then(async (qr) => {
        if (!tok) {
          setLoggedOut(true);
          setLoading(false);
          return;
        }
        try {
          setMerchantId(qr.merchant.id);
          setOrders(await getMyOrders(base, tok, qr.merchant.id));
        } finally {
          setLoading(false);
        }
      })
      .catch(() => setLoading(false));
  }, [base, token]);

  // Poll while the page is open so a "Ready for pick-up" appears live (every 8s).
  useEffect(() => {
    if (!merchantId) return;
    const tok = getCustomerToken();
    if (!tok) return;
    const t = setInterval(() => {
      getMyOrders(base, tok, merchantId).then(setOrders).catch(() => {});
    }, 8000);
    return () => clearInterval(t);
  }, [merchantId, base]);

  const Shell = ({ children }: { children: React.ReactNode }) => (
    <div className="t-shell">
      <header style={{ padding: "var(--space-4)", background: "linear-gradient(180deg, var(--brand-600), var(--brand-700))", color: "#fff" }}>
        <div style={{ fontSize: "var(--text-lg)", fontWeight: 900 }}>My Orders</div>
        <div style={{ fontSize: "var(--text-xs)", opacity: 0.85 }}>Your order history</div>
      </header>
      <main style={{ flex: 1, padding: "var(--space-4)", display: "flex", flexDirection: "column" }}>{children}</main>
      <CustomerTabBar token={token} active="orders" />
    </div>
  );

  if (loading) {
    return (
      <Shell>
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} width="100%" height={84} radius={12} style={{ marginBottom: 12 }} />
        ))}
      </Shell>
    );
  }

  if (loggedOut) {
    return (
      <Shell>
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <Card pad style={{ width: "100%", textAlign: "center" }}>
            <Icons.Receipt size={44} color="var(--color-primary)" style={{ marginBottom: 8 }} />
            <div style={{ fontWeight: 800, fontSize: "var(--text-lg)", marginBottom: 6 }}>Log in to see your orders</div>
            <Button block variant="primary" size="lg" leftIcon={Icons.ArrowLeft} onClick={() => router.push(`/t/${encodeURIComponent(token)}`)}>
              Go to Menu
            </Button>
          </Card>
        </div>
      </Shell>
    );
  }

  return (
    <Shell>
      {!orders || orders.length === 0 ? (
        <Card flush>
          <EmptyState icon={Icons.Receipt} title="No orders yet">
            Your past orders will show up here. Tap Menu to get started.
          </EmptyState>
        </Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
          {orders.map((o) => {
            const expanded = expandedId === o.id;
            const detail = details[o.id];
            return (
              <Card pad key={o.id}>
                <button
                  type="button"
                  onClick={() => toggleOrder(o.id)}
                  aria-expanded={expanded}
                  style={{ all: "unset", cursor: "pointer", display: "block", width: "100%" }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "var(--space-2)" }}>
                    <div style={{ fontWeight: 800 }}>Order #{o.id.slice(0, 8)}</div>
                    <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
                      {/* Keep an explicit "✓ Paid" confirmation when the badge shows the pick-up journey
                          (self-collect) instead of the word "Paid" (served orders already say "Paid"). */}
                      {o.status === "completed" && o.hand_off === "self_pickup" && (
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 2, fontSize: "var(--text-xs)", fontWeight: 700, color: "var(--color-success)" }}>
                          <Icons.Check size={13} /> Paid
                        </span>
                      )}
                      {(() => { const b = pickupBadge(o); return <Badge tone={b.tone}>{b.label}</Badge>; })()}
                      <Icons.ChevronRight
                        size={18}
                        style={{ transform: expanded ? "rotate(90deg)" : "none", transition: "transform .15s", color: "var(--color-text-muted)" }}
                      />
                    </div>
                  </div>
                  <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginTop: 4 }}>
                    {o.summary}
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginTop: "var(--space-2)" }}>
                    <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>
                      {o.outlet_name ? `${o.outlet_name} · ` : ""}{relativeTime(o.created_at)} · {o.items_count} item{o.items_count === 1 ? "" : "s"}
                    </span>
                    <span style={{ fontWeight: 800, color: "var(--color-primary)" }}>{formatSGD(o.total)}</span>
                  </div>
                </button>

                {expanded && (
                  <div style={{ marginTop: "var(--space-3)", borderTop: "1px solid var(--color-border)", paddingTop: "var(--space-3)" }}>
                    {detail === "loading" || detail === undefined ? (
                      <Skeleton width="100%" height={72} radius={8} />
                    ) : detail === "error" ? (
                      <div style={{ fontSize: "var(--text-sm)", color: "var(--color-danger)" }}>Couldn’t load details. Tap again to retry.</div>
                    ) : (
                      <>
                        {detail.items.map((it, idx) => (
                          <div key={idx} style={{ marginBottom: "var(--space-2)" }}>
                            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-sm)" }}>
                              <span><strong>{it.quantity}×</strong> {it.name_snapshot}</span>
                              <span>{formatSGD(it.line_total)}</span>
                            </div>
                            {it.modifiers && it.modifiers.length > 0 && (
                              <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", paddingLeft: 16 }}>
                                {it.modifiers.map((m, mi) => (
                                  <span key={mi}>{m.name}{m.price_delta ? ` (+${formatSGD(m.price_delta)})` : ""}{mi < it.modifiers.length - 1 ? ", " : ""}</span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                        <div style={{ borderTop: "1px dashed var(--color-border)", marginTop: "var(--space-2)", paddingTop: "var(--space-2)", fontSize: "var(--text-sm)" }}>
                          {[
                            ["Subtotal", detail.subtotal],
                            ["Service charge", detail.service_charge],
                            ["GST", detail.tax],
                          ].map(([label, val]) => (
                            <div key={label as string} style={{ display: "flex", justifyContent: "space-between", color: "var(--color-text-muted)" }}>
                              <span>{label}</span><span>{formatSGD(val as number)}</span>
                            </div>
                          ))}
                          <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 800, marginTop: 4 }}>
                            <span>Total</span><span style={{ color: "var(--color-primary)" }}>{formatSGD(detail.total)}</span>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </Shell>
  );
}
