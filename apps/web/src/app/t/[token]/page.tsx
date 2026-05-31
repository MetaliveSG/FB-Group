"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  resolveQr,
  resolveStallMenu,
  otpRequest,
  otpVerify,
  createOrder,
  checkout,
  getApiBase,
  installAuthHandler,
  AUTH_LOGOUT_EVENT,
} from "@/lib/api";
import {
  getCustomerToken,
  setCustomerToken,
  setCustomerRefreshToken,
  getCustomerData,
  setCustomerData,
} from "@/lib/auth";
import { formatSGD } from "@/lib/format";
import { filterMenuItems } from "@/lib/menu";
import { Button, Card, Sheet, EmptyState, Skeleton, Icons } from "@/components/ui";
import CustomerTabBar from "@/components/CustomerTabBar";
import MenuCategoryNav from "@/components/MenuCategoryNav";
import CustomiseSheet from "@/components/CustomiseSheet";
import CountrySelect, { DEFAULT_REGION } from "@/components/CountrySelect";
import StallDirectory from "@/components/StallDirectory";
import type {
  QrResolution,
  Menu,
  MenuItem,
  MenuCategory,
  StallRef,
  OrderOut,
  CheckoutResponse,
  PaymentMethod,
} from "@fbgroup/api-client";

// ─── Types ────────────────────────────────────────────────────

interface CartEntry {
  item: MenuItem;
  quantity: number;
  selectedModifierIds: string[];
}

type AppStep =
  | "loading"
  | "menu"
  | "auth"
  | "ordering"
  | "order-placed"
  | "payment"
  | "success"
  | "error";

// ─── Helpers ─────────────────────────────────────────────────

function cartEntryTotal(entry: CartEntry): number {
  const modSum = entry.item.modifiers
    .filter((m) => entry.selectedModifierIds.includes(m.id))
    .reduce((s, m) => s + m.price_delta, 0);
  return (entry.item.price + modSum) * entry.quantity;
}
function cartTotal(cart: CartEntry[]): number {
  return cart.reduce((s, e) => s + cartEntryTotal(e), 0);
}
function cartCount(cart: CartEntry[]): number {
  return cart.reduce((s, e) => s + e.quantity, 0);
}

const Shell = ({ children }: { children: React.ReactNode }) => (
  <div className="t-shell">
    {children}
  </div>
);

function Banner({ qr, right }: { qr: QrResolution | null; right?: React.ReactNode }) {
  return (
    <header style={{ padding: "var(--space-4)", background: "linear-gradient(180deg, var(--brand-600), var(--brand-700))", color: "#fff" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "var(--text-lg)", fontWeight: 900, lineHeight: 1.15, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{qr?.merchant.name ?? "Menu"}</div>
          <div style={{ fontSize: "var(--text-xs)", opacity: 0.85, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {qr ? `${qr.outlet.name} · Table ${qr.table.label}` : ""}
          </div>
        </div>
        {right && <div style={{ flexShrink: 0 }}>{right}</div>}
      </div>
    </header>
  );
}

// ─── Menu item card ───────────────────────────────────────────

function MenuItemCard({
  item,
  onAdd,
  onCustomise,
}: {
  item: MenuItem;
  onAdd: (item: MenuItem, modifierIds: string[], qty: number) => void;
  onCustomise: (item: MenuItem) => void;
}) {
  const available = item.is_available;
  const hasOptions = item.modifiers.length > 0;

  return (
    <Card pad style={{ marginBottom: "var(--space-3)", opacity: available ? 1 : 0.55 }}>
      <div style={{ display: "flex", gap: "var(--space-3)", alignItems: "center" }}>
        {item.image_url && (
          <img
            src={item.image_url}
            alt={item.name}
            loading="lazy"
            style={{
              width: 84,
              height: 84,
              flexShrink: 0,
              objectFit: "cover",
              borderRadius: "var(--radius-md)",
              background: "var(--color-surface-2, #f1f1f1)",
            }}
          />
        )}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: "var(--text-base)" }}>{item.name}</div>
          {item.description && item.description !== item.name && (
            <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>{item.description}</div>
          )}
          <div style={{ marginTop: 6, fontWeight: 800, color: "var(--color-primary)" }}>
            {formatSGD(item.price)}
            {hasOptions && (
              <span style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginLeft: 6, fontWeight: 400 }}>+ options</span>
            )}
          </div>
        </div>
        <Button
          size="sm"
          variant="primary"
          leftIcon={Icons.Plus}
          disabled={!available}
          style={{ flexShrink: 0, alignSelf: "center" }}
          aria-label={hasOptions ? `Customise ${item.name}` : `Add ${item.name}`}
          onClick={() => (hasOptions ? onCustomise(item) : onAdd(item, [], 1))}
        >
          {available ? "Add" : "Sold out"}
        </Button>
      </div>
    </Card>
  );
}

