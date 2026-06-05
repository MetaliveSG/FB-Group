"use client";

// Staff POS (tablet-first, landscape). Flow: setup (bind outlet via its QR token) → PIN lock →
// order (item grid + ticket) → pay (mock) → receipt. Reuses the existing order/checkout/voucher engine.
// See docs/architecture-pos-mvp.md.

import { useState, useEffect, useCallback } from "react";
import {
  resolveQr, pinLogin, createManualOrder, cashierCheckout, getReceipt, redeemVoucher,
  getApiBase,
} from "@/lib/api";
import { setStaffToken, getStaffToken, clearStaffToken } from "@/lib/auth";
import type { QrResolution, Menu, MenuItem, OrderOut, ReceiptPayload, PaymentMethod } from "@fbgroup/api-client";

type Step = "setup" | "lock" | "order" | "pay" | "receipt";
type Binding = { merchant_id: string; outlet_id: string; outlet_name: string; qr_token: string };
type Line = { item: MenuItem; qty: number };

const BIND_KEY = "fbgroup_pos_binding";
const PAY_METHODS: { m: PaymentMethod; label: string }[] = [
  { m: "cash", label: "Cash" }, { m: "card", label: "Card" }, { m: "paynow", label: "PayNow" },
  { m: "nets", label: "NETS" }, { m: "paywave", label: "PayWave" },
];

function money(n: number) { return `$${n.toFixed(2)}`; }

