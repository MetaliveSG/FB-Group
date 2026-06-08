# Real Payment — build scope (PayNow · cards · Apple Pay · Google Pay)

_Replaces the **mock** payment in CIP checkout with real money for the SG foodcourt pilot. Methods:
**PayNow + cards + Apple Pay + Google Pay**, in the **webapp** (PWA, no native app). Plugs into the existing
`checkout` / `record_sale()` path. Critical-path #1 for the pilot (`docs/foodcourt-pilot-kit.md`). Status: PLAN._

## PSP choice (this is the main decision)
You don't build card/wallet rails yourself — you pick a Payment Service Provider. Two real options for SG:

**Both support all four methods** (Apple Pay, Google Pay, PayNow, cards) — HitPay also adds GrabPay/ShopeePay/
BNPL. The real difference is **inline vs hosted checkout**, not coverage:

| | **Stripe** (recommended for inline UX) | **HitPay** (SG-native, cheaper) |
|---|---|---|
| Apple Pay + Google Pay | **inline** via **Express Checkout Element** (wallet buttons render *in your own checkout*, no redirect) | **supported**, but on HitPay's **hosted checkout page** |
| Render model | **embeddable elements** in your webapp | **hosted checkout** (redirect/embed HitPay's page) |
| PayNow | supported (SGD; QR, async webhook) | **first-class / native**, SG SME default |
| Cards (Visa/MC/Amex) + 3DS/SCA | yes, PSP-handled | yes |
| **Local e-wallets** | GrabPay, AliPay, WeChat Pay — **NO ShopeePay / Atome** | **GrabPay, ShopeePay, Atome (BNPL), GrabPay/ShopeePay Later**, AliPay, WeChat Pay |
| Dev experience / docs | **best-in-class** | good, simpler/SG-focused |
| Fees (SG, indicative) | ~3.4% + S$0.50 cards; PayNow lower | **lower** cards; PayNow cheap |
| Marketplace / per-stall settlement | **Stripe Connect** (mature) | HitPay has split options |

**E-wallet coverage (decisive for a mass-market foodcourt):** SG foodcourt diners pay with **PayNow + GrabPay
+ ShopeePay** every day. **Stripe is missing ShopeePay (and Atome).** **HitPay covers all of them** + the BNPL
"Later" options. So for *this* audience, **HitPay has the better e-wallet fit.**

**Recommendation (revised):** for the **SG foodcourt pilot, lean HitPay** — broadest **local e-wallet coverage**
(incl. **ShopeePay**, which Stripe lacks) + **lower fees** + SG-native, accepting its **hosted-checkout** UX.
Choose **Stripe** instead only if **inline in-webapp wallet UX** or **mature per-stall settlement (Connect)**
is the priority over coverage/cost. *(HitPay fully supports Apple Pay/Google Pay too — the real axes are
**e-wallet coverage + fees (→ HitPay)** vs **inline UX + Connect (→ Stripe)**.)* Decide before build — it
changes the SDK, not the architecture.

## How each method works (so expectations are right)
- **Apple Pay (web):** needs **Apple Pay on the Web** — HTTPS on a real domain + a **domain-association file**
  at `/.well-known/...` (Stripe auto-manages the merchant ID). Shows **only on Apple/Safari**.
- **Google Pay (web):** Google Pay API for Web; PSP element handles it. Shows on **Chrome/Android**.
  → Both are **card-backed wallets** — one tap, no card entry. Express Checkout Element renders both for you.
- **Cards:** PSP-hosted **Payment Element** (raw card data never touches our server → **PCI SAQ-A**). 3DS by PSP.
- **PayNow:** **asynchronous** — show the **PayNow QR**, diner scans with their bank app, payment confirms
  **out-of-band** → we get a **webhook**. So checkout must handle a **pending → paid** state, not instant.

## Architecture (where it plugs in)
**Backend (`apps/api`):**
- New `payments` service: create a **PaymentIntent** (Stripe) / payment request → return client secret to the webapp.
- **Webhook endpoint** (PSP → CIP): signature-verified, **idempotent** by intent id. On `succeeded` → mark
  `Payment` paid → **finalise the order via `record_sale()`** → loyalty/CRM accrue (the existing path).
- Wire real refs into existing `Payment`/`Transaction` models (intent id, method, status). Handle **async PayNow**
  (pending until webhook). **Refunds** for the **void flow** (`orders.void_order`) — now real, not mock.
**Frontend (`apps/web`):**
- Replace the mock "Pay" with the **Express Checkout Element** (Apple/Google Pay buttons + card) + **PayNow** method.
- Order states: `pending_payment → paid` (on webhook) → triggers **order-ahead fulfilment** / earn.
**Order-ahead vs receipt-QR:** order-ahead pays here (in-app); the **queue lane pays at uPOS** (no CIP payment —
it earns via the signed receipt-QR). So this build is for the **order-ahead lane + any in-app redemption**.

## Settlement (the foodcourt nuance — a decision)
- **Pilot (recommended): single merchant account** — **FSG (operator) is merchant-of-record**, collects all
  order-ahead funds, remits to stalls via their existing arrangement. **No per-stall KYC** → fastest.
- **Phase 2: per-stall connected accounts** (Stripe Connect / marketplace **split settlement**) → funds land
  per stall automatically. This is the **M2 moat** — **defer past the pilot.**
- *Decision: who is merchant-of-record for the pilot — FSG, or each stall?* (FSG = simplest.)

## Effort estimate
| Work | Est |
|---|---|
| PSP account + PayNow activation + **KYC** (FSG) | lead time **days** — start Wk-0, runs parallel |
| Backend: payment service + PaymentIntent + webhook + wire to `record_sale` | **3–5 d** |
| Frontend: Express Checkout Element (Apple/GPay/card) + PayNow flow + pending state | **2–3 d** |
| Apple Pay domain verification + wallet config | **0.5–1 d** |
| Refund path for void flow | **1 d** |
| Testing: sandbox, 3DS, **PayNow async**, refunds, idempotent webhooks | **2–3 d** |
| **Total dev** | **~1.5–2 weeks** (+ KYC lead time in parallel) |

## Gotchas / risks
- **PayNow is async** → must design the **pending→paid** UX (QR + "waiting", webhook confirm, expiry/timeout). Don't assume instant.
- **Apple Pay web** = domain-association file + HTTPS + real domain; only on Apple/Safari. PWA must be on a proper domain.
- **KYC / PayNow activation lead time** can gate go-live — **start Week 0.**
- **PCI:** use PSP-hosted elements only — **never** build a raw card form (keeps you SAQ-A).
- **Webhooks:** signature-verify + idempotent (PayNow + retries).
- **Fees vs margin:** ~2–3.4% per txn — factor into the +10% economics + coupon guardrails (the Luckin CFO discipline).
- **Settlement-per-stall deferred** — pilot uses one account; don't accidentally scope Connect now.

## Decisions needed before build
1. **PSP: Stripe (DX + free Apple/Google Pay) or HitPay (SG-native, cheaper)?**
2. **Merchant-of-record for the pilot: FSG (one account, simplest) or per-stall (defer)?**