// ─── OTP login ────────────────────────────────────────────────

function OtpPanel({ onSuccess }: { onSuccess: (token: string, customer: Record<string, unknown>) => void }) {
  const base = getApiBase();
  const [phone, setPhone] = useState("");
  const [region, setRegion] = useState(DEFAULT_REGION);
  const [code, setCode] = useState("");
  const [fullName, setFullName] = useState("");
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [debugCode, setDebugCode] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function requestOtp(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await otpRequest(base, phone, region);
      if (res.debug_code) {
        setDebugCode(res.debug_code);
        setCode(res.debug_code);
      }
      setStep("code");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to send OTP");
    } finally {
      setLoading(false);
    }
  }

  async function verifyOtp(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await otpVerify(base, phone, code, fullName || undefined, region);
      setCustomerToken(res.access_token);
      setCustomerRefreshToken(res.refresh_token);
      if (res.customer) setCustomerData(res.customer as Record<string, unknown>);
      onSuccess(res.access_token, (res.customer as Record<string, unknown>) ?? {});
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "OTP verification failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card pad>
      <div style={{ fontSize: "var(--text-xl)", fontWeight: 800, marginBottom: "var(--space-3)" }}>Log in to order</div>
      {error && (
        <div style={{ color: "var(--color-danger)", fontSize: "var(--text-sm)", marginBottom: "var(--space-3)" }}>{error}</div>
      )}
      {step === "phone" ? (
        <form onSubmit={requestOtp}>
          <div className="form-group">
            <label>Mobile Number</label>
            <div className="phone-row">
              <CountrySelect region={region} onChange={setRegion} disabled={loading} />
              <input type="tel" inputMode="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="9123 4567" required />
            </div>
          </div>
          <Button block variant="primary" size="lg" type="submit" loading={loading}>Send OTP</Button>
        </form>
      ) : (
        <form onSubmit={verifyOtp}>
          <div className="form-group">
            <label>Your Name (optional)</label>
            <input type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="e.g. Jane Tan" />
          </div>
          <div className="form-group">
            <label>OTP Code</label>
            <input type="text" value={code} onChange={(e) => setCode(e.target.value)} placeholder="6-digit code" required />
          </div>
          {debugCode && (
            <div style={{ background: "var(--color-info-bg)", color: "var(--color-info)", padding: "var(--space-2) var(--space-3)", borderRadius: "var(--radius)", fontSize: "var(--text-sm)", marginBottom: "var(--space-3)" }}>
              Dev mode — OTP auto-filled: <strong>{debugCode}</strong>
            </div>
          )}
          <Button block variant="primary" size="lg" type="submit" loading={loading}>Verify &amp; Login</Button>
          <div style={{ height: "var(--space-2)" }} />
          <Button block variant="ghost" type="button" onClick={() => setStep("phone")}>Back</Button>
        </form>
      )}
    </Card>
  );
}

// ─── Main Page ─────────────────────────────────────────────────