export default function PosPage() {
  const base = getApiBase();
  const [step, setStep] = useState<Step>("setup");
  const [binding, setBinding] = useState<Binding | null>(null);
  const [menu, setMenu] = useState<Menu | null>(null);
  const [tokenInput, setTokenInput] = useState("");
  const [pin, setPin] = useState("");
  const [staffName, setStaffName] = useState("");
  const [cat, setCat] = useState<string | null>(null);
  const [lines, setLines] = useState<Line[]>([]);
  const [dinerPhone, setDinerPhone] = useState("");
  const [voucher, setVoucher] = useState("");
  const [order, setOrder] = useState<OrderOut | null>(null);
  const [receipt, setReceipt] = useState<ReceiptPayload | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Restore the outlet binding (device is bound once, then PIN-only).
  const loadMenu = useCallback(async (b: Binding) => {
    const qr: QrResolution = await resolveQr(base, b.qr_token);
    setMenu(qr.menu ?? null);
    if (qr.menu?.categories?.[0]) setCat(qr.menu.categories[0].id);
  }, [base]);

  useEffect(() => {
    const raw = typeof window !== "undefined" ? localStorage.getItem(BIND_KEY) : null;
    if (raw) {
      try {
        const b = JSON.parse(raw) as Binding;
        setBinding(b);
        loadMenu(b).catch(() => {});
        setStep(getStaffToken() ? "order" : "lock");
      } catch { /* ignore */ }
    }
  }, [loadMenu]);

  async function doSetup(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setError(null);
    try {
      const qr: QrResolution = await resolveQr(base, tokenInput.trim());
      const b: Binding = { merchant_id: qr.merchant.id, outlet_id: qr.outlet.id, outlet_name: qr.outlet.name, qr_token: qr.qr_token };
      localStorage.setItem(BIND_KEY, JSON.stringify(b));
      setBinding(b); setMenu(qr.menu ?? null);
      if (qr.menu?.categories?.[0]) setCat(qr.menu.categories[0].id);
      setStep("lock");
    } catch (err) { setError(err instanceof Error ? err.message : "Could not find that outlet"); }
    finally { setBusy(false); }
  }

  async function unlock(e: React.FormEvent) {
    e.preventDefault();
    if (!binding) return;
    setBusy(true); setError(null);
    try {
      const res = await pinLogin(base, binding.merchant_id, pin);
      setStaffToken(res.access_token);
      setStaffName(res.user?.full_name || "Staff");
      setPin("");
      setStep("order");
    } catch { setError("Invalid PIN"); setPin(""); }
    finally { setBusy(false); }
  }

  function addItem(item: MenuItem) {
    setLines((prev) => {
      const i = prev.findIndex((l) => l.item.id === item.id);
      if (i >= 0) { const next = [...prev]; next[i] = { ...next[i], qty: next[i].qty + 1 }; return next; }
      return [...prev, { item, qty: 1 }];
    });
  }
  function bump(id: string, d: number) {
    setLines((prev) => prev.flatMap((l) => l.item.id === id ? (l.qty + d <= 0 ? [] : [{ ...l, qty: l.qty + d }]) : [l]));
  }
  const subtotal = lines.reduce((s, l) => s + l.item.price * l.qty, 0);

  async function pay(method: PaymentMethod) {
    if (!binding || lines.length === 0) return;
    setBusy(true); setError(null);
    try {
      const tok = getStaffToken();
      if (!tok) { setStep("lock"); return; }
      const o = await createManualOrder(base, tok, {
        outlet_id: binding.outlet_id,
        items: lines.map((l) => ({ menu_item_id: l.item.id, quantity: l.qty })),
        customer_phone: dinerPhone.trim() || undefined,
      });
      if (voucher.trim()) {
        try { await redeemVoucher(base, tok, voucher.trim().toUpperCase(), { order_id: o.id }); }
        catch (err) { setError(err instanceof Error ? err.message : "Voucher not applied"); }
      }
      await cashierCheckout(base, tok, o.id, method);
      const rec = await getReceipt(base, tok, o.id);
      setOrder(o); setReceipt(rec); setStep("receipt");
    } catch (err) { setError(err instanceof Error ? err.message : "Payment failed"); }
    finally { setBusy(false); }
  }

  function newOrder() {
    setLines([]); setDinerPhone(""); setVoucher(""); setOrder(null); setReceipt(null); setError(null); setStep("order");
  }
  function lock() { clearStaffToken(); setStep("lock"); newOrder(); }

  // ── Render ──────────────────────────────────────────────────────────
  const shell: React.CSSProperties = { minHeight: "100vh", background: "#0f172a", color: "#e2e8f0", display: "flex", flexDirection: "column" };

  if (step === "setup") {
    return (
      <div style={{ ...shell, alignItems: "center", justifyContent: "center" }}>
        <form onSubmit={doSetup} style={{ background: "#1e293b", padding: 32, borderRadius: 16, width: 380, maxWidth: "90vw" }}>
          <h1 style={{ fontSize: 22, fontWeight: 800, margin: "0 0 4px" }}>POS Setup</h1>
          <p style={{ color: "#94a3b8", fontSize: 14, marginTop: 0 }}>Bind this device to an outlet — enter its QR token.</p>
          {error && <div style={{ color: "#fca5a5", fontSize: 14, marginBottom: 8 }}>{error}</div>}
          <input value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} placeholder="e.g. toast-box-orchard-f1878dd3"
                 style={{ width: "100%", padding: 12, borderRadius: 8, border: "1px solid #334155", background: "#0f172a", color: "#fff", fontFamily: "monospace" }} />
          <button type="submit" disabled={busy} style={primaryBtn}>{busy ? "Connecting…" : "Connect outlet"}</button>
        </form>
      </div>
    );
  }

  if (step === "lock") {
    return (
      <div style={{ ...shell, alignItems: "center", justifyContent: "center" }}>
        <form onSubmit={unlock} style={{ background: "#1e293b", padding: 32, borderRadius: 16, width: 320, textAlign: "center" }}>
          <div style={{ color: "#94a3b8", fontSize: 13 }}>{binding?.outlet_name}</div>
          <h1 style={{ fontSize: 20, fontWeight: 800, margin: "4px 0 16px" }}>Enter PIN</h1>
          {error && <div style={{ color: "#fca5a5", fontSize: 14, marginBottom: 8 }}>{error}</div>}
          <div style={{ fontSize: 28, letterSpacing: 8, height: 36, fontFamily: "monospace" }}>{"•".repeat(pin.length)}</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10, marginTop: 16 }}>
            {["1", "2", "3", "4", "5", "6", "7", "8", "9", "⌫", "0", "OK"].map((k) => (
              <button key={k} type={k === "OK" ? "submit" : "button"} disabled={busy}
                onClick={() => { if (k === "⌫") setPin((p) => p.slice(0, -1)); else if (k !== "OK" && pin.length < 6) setPin((p) => p + k); }}
                style={{ padding: "16px 0", fontSize: 20, fontWeight: 700, borderRadius: 10, border: "1px solid #334155",
                         background: k === "OK" ? "var(--color-primary, #e23744)" : "#0f172a", color: "#fff", cursor: "pointer" }}>
                {k}
              </button>
            ))}
          </div>
          <button type="button" onClick={() => { localStorage.removeItem(BIND_KEY); setBinding(null); setStep("setup"); }}
                  style={{ marginTop: 14, background: "none", border: "none", color: "#64748b", fontSize: 12, cursor: "pointer" }}>
            Unbind device
          </button>
        </form>
      </div>
    );
  }

  if (step === "receipt" && receipt) {
    return (
      <div style={{ ...shell, alignItems: "center", justifyContent: "center", padding: 20 }}>
        <div id="pos-receipt" style={{ background: "#fff", color: "#111", width: 320, padding: 20, borderRadius: 8, fontFamily: "monospace", fontSize: 13 }}>
          <div style={{ textAlign: "center", marginBottom: 8 }}>
            <div style={{ fontWeight: 800, fontSize: 15 }}>{receipt.company.name}</div>
            {receipt.company.uen && <div>UEN {receipt.company.uen}</div>}
            {receipt.company.address && <div>{receipt.company.address}</div>}
            {receipt.company.phone && <div>{receipt.company.phone}</div>}
            <div style={{ marginTop: 4 }}>{receipt.outlet.name}{receipt.stall ? ` · ${receipt.stall}` : ""}</div>
          </div>
          <div style={{ borderTop: "1px dashed #999", margin: "8px 0" }} />
          <div>Order {receipt.order_id.slice(0, 8)} · {new Date(receipt.created_at).toLocaleString()}</div>
          <div style={{ borderTop: "1px dashed #999", margin: "8px 0" }} />
          {receipt.items.map((it, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between" }}><span>{it.quantity}× {it.name}</span><span>{money(it.line_total)}</span></div>
          ))}
          <div style={{ borderTop: "1px dashed #999", margin: "8px 0" }} />
          {[["Subtotal", receipt.subtotal], ["Service", receipt.service_charge], ["GST", receipt.tax]].map(([l, v]) => (
            <div key={l as string} style={{ display: "flex", justifyContent: "space-between", color: "#555" }}><span>{l}</span><span>{money(v as number)}</span></div>
          ))}
          {receipt.discount > 0 && <div style={{ display: "flex", justifyContent: "space-between", color: "#166534" }}><span>Discount {receipt.voucher_code ? `(${receipt.voucher_code})` : ""}</span><span>-{money(receipt.discount)}</span></div>}
          <div style={{ display: "flex", justifyContent: "space-between", fontWeight: 800, fontSize: 15, marginTop: 4 }}><span>TOTAL</span><span>{money(receipt.total)}</span></div>
          {receipt.payment && <div style={{ marginTop: 6 }}>Paid: {receipt.payment.method.toUpperCase()} · {receipt.payment.reference ?? ""}</div>}
          {receipt.points_earned ? <div>Coins earned: +{receipt.points_earned}</div> : null}
          <div style={{ textAlign: "center", marginTop: 10 }}>{receipt.footer}</div>
        </div>
        <div style={{ display: "flex", gap: 12, marginTop: 20 }}>
          <button onClick={() => window.print()} style={{ ...primaryBtn, width: 150 }}>Print</button>
          <button onClick={newOrder} style={{ ...primaryBtn, width: 150, background: "#334155" }}>New order</button>
        </div>
      </div>
    );
  }

  // order / pay — 2-pane
  const cats = menu?.categories ?? [];
  const items = cats.find((c) => c.id === cat)?.items ?? [];
  return (
    <div style={shell}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", background: "#1e293b" }}>
        <div style={{ fontWeight: 800 }}>{binding?.outlet_name} <span style={{ color: "#64748b", fontWeight: 400 }}>· POS</span></div>
        <div style={{ display: "flex", gap: 12, alignItems: "center", fontSize: 14 }}>
          <span style={{ color: "#94a3b8" }}>{staffName}</span>
          <button onClick={lock} style={{ background: "#334155", border: "none", color: "#fff", borderRadius: 8, padding: "6px 12px", cursor: "pointer" }}>Lock</button>
        </div>
      </div>
      {error && <div style={{ background: "#7f1d1d", color: "#fecaca", padding: "8px 16px", fontSize: 14 }}>{error}</div>}
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        {/* Left: menu */}
        <div style={{ flex: 1, padding: 16, overflowY: "auto" }}>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
            {cats.map((c) => (
              <button key={c.id} onClick={() => setCat(c.id)}
                style={{ padding: "8px 14px", borderRadius: 999, border: "none", cursor: "pointer", fontWeight: 600,
                         background: c.id === cat ? "var(--color-primary, #e23744)" : "#1e293b", color: "#fff" }}>{c.name}</button>
            ))}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))", gap: 12 }}>
            {items.map((it) => (
              <button key={it.id} data-testid="pos-item" onClick={() => addItem(it)} disabled={!it.is_available}
                style={{ textAlign: "left", background: "#1e293b", border: "1px solid #334155", borderRadius: 12, padding: 14, cursor: "pointer", color: "#fff", opacity: it.is_available ? 1 : 0.4, minHeight: 80 }}>
                <div style={{ fontWeight: 600, fontSize: 15 }}>{it.name}</div>
                <div style={{ color: "var(--color-primary, #fb7185)", fontWeight: 700, marginTop: 6 }}>{money(it.price)}</div>
              </button>
            ))}
          </div>
        </div>
        {/* Right: ticket */}
        <div style={{ width: 360, background: "#1e293b", display: "flex", flexDirection: "column", padding: 16 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Ticket</div>
          <div style={{ flex: 1, overflowY: "auto" }}>
            {lines.length === 0 ? <div style={{ color: "#64748b", fontSize: 14 }}>Tap items to add…</div> :
              lines.map((l) => (
                <div key={l.item.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 0" }}>
                  <div><div style={{ fontSize: 14 }}>{l.item.name}</div><div style={{ color: "#64748b", fontSize: 12 }}>{money(l.item.price)}</div></div>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <button onClick={() => bump(l.item.id, -1)} style={stepBtn}>−</button>
                    <span style={{ minWidth: 18, textAlign: "center" }}>{l.qty}</span>
                    <button onClick={() => bump(l.item.id, 1)} style={stepBtn}>+</button>
                  </div>
                </div>
              ))}
          </div>
          <div style={{ borderTop: "1px solid #334155", paddingTop: 10, marginTop: 8 }}>
            <input value={dinerPhone} onChange={(e) => setDinerPhone(e.target.value)} placeholder="+ Diner phone (loyalty)"
                   style={ticketInput} />
            <input value={voucher} onChange={(e) => setVoucher(e.target.value.toUpperCase())} placeholder="Voucher code (optional)"
                   style={{ ...ticketInput, fontFamily: "monospace" }} />
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 14, color: "#94a3b8", margin: "8px 0" }}>
              <span>Subtotal (excl. svc/GST)</span><span>{money(subtotal)}</span>
            </div>
            {step === "pay" ? (
              <div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                  {PAY_METHODS.map((p) => (
                    <button key={p.m} data-testid={`pos-pay-${p.m}`} disabled={busy} onClick={() => pay(p.m)} style={{ ...primaryBtn, marginTop: 0, padding: "14px 0" }}>{p.label}</button>
                  ))}
                </div>
                <button onClick={() => setStep("order")} style={{ ...primaryBtn, marginTop: 8, background: "#334155" }}>Back</button>
              </div>
            ) : (
              <button data-testid="pos-charge" disabled={lines.length === 0 || busy} onClick={() => setStep("pay")} style={{ ...primaryBtn, opacity: lines.length === 0 ? 0.5 : 1 }}>
                {busy ? "…" : `Charge ${money(subtotal)}+`}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const primaryBtn: React.CSSProperties = { width: "100%", marginTop: 12, padding: "14px 0", borderRadius: 10, border: "none", background: "var(--color-primary, #e23744)", color: "#fff", fontSize: 16, fontWeight: 700, cursor: "pointer" };
const stepBtn: React.CSSProperties = { width: 30, height: 30, borderRadius: 8, border: "1px solid #475569", background: "#0f172a", color: "#fff", cursor: "pointer", fontSize: 16 };
const ticketInput: React.CSSProperties = { width: "100%", padding: 10, marginBottom: 8, borderRadius: 8, border: "1px solid #334155", background: "#0f172a", color: "#fff", boxSizing: "border-box" };
