---
marp: true
paginate: true
footer: 'FSG × CIP  ·  Strictly Private & Confidential  ·  2026'
size: 16:9
---

<!-- FSG chairman deck — Big-4 grade, red/yellow master. Render:
     marp docs/fsg-chairman-deck.md --pdf  --allow-local-files
     marp docs/fsg-chairman-deck.md --pptx --allow-local-files
     Numbers illustrative — insert FSG actuals. Decided architecture: no POS change; small uPOS
     integration (webhook + signed receipt-QR) + a small tablet at anchor stalls. Source narrative:
     docs/cip-vs-salesforce-fnb.md, foodcourt-pilot-kit.md, payments-build-spec.md, wallet-scope.md. -->

<style>
:root{
  --red:#C8102E; --red-d:#9E0C24; --gold:#F2A900; --gold-d:#C9871A;
  --ink:#191919; --muted:#6E6E6E; --line:#E6E3DE; --paper:#FFFFFF; --wash:#FBF7F0;
}
section{
  font-family:"Helvetica Neue","Segoe UI",Arial,sans-serif;
  font-size:23px; line-height:1.45; color:var(--ink); background:var(--paper);
  padding:70px 72px 78px;
}
section::before{ content:""; position:absolute; top:0; left:0; right:0; height:9px; background:var(--red); }
h1{ font-size:38px; font-weight:800; letter-spacing:-.01em; margin:0 0 18px; color:var(--ink); }
h1::after{ content:""; display:block; width:60px; height:5px; background:var(--gold); margin-top:12px; }
h2{ font-size:26px; color:var(--red-d); margin:.2em 0 .3em; }
h3{ font-size:21px; color:var(--ink); margin:.2em 0; }
strong{ color:var(--red-d); }
em{ color:var(--muted); }
a{ color:var(--red); }
ul,ol{ margin:.2em 0; } li{ margin:.32em 0; }
table{ border-collapse:collapse; width:100%; font-size:20px; }
th{ background:var(--red); color:#fff; text-align:left; padding:9px 12px; font-weight:700; }
td{ padding:9px 12px; border-bottom:1px solid var(--line); }
tr:nth-child(even) td{ background:var(--wash); }
footer{ color:var(--muted); font-size:12px; }
section::after{ /* page number colour via paginate */ }
.marpit > svg foreignObject section:after{}
/* --- callouts --- */
.sowhat{ background:var(--wash); border-left:8px solid var(--gold); padding:14px 20px; font-weight:600; color:var(--ink); margin-top:10px; }
.kpi{ font-size:76px; font-weight:900; color:var(--red); line-height:1; letter-spacing:-.02em; }
.kpi small{ font-size:26px; color:var(--ink); font-weight:700; }
.src{ position:absolute; bottom:30px; left:72px; right:72px; font-size:12px; color:var(--muted); font-style:italic; }
.lead{ font-size:26px; color:var(--ink); }
.tag{ display:inline-block; background:var(--gold); color:var(--ink); font-weight:800; font-size:13px; padding:3px 10px; border-radius:3px; letter-spacing:.04em; text-transform:uppercase; }
/* --- cover --- */
section.cover{ background:linear-gradient(135deg,var(--red) 0%,var(--red-d) 100%); color:#fff; padding-top:150px; }
section.cover::before{ background:var(--gold); height:14px; }
section.cover h1{ color:#fff; font-size:52px; } section.cover h1::after{ background:#fff; }
section.cover .lead{ color:#FFE7AE; font-size:27px; }
section.cover .lead strong{ color:#FFD24D; }
section.cover .meta{ position:absolute; bottom:60px; left:72px; color:#FFD9A8; font-size:16px; letter-spacing:.03em; }
/* --- section divider --- */
section.div{ background:var(--ink); color:#fff; padding-top:230px; }
section.div::before{ background:var(--gold); }
section.div h1{ color:#fff; font-size:44px; } section.div h1::after{ background:var(--red); width:90px; }
section.div .tag{ background:var(--red); color:#fff; }
/* --- centred KPI slide --- */
section.center{ text-align:center; } section.center h1::after{ margin:12px auto 0; }
</style>

<!-- _class: cover -->
<!-- _paginate: false -->
<!-- _footer: '' -->

<span class="tag">Strictly Private &amp; Confidential</span>

# Turn every diner into a regular

<p class="lead">CIP × FSG — grow foodcourt transactions <strong style="color:#fff">+10%</strong><br/>without changing a single till.</p>

<div class="meta">Customer Intelligence Platform · Board proposal · 2026</div>

---

# Agenda

1. **The opportunity** — a $26M base, a +10% mandate
2. **The model** — no POS change: two capture lanes, one engine
3. **What changes at the stall** — a small uPOS hook + a tablet
4. **The diner journey** — order · login · earn · play · return
5. **The growth engine** — intelligence that compounds
6. **The business case** — where the +$2.6M comes from
7. **The ask** — a 6-week, measured pilot
8. **Appendix** — decisions locked · guardrails

---

# The argument, in one page

| | |
|---|---|
| **The mandate** | Grow transactions **+10% = +SGD 2.6M** on a **$26M** base. |
| **The problem** | ~80% of diners are **anonymous**; peak queues **lose sales**; no way to bring diners back. |
| **The insight** | A growth target needs a **growth engine** — not another system of record. *You can't grow what you can't see.* |
| **The model** | **Keep uPOS.** A **small integration** + a **small tablet** at stalls turn every meal into a known, returning customer — **no app to install.** |
| **The proof** | **One foodcourt, 6 weeks**, measured against a holdout. Scale only if it works. |

<div class="sowhat">So what: this is a low-risk way to put a measurable dent in the +10% — without touching how your stalls operate.</div>

---

<!-- _class: div -->
<span class="tag">01</span>

# The opportunity

---

<!-- _class: center -->

# Your +10% is a growth problem — not a software purchase

<p class="kpi">+SGD 2.6M <small>= +10% on a $26M base</small></p>

<p class="lead" style="margin-top:30px">The real question isn't <em>"which platform?"</em><br/>It's <strong>"what actually produces that +$2.6M?"</strong></p>

<div class="sowhat">Most tools <strong>run</strong> your operations. CIP is built to <strong>grow</strong> the business.</div>

---

# Today, 80% of a $26M base is invisible — and unrepeatable

- **You don't know your diners.** Most of that $26M is **anonymous** — no name, no return path.
- **Queues cost you sales.** At peak, diners see the line and **walk away** — lost revenue you never record.
- **A great meal doesn't equal a return visit.** No identity → no loyalty → no win-back.

<div class="sowhat">The constraint is capture. Fix capture, and retention + the +10% follow.</div>

---

<!-- _class: div -->
<span class="tag">02</span>

# The model — no POS change

---

# Two capture lanes, one engine — your tills untouched

![w:1080](../artifacts/uiux-benchmark/fsg-flow.svg)

<div class="src">No till is replaced. The only additions: a small uPOS integration (outbound webhook + signed receipt-QR) and a ~$150 tablet at anchor stalls. All diner-facing screens are a web app — nothing to download.</div>

---

# End-to-end: the two diner journeys, step by step

![w:1100](../artifacts/uiux-benchmark/fsg-flow-e2e.svg)

<div class="src">Grounded in docs/foodcourt-pilot-kit.md §0 — ① no-queue = order-ahead (+10% engine); ② queue = scan signed receipt-QR (retention). Both feed one engine.</div>

---

# All that changes at the stall: a small uPOS hook + a tablet

| What | Change | Effort | Why |
|---|---|---|---|
| **uPOS outbound webhook** | small integration (one vendor, all stalls) | low | 100% sale capture → airtight +10% measurement |
| **Signed receipt-QR** | uPOS prints a QR on the receipt | low | walk-up diners scan → earn (queue lane) |
| **Small tablet** (anchor stalls) | ~$150 device, web kiosk | low | receive app order-ahead orders → “Ready” |
| **The till itself** | **none** | — | cashiers ring sales exactly as today |
| **Diner app** | **none** | — | web app, no install |

<div class="sowhat">Keep your POS. One small integration + a tablet unlock order-ahead and loyalty — that’s the entire footprint.</div>

---

<!-- _class: div -->
<span class="tag">03</span>

# The diner journey

---

# Every diner becomes known, rewarded, and brought back

<div style="display:flex;gap:24px;align-items:flex-start">
<div style="flex:1.05">

**① Order** — scan → order → **skip the queue**
**② Log in** — phone + OTP → *now you know them* (PDPA-clean)
**③ Pay** — PayNow/card/**FS Wallet** → collect when ready
**④ Earn** — coins + tier + FS Wallet, one account
**⑤ Play** — spin-the-wheel & jackpot → a reason to return

<div class="sowhat">Capture is invisible to the diner — it just feels like a faster, more rewarding meal.</div>

</div>
<div style="flex:.95;text-align:center">

![h:430](../artifacts/uiux-benchmark/beat3_proof.jpg)
<em style="font-size:14px">Design direction — final artwork in progress</em>

</div>
</div>

---

<!-- _class: div -->
<span class="tag">04</span>

# The case & the ask

---

# Intelligence turns each visit into the next one

Every order (both lanes) feeds the CRM + AI:

- **Lapsing diner** → automatic **win-back** offer (WhatsApp)
- **Earned at the chicken-rice stall** → **cross-stall** nudge to drinks
- **Quiet 3pm** → a targeted **off-peak** deal
- **Coalition-ready** → earn across all FSG courts (one network)

<div class="sowhat">The data compounds daily — and gets harder for any competitor to copy. That is the durable moat.</div>

---

# +10% = one more visit per regular, per year

<p class="lead">$26M ÷ ~$25 a ticket ≈ <strong>~1 million transactions / year</strong></p>

- **+10% ≈ one extra visit per regular diner, per year** — exactly what loyalty + win-back drive
- Capture **40%** of diners × lift their spend **25%** → **+10% court-wide**
- Even a **1% lift = $260k** — and retention **compounds**

<div class="sowhat">This is retention math, not a moonshot. The engine exists; the pilot proves the number.</div>

<div class="src">Illustrative — to be calibrated with FSG’s actual average ticket, transaction volume and current capture rate.</div>

---

# CIP grows; your POS & enterprise tools run — keep them

| The job | **CIP** *(necessary)* | POS / Salesforce *(optional)* |
|---|---|---|
| Capture the diner at the meal | ✅ | ❌ |
| Loyalty · FS Wallet · games | ✅ | ❌ |
| AI that grows revenue | ✅ | add-on |
| Ring the sale / enterprise admin | keep uPOS | ✅ |

<div class="sowhat">We are not a replacement — we are the growth layer that sits beside what you already run.</div>

---

# Prove it on one court, in 6 weeks

<div style="display:flex;gap:30px">
<div style="flex:1">

**Pilot**
- One foodcourt · anchor stalls · 4–6 weeks
- Order-ahead + loyalty + win-back live
- **Measured vs a held-back control** → a real lift number

**Then**
- Works → scale to **every FSG court**
- Add wallet auto-reload, referral, AI ops

</div>
<div style="flex:1">

**Why it’s low-risk**
- **No POS change · no app install**
- Small footprint (a hook + a tablet)
- Near-zero commission
- Stop anytime — you keep the data

</div>
</div>

<div class="sowhat">Give us one court for six weeks. We show you the +10% — with data, not a slide.</div>

---

<!-- _class: div -->
<span class="tag">05</span>

# Appendix

---

# The decisions, locked

| Decision | Choice |
|---|---|
| **POS** | **Keep uPOS** — small integration only (webhook + signed receipt-QR) |
| **Stall device** | small **tablet** at anchor stalls (~$150) for order-ahead |
| **Diner client** | **web app** — no install |
| **Payments** | **HitPay** (PayNow · cards · GrabPay/ShopeePay · Apple/Google Pay) |
| **Merchant-of-record** | **FSG** (single account; per-stall split = later) |
| **FS Wallet** | deposit-only, auto-reload, FSG-issued (CIP rails) |
| **Capture** | dual-lane: order-ahead (app) + receipt-QR (queue) |
| **Network** | money stays per-enterprise; **coins** roam (coalition) |

---

# Guardrails: your money, data and POS — protected

- **POS untouched** — cashiers operate exactly as today.
- **Wallet integrity** — every transaction is **logged & non-repudiable** (tamper-evident ledger); balance can never go negative.
- **PDPA** — explicit diner consent at capture; data stays FSG’s.
- **Spend discipline** — coupon-budget caps & margin guardrails so the +10% is *profitable* growth (the Luckin lesson).
- **No lock-in fear** — you own the customer data; export anytime.

<div class="sowhat">Growth, governed. The upside of capture without the operational or compliance risk.</div>

---

<!-- _class: cover -->
<!-- _paginate: false -->
<!-- _footer: '' -->

# Keep your POS.<br/>We bring your diners back.

<p class="lead">One court. Six weeks. A measured +10%.</p>

<div class="meta">Customer Intelligence Platform · Let's run the pilot</div>
