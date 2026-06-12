# CIP Phase ① — Flow Mindmap (loyalty first, at the existing uPOS counter)

_Working map of the LOCKED phase-① flow (decisions 2026-06-12 — see `decisions.md`; full spec
`architecture/payments.md` §7b/§8). **Branches marked 🔀 are different routes to be discussed
later** — they're placeholders, not designs. Renders as a diagram on GitHub (Mermaid)._

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