export default function TablePage() {
  const params = useParams();
  const router = useRouter();
  const token = decodeURIComponent(params.token as string);
  const base = getApiBase();

  const [step, setStep] = useState<AppStep>("loading");
  const [qrData, setQrData] = useState<QrResolution | null>(null);
  const [cart, setCart] = useState<CartEntry[]>([]);
  const [cartOpen, setCartOpen] = useState(false);
  const [resumeCheckout, setResumeCheckout] = useState(false);
  const [search, setSearch] = useState("");
  const [activeCat, setActiveCat] = useState<string | null>(null);
  const [customiseItem, setCustomiseItem] = useState<MenuItem | null>(null);
  // Foodcourt: which stall (menu) is being browsed, and its fetched full menu.
  const [selectedStall, setSelectedStall] = useState<StallRef | null>(null);
  const [stallMenu, setStallMenu] = useState<Menu | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [customerToken, setCustomerTokenState] = useState<string | null>(null);
  const [customerName, setCustomerName] = useState<string | null>(null);
  const [order, setOrder] = useState<OrderOut | null>(null);
  const [checkoutResult, setCheckoutResult] = useState<CheckoutResponse | null>(null);
  const [selectedPayment, setSelectedPayment] = useState<PaymentMethod>("card");
  const [forceOutcome, setForceOutcome] = useState<string>("");
  const [placingOrder, setPlacingOrder] = useState(false);
  const [checkingOut, setCheckingOut] = useState(false);

  useEffect(() => {
    installAuthHandler();

    const stored = getCustomerToken();
    if (stored) {
      setCustomerTokenState(stored);
      const data = getCustomerData();
      if (data?.full_name) setCustomerName(data.full_name as string);
    }

    function onLogout(e: Event) {
      const detail = (e as CustomEvent).detail as { actor?: string } | undefined;
      if (detail?.actor && detail.actor !== "customer") return;
      setCustomerTokenState(null);
      setCustomerName(null);
      setError("Your session expired — please log in again to continue.");
      setStep((prev) => (prev === "success" ? prev : "auth"));
    }
    window.addEventListener(AUTH_LOGOUT_EVENT, onLogout);

    resolveQr(base, token)
      .then((data) => {
        setQrData(data);
        setStep((prev) => (prev === "auth" ? prev : "menu"));
      })
      .catch((err) => {
        setError(err.message ?? "Invalid QR token");
        setStep("error");
      });

    return () => window.removeEventListener(AUTH_LOGOUT_EVENT, onLogout);
  }, [token, base]);

  // Persist the cart per QR token so it survives tab switches (Rewards/Orders/Me
  // unmount this page) and refreshes. Load once on mount; save on change. The
  // skip-first-write guard stops the empty initial state from clobbering a stored
  // cart before the load effect runs.
  const cartKey = `fbcart:${token}`;
  const cartLoaded = useRef(false);
  useEffect(() => {
    try {
      const raw = localStorage.getItem(cartKey);
      if (raw) setCart(JSON.parse(raw) as CartEntry[]);
    } catch { /* ignore corrupt/unavailable storage */ }
  }, [cartKey]);
  useEffect(() => {
    if (!cartLoaded.current) { cartLoaded.current = true; return; }
    try { localStorage.setItem(cartKey, JSON.stringify(cart)); } catch { /* quota/private mode */ }
  }, [cart, cartKey]);

  // The menu currently shown: a single-stall outlet's inline menu, or the fetched
  // menu of the stall the diner tapped in a foodcourt.
  const activeMenu: Menu | null = stallMenu ?? qrData?.menu ?? null;
  // Scroll-spy: highlight the category whose section is nearest the top of the
  // viewport (under the sticky header + category bar). Re-arms when the menu data
  // loads or search is cleared (no sections while searching).
  const categories = activeMenu?.categories ?? [];
  useEffect(() => {
    if (step !== "menu" || search || categories.length < 2) return;
    setActiveCat((prev) => prev ?? categories[0]?.id ?? null);
    const obs = new IntersectionObserver(
      (entries) => {
        const top = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (top) setActiveCat(top.target.getAttribute("data-cat"));
      },
      { rootMargin: "-120px 0px -65% 0px", threshold: 0 }
    );
    categories.forEach((c) => {
      const el = document.getElementById(`menu-cat-${c.id}`);
      if (el) obs.observe(el);
    });
    return () => obs.disconnect();
  }, [step, search, qrData, stallMenu]);

  // Foodcourt: open a stall → fetch its full menu, reset menu-local UI state.
  const selectStall = useCallback((stall: StallRef) => {
    setSelectedStall(stall);
    setStallMenu(null);
    setSearch("");
    setActiveCat(null);
    resolveStallMenu(base, token, stall.menu_id).then(setStallMenu).catch(() => setStallMenu(null));
  }, [base, token]);

  const backToStalls = useCallback(() => {
    setSelectedStall(null);
    setStallMenu(null);
    setSearch("");
  }, []);

  const scrollToCat = useCallback((id: string) => {
    setActiveCat(id);
    document.getElementById(`menu-cat-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const addToCart = useCallback((item: MenuItem, modifierIds: string[], qty: number = 1) => {
    const addQty = Math.max(1, qty);
    setCart((prev) => {
      const existingIdx = prev.findIndex(
        (e) =>
          e.item.id === item.id &&
          JSON.stringify([...e.selectedModifierIds].sort()) === JSON.stringify([...modifierIds].sort())
      );
      if (existingIdx >= 0) {
        const updated = [...prev];
        updated[existingIdx] = { ...updated[existingIdx], quantity: updated[existingIdx].quantity + addQty };
        return updated;
      }
      return [...prev, { item, quantity: addQty, selectedModifierIds: modifierIds }];
    });
  }, []);

  const removeFromCart = useCallback((idx: number) => {
    setCart((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  async function placeOrder() {
    if (!customerToken || !qrData || cart.length === 0) return;
    setPlacingOrder(true);
    setError(null);
    try {
      const items = cart.map((e) => ({ menu_item_id: e.item.id, quantity: e.quantity, modifier_ids: e.selectedModifierIds }));
      const orderRes = await createOrder(base, customerToken, { qr_token: token, items, order_type: "dine_in" });
      setOrder(orderRes);
      setCartOpen(false);
      setStep("payment");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to place order");
    } finally {
      setPlacingOrder(false);
    }
  }

  async function doCheckout() {
    if (!customerToken || !order) return;
    setCheckingOut(true);
    setError(null);
    try {
      const result = await checkout(base, customerToken, order.id, selectedPayment, forceOutcome || undefined);
      setCheckoutResult(result);
      setCart([]);  // order is paid — clear the (persisted) cart
      setStep("success");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setCheckingOut(false);
    }
  }

  // ── Loading ──
  if (step === "loading") {
    return (
      <Shell>
        <Banner qr={null} />
        <main style={{ flex: 1, padding: "var(--space-4)", color: "var(--color-text-muted)" }}>Loading menu…</main>
        <CustomerTabBar token={token} active="menu" />
      </Shell>
    );
  }

  // ── Error ──
  if (step === "error") {
    return (
      <Shell>
        <main style={{ flex: 1, display: "flex", alignItems: "center", padding: "var(--space-5)" }}>
          <Card pad style={{ width: "100%", textAlign: "center" }}>
            <Icons.X size={44} color="var(--color-danger)" style={{ marginBottom: 8 }} />
            <div style={{ fontWeight: 800, fontSize: "var(--text-lg)", marginBottom: 6 }}>Something went wrong</div>
            <p style={{ color: "var(--color-text-muted)", marginBottom: "var(--space-4)" }}>{error}</p>
            <Button block variant="primary" onClick={() => router.push("/")}>Back to Home</Button>
          </Card>
        </main>
      </Shell>
    );
  }

  // ── Auth ──
  if (step === "auth") {
    return (
      <Shell>
        <Banner
          qr={qrData}
          right={
            <button onClick={() => setStep("menu")} aria-label="Close" style={{ background: "rgba(255,255,255,0.18)", border: "none", borderRadius: "var(--radius-pill)", width: 36, height: 36, display: "grid", placeItems: "center", color: "#fff", cursor: "pointer" }}>
              <Icons.X size={20} />
            </button>
          }
        />
        <main style={{ flex: 1, padding: "var(--space-4)" }}>
          <OtpPanel
            onSuccess={(tok, cust) => {
              setCustomerTokenState(tok);
              if (cust.full_name) setCustomerName(cust.full_name as string);
              setError(null);
              setStep("menu");
              // If they came here from "Log in to Order", reopen the cart so they can
              // pay straight away (now signed in → the sheet shows "Place Order").
              if (resumeCheckout) {
                setResumeCheckout(false);
                setCartOpen(true);
              }
            }}
          />
        </main>
      </Shell>
    );
  }

  // ── Success ──
  if (step === "success" && checkoutResult) {
    return (
      <Shell>
        <main style={{ flex: 1, display: "flex", alignItems: "center", padding: "var(--space-5)" }}>
          <Card pad style={{ width: "100%", textAlign: "center" }}>
            <div style={{ width: 72, height: 72, borderRadius: "50%", background: "var(--color-success-bg)", display: "grid", placeItems: "center", margin: "0 auto var(--space-3)" }}>
              <Icons.Check size={40} color="var(--color-success)" />
            </div>
            <div style={{ fontSize: "var(--text-2xl)", fontWeight: 900 }}>Payment Successful!</div>
            <p style={{ color: "var(--color-text-muted)", fontSize: "var(--text-sm)", marginTop: 4 }}>
              Order #{checkoutResult.order_id.slice(0, 8)} · {checkoutResult.payment.method.toUpperCase()} · Ref {checkoutResult.payment.reference}
            </p>
            <div style={{ margin: "var(--space-4) 0", padding: "var(--space-4)", background: "var(--color-surface-alt)", borderRadius: "var(--radius-lg)" }}>
              <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>You earned</div>
              <div style={{ fontSize: "var(--text-4xl)", fontWeight: 900, color: "var(--color-primary)" }}>
                +{checkoutResult.points_earned} coins
              </div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
              <Button block variant="accent" size="lg" leftIcon={Icons.Gift} onClick={() => router.push(`/t/${encodeURIComponent(token)}/rewards`)}>
                Rewards &amp; Games
              </Button>
              <Button block variant="primary" onClick={() => { setCart([]); setOrder(null); setCheckoutResult(null); setStep("menu"); }}>
                Order Again
              </Button>
            </div>
          </Card>
        </main>
      </Shell>
    );
  }

  // ── Payment ──
  if (step === "payment" && order) {
    const methods: PaymentMethod[] = ["cash", "card", "nets", "paywave", "paynow"];
    return (
      <Shell>
        <Banner
          qr={qrData}
          right={
            <button onClick={() => setStep("menu")} aria-label="Back to menu" style={{ background: "rgba(255,255,255,0.18)", border: "none", borderRadius: "var(--radius-pill)", width: 36, height: 36, display: "grid", placeItems: "center", color: "#fff", cursor: "pointer" }}>
              <Icons.ArrowLeft size={20} />
            </button>
          }
        />
        <main style={{ flex: 1, padding: "var(--space-4)" }}>
          <div style={{ fontSize: "var(--text-xl)", fontWeight: 800, marginBottom: "var(--space-3)" }}>Order Summary</div>
          <Card flush style={{ marginBottom: "var(--space-3)" }}>
            {order.items.map((item, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "var(--space-3) var(--space-4)", borderBottom: "1px solid var(--color-border)" }}>
                <span>{item.name_snapshot} × {item.quantity}</span>
                <span style={{ fontWeight: 700 }}>{formatSGD(item.line_total)}</span>
              </div>
            ))}
            <div style={{ padding: "var(--space-3) var(--space-4)" }}>
              {[["Subtotal", order.subtotal], ["Service Charge (10%)", order.service_charge], ["GST (9%)", order.tax]].map(([label, val]) => (
                <div key={label as string} style={{ display: "flex", justifyContent: "space-between", fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginBottom: 4 }}>
                  <span>{label}</span><span>{formatSGD(val as number)}</span>
                </div>
              ))}
              <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 900, fontSize: "var(--text-lg)", marginTop: 6 }}>
                <span>Total</span><span>{formatSGD(order.total)}</span>
              </div>
            </div>
          </Card>

          <div style={{ fontSize: "var(--text-xs)", textTransform: "uppercase", letterSpacing: 1, color: "var(--color-text-muted)", fontWeight: 700, margin: "var(--space-4) 0 var(--space-2)" }}>
            Payment method
          </div>
          <div className="payment-grid">
            {methods.map((m) => (
              <button key={m} className={`payment-btn ${selectedPayment === m ? "selected" : ""}`} onClick={() => setSelectedPayment(m)}>
                {m.toUpperCase()}
              </button>
            ))}
          </div>

          <details style={{ marginTop: "var(--space-3)", fontSize: "var(--text-sm)", color: "var(--color-text-muted)" }}>
            <summary style={{ cursor: "pointer" }}>Demo: force outcome</summary>
            <select value={forceOutcome} onChange={(e) => setForceOutcome(e.target.value)} style={{ width: "100%", marginTop: 8, padding: "var(--space-2)" }}>
              <option value="">success (default)</option>
              <option value="declined">declined</option>
              <option value="timeout">timeout</option>
            </select>
          </details>

          {error && <div style={{ color: "var(--color-danger)", fontSize: "var(--text-sm)", marginTop: "var(--space-3)" }}>{error}</div>}
        </main>

        <div style={{ position: "sticky", bottom: 0, padding: "var(--space-3) var(--space-4) calc(var(--tab-bar-h) + env(safe-area-inset-bottom))", background: "var(--color-surface)", borderTop: "1px solid var(--color-border)", boxShadow: "0 -2px 12px rgba(0,0,0,0.06)" }}>
          <Button block variant="primary" size="lg" leftIcon={Icons.CreditCard} onClick={doCheckout} loading={checkingOut}>
            Pay {formatSGD(order.total)}
          </Button>
        </div>
      </Shell>
    );
  }

  // ── Menu ──
  const subtotal = cartTotal(cart);
  const count = cartCount(cart);
  const allMenuItems = categories.flatMap((c) => c.items);
  const filteredItems = filterMenuItems(allMenuItems, search);
  const inDirectory = !!qrData?.is_foodcourt && !selectedStall;   // foodcourt landing
  const loadingStall = !!selectedStall && !stallMenu;             // stall menu fetching

  return (
    <Shell>
      <Banner
        qr={qrData}
        right={
          customerToken ? (
            <button onClick={() => router.push(`/t/${encodeURIComponent(token)}/rewards`)} aria-label="Rewards" style={{ background: "rgba(255,255,255,0.18)", border: "none", borderRadius: "var(--radius-pill)", height: 36, padding: "0 12px", display: "inline-flex", alignItems: "center", gap: 6, color: "#fff", cursor: "pointer", fontWeight: 700, fontSize: "var(--text-sm)" }}>
              <Icons.Gift size={18} /> Rewards
            </button>
          ) : (
            <button onClick={() => setStep("auth")} style={{ background: "#fff", border: "none", borderRadius: "var(--radius-pill)", height: 36, padding: "0 14px", color: "var(--color-primary)", cursor: "pointer", fontWeight: 800, fontSize: "var(--text-sm)" }}>
              Log in
            </button>
          )
        }
      />

      {/* Foodcourt: a "← All stalls · <stall>" bar when browsing one stall's menu */}
      {selectedStall && (
        <button type="button" className="stall-backbar" onClick={backToStalls}>
          <Icons.ArrowLeft size={18} /> All stalls
          <span className="stall-backbar__name">{selectedStall.stall_name}</span>
        </button>
      )}

      {/* Category bar + search only in a menu view (not the stall directory) */}
      {!inDirectory && !loadingStall && (
        <MenuCategoryNav
          categories={categories.map((c) => ({ id: c.id, name: c.name }))}
          activeCat={activeCat}
          onSelect={scrollToCat}
          search={search}
          onSearch={setSearch}
          showSearch={allMenuItems.length > 6}
        />
      )}

      <main style={{ flex: 1, padding: "var(--space-4)", paddingBottom: count > 0 ? 172 : 92 }}>
        {customerName && !selectedStall && (
          <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginBottom: "var(--space-3)" }}>
            Welcome back, <strong style={{ color: "var(--color-text)" }}>{customerName}</strong> 👋
          </div>
        )}
        {error && <div style={{ color: "var(--color-danger)", fontSize: "var(--text-sm)", marginBottom: "var(--space-3)" }}>{error}</div>}

        {inDirectory ? (
          <>
            <div style={{ fontSize: "var(--text-sm)", color: "var(--color-text-muted)", marginBottom: "var(--space-3)" }}>
              Order from any stall — your coins work across the whole food hall.
            </div>
            <StallDirectory stalls={qrData?.stalls ?? []} onSelect={selectStall} />
          </>
        ) : loadingStall ? (
          <>
            <Skeleton width="100%" height={96} radius={12} style={{ marginBottom: 12 }} />
            <Skeleton width="100%" height={96} radius={12} style={{ marginBottom: 12 }} />
          </>
        ) : search ? (
          filteredItems.length === 0 ? (
            <Card flush><EmptyState icon={Icons.Search} title="No matches">Try another dish or category.</EmptyState></Card>
          ) : (
            filteredItems.map((item) => (
              <MenuItemCard key={item.id} item={item} onAdd={addToCart} onCustomise={setCustomiseItem} />
            ))
          )
        ) : (
          categories.map((cat: MenuCategory) => (
            <section key={cat.id} id={`menu-cat-${cat.id}`} data-cat={cat.id} style={{ marginBottom: "var(--space-5)", scrollMarginTop: 64 }}>
              <h2 style={{ fontSize: "var(--text-lg)", fontWeight: 800, margin: "0 0 var(--space-3)" }}>{cat.name}</h2>
              {cat.items.map((item) => (
                <MenuItemCard key={item.id} item={item} onAdd={addToCart} onCustomise={setCustomiseItem} />
              ))}
            </section>
          ))
        )}
      </main>

      {/* Cart CTA — floats just above the tab bar when the cart has items */}
      {count > 0 && (
        <div style={{ position: "sticky", bottom: "calc(var(--tab-bar-h) + env(safe-area-inset-bottom))", zIndex: 1090, padding: "var(--space-3) var(--space-4)", background: "var(--color-surface)", borderTop: "1px solid var(--color-border)", boxShadow: "0 -2px 12px rgba(0,0,0,0.08)" }}>
          <Button block variant="primary" size="lg" leftIcon={Icons.ShoppingCart} onClick={() => setCartOpen(true)}>
            View cart · {count} {count === 1 ? "item" : "items"}
            <span style={{ marginLeft: "auto" }}>{formatSGD(subtotal)}</span>
          </Button>
        </div>
      )}

      <CustomerTabBar token={token} active="menu" />

      {/* Cart sheet */}
      <Sheet open={cartOpen} onClose={() => setCartOpen(false)}>
        <div style={{ fontSize: "var(--text-xl)", fontWeight: 800, marginBottom: "var(--space-3)" }}>Your Cart</div>
        {cart.length === 0 ? (
          <EmptyState icon={Icons.ShoppingCart} title="Your cart is empty">Add items from the menu.</EmptyState>
        ) : (
          <>
            <div style={{ maxHeight: "40vh", overflowY: "auto", marginBottom: "var(--space-3)" }}>
              {cart.map((entry, idx) => {
                const mods = entry.item.modifiers.filter((m) => entry.selectedModifierIds.includes(m.id));
                return (
                  <div key={idx} style={{ display: "flex", gap: "var(--space-3)", padding: "var(--space-3) 0", borderBottom: "1px solid var(--color-border)" }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600 }}>{entry.item.name} <span style={{ color: "var(--color-text-muted)", fontWeight: 400 }}>× {entry.quantity}</span></div>
                      {mods.length > 0 && <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)" }}>+{mods.map((m) => m.name).join(", ")}</div>}
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4 }}>
                      <span style={{ fontWeight: 700 }}>{formatSGD(cartEntryTotal(entry))}</span>
                      <button onClick={() => removeFromCart(idx)} aria-label="Remove" style={{ background: "none", border: "none", color: "var(--color-danger)", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: 2, fontSize: "var(--text-xs)", padding: 0 }}>
                        <Icons.Trash2 size={14} /> Remove
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 800, fontSize: "var(--text-lg)", marginBottom: 4 }}>
              <span>Subtotal</span><span>{formatSGD(subtotal)}</span>
            </div>
            <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginBottom: "var(--space-3)" }}>
              Service charge &amp; GST applied at checkout
            </div>
            {customerToken ? (
              <Button block variant="primary" size="lg" loading={placingOrder} onClick={placeOrder}>Place Order</Button>
            ) : (
              <Button block variant="primary" size="lg" onClick={() => { setResumeCheckout(true); setCartOpen(false); setStep("auth"); }}>Log in to Order</Button>
            )}
          </>
        )}
      </Sheet>

      {/* Customise sheet — opens when an item with options is tapped */}
      {customiseItem && (
        <CustomiseSheet
          item={customiseItem}
          onClose={() => setCustomiseItem(null)}
          onAdd={addToCart}
        />
      )}
    </Shell>
  );
}
