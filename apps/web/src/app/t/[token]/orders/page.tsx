"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { resolveQr, getMyOrders, getApiBase, installAuthHandler } from "@/lib/api";
import { getCustomerToken } from "@/lib/auth";
import { formatSGD, relativeTime } from "@/lib/format";
import { Card, Badge, Skeleton, EmptyState, Button, Icons } from "@/components/ui";
import CustomerTabBar from "@/components/CustomerTabBar";
import type { MyOrder } from "@fbgroup/api-client";

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
          setOrders(await getMyOrders(base, tok, qr.merchant.id));
        } finally {
          setLoading(false);
        }
      })
      .catch(() => setLoading(false));
  }, [base, token]);

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
          {orders.map((o) => (
            <Card pad key={o.id}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "var(--space-2)" }}>
                <div style={{ fontWeight: 800 }}>Order #{o.id.slice(0, 8)}</div>
                <Badge tone={STATUS_TONE[o.status] ?? "default"}>{o.status}</Badge>
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
            </Card>
          ))}
        </div>
      )}
    </Shell>
  );
}
