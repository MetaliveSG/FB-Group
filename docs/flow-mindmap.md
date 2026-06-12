# CIP Phase ① — Flow Mindmap (loyalty first, at the existing uPOS counter)

_Working map of the LOCKED phase-① flow (decisions 2026-06-12 — see `decisions.md`; full spec
`architecture/payments.md` §7b/§8). **Branches marked 🔀 are different routes to be discussed
later** — they're placeholders, not designs. Renders as a diagram on GitHub (Mermaid)._

## The 30-second version (for the FSG room — board + their uPOS CTO)

**Mei Ling's first visit:**
1. **While queueing**, sees *"Scan for $10 FREE vouchers"* — scans, phone number, done. → *FSG gains
   a member in 30 seconds, before she even orders.*
2. Orders 2 kopi; cashier bills **$3 on uPOS** — nothing changes. → *same till, same routine.*
3. Shows her $2 voucher; cashier **scans it with the same uPOS scanner** → till shows **$1** → she
   pays $1. → *FSG knows who bought what, where, for how much.*
4. Her phone: **"300 coins earned! Voucher #2 unlocked."** → *a manufactured reason to return — 4
   more times.*
5. Next week the AI notices she loves kopi → sends a kopi voucher. → *marketing that pays for
   itself, measured at the till.*

**The money:** she SEES $5 of free value; FSG PAYS food cost only (≈$1.80, spread over 2+ visits);
FSG COLLECTS $1 cash today vs $0.90 kopi cost — **never cash-negative, even on the free-gift visit.**

**For the uPOS CTO — uPOS is NOT replaced; one integration, all stalls, three capabilities:**
1. **At tender** (the only new cashier step): scan a QR → call our API → apply the returned
   deduction → show balance due. *Exactly how gift-card tenders work today.*
2. **After sale:** send the sale record (items, amount, stall, txn id). *Batched or delayed is fine —
   nothing at the counter waits on it.*
3. *Nice-to-have:* a QR on the printed receipt so members who paid without a voucher still earn.

Same integration later takes the **FS Wallet** as a tender — build once, two products. Signed calls
both ways · idempotent (a retry can never double-deduct) · **zero customer personal data enters uPOS**
(PDPA-clean).

---

```mermaid
mindmap
  root((CIP Phase ①<br/>Loyalty + CRM<br/>at existing uPOS))
    1 · Diner journey — first visit
      Order verbally at stall — unchanged
      Cashier bills $3 in uPOS
      Scan counter standee QR
        Register in-queue — under 60s
          Phone + OTP autofill
          One PDPA consent tap
        Welcome pack lands — 5 × $2
          Voucher 1 unlocked
          2 to 5 locked — sequential
      Show voucher QR — one-time token, ~90s TTL
        Voucher still ISSUED — armed, nothing burned
        TTL expires → re-show, voucher untouched
      Cashier scans with uPOS scanner
        uPOS calls /tender/scan — bill context included
        Validate + REDEEM atomically — one call
        $2 deducted — uPOS shows $1 balance
        Webapp flips ~2s → ✓ redeemed + live clock
        AT SCAN-APPROVAL: voucher 1 → REDEEMED
        Voucher 2 UNLOCKS — the retention moment
        300 coins provisional
      Pay $1 balance — cash or PayNow
      Later — webhook match
        items attach to profile
        coins provisional → CONFIRMED
    2 · Diner journey — returning
      Open webapp → next voucher QR → same scan flow
      No-voucher visit — earn only
        Pay normally at counter
        Scan receipt QR → verified coins
    3 · uPOS integration — the two gates
      Q1 Outbound webhook — MUST
        items + stall + amount + txn_id
        feeds capture and earn verification
      Q5 Scan-at-tender — MUST for vouchers
        scan code → call CIP → apply deduction
      Q2 Receipt QR — earn-only lane
      Fallback if Q5 = no
        manual uPOS discount + live-clock glance
    4 · CIP engine
      Token service — single-use, typed voucher/wallet
      /tender/scan — idempotent by txn_id
      tender_intents — approved → matched
      Voucher core R39 + sequential-unlock extension
      Min-spend checked vs REAL uPOS bill
      Earn: provisional → verified on webhook match
      Redeem-on-scan — no two-phase hold
      Reversal nets: tender-void · 24h no-match auto-return
      Daily recon + exception report
    5 · Economics & guardrails
      100 coins per $1 gross bill — tenant config
      100 coins = $1 — FOOD ONLY, never cash
      Min-spend $3 on $2 welcome vouchers
      COGS-backed: $3 face ≈ $0.90 real cost
      Vouchers funded by FSG campaign budget — never the stall
      Caps: per-txn, daily, one voucher per visit
    6 · CRM & intelligence output
      Item-level customer profiles
      RFM · segments · win-back — existing
      AI advisor → recommended actions
      One-click campaign → voucher core → measured at the same counter
    7 · 🔀 Different routes — discuss later
      🔀 Wallet as tender — phase ②, same scan rail
      🔀 Online ordering / order-ahead — phase ③
      🔀 Non-voucher diner + voucher on cash/PayNow fallback detail
      🔀 Multi-voucher or voucher+wallet in ONE scan
      🔀 Per-stall settlement of voucher funding — M2
      🔀 Offline / uPOS-down degraded mode
```

## Reading order
- The happy path = branch **1** top-to-bottom (the worked example: 2 kopi · $3 bill · $2 voucher ·
  $1 paid · 300 coins).
- Branch **3** is what FSG asks uPOS in Week 0 — Q1 + Q5 gate the whole phase.
- Branch **7** items are intentionally undesigned; pull one into a session to spec it.

## Data flow — the counter transaction (sequence)

```mermaid
sequenceDiagram
    autonumber
    actor D as Diner (webapp)
    participant C as CIP API + DB
    participant U as uPOS (till)
    actor K as Cashier

    K->>U: bills 2x kopi = $3
    rect rgb(245,245,245)
    note over D,C: ① Register (first visit, <60s)
    D->>C: phone
    C-->>D: OTP
    D->>C: OTP + PDPA consent
    C-->>D: welcome pack 5x$2 (#1 unlocked)
    end
    rect rgb(245,245,245)
    note over D,C: ② Arm voucher (nothing burned)
    D->>C: use voucher #1
    C-->>D: QR token (90s, single-use) — voucher stays ISSUED
    end
    rect rgb(235,245,235)
    note over C,U: ③ Scan at tender — ONE atomic call
    D->>K: shows QR
    K->>U: scans
    U->>C: POST /tender/scan {token, bill $3, stall, txn_id} (HMAC)
    note over C: validate (single-use · window · min-spend)<br/>→ #1 REDEEMED · #2 UNLOCKED<br/>→ +300 coins PROVISIONAL · tender_intent
    C-->>U: {approved, deduct 2.00}
    U-->>K: balance $1 due
    C-->>D: (poll ~2s) ✓ redeemed · #2 unlocked
    D->>K: pays $1 cash/PayNow
    end
    rect rgb(235,240,250)
    note over U,C: ④ Evidence — async, may lag
    U->>C: webhook sale.completed {txn_id, items[2x kopi], tenders}
    note over C: match by txn_id → items → profile<br/>coins PROVISIONAL → CONFIRMED<br/>recon: voucher $2 = FSG campaign budget
    end
    note over C: ⑤ RFM/segments/AI → next campaign voucher → back to ②
```
