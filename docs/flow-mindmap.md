# CIP Phase ① — Flow (loyalty first, at the existing uPOS counter)

_The LOCKED phase-① flow (decisions 2026-06-12; full spec `architecture/payments.md` §7b/§8).
Drawn as ONE vertical step flow. Routes not yet designed are listed at the bottom._

## The 30-second version (for the FSG room — board + their uPOS CTO)

**Mei Ling's first visit:**
1. **While queueing**, sees *"Scan for $10 FREE vouchers"* — scans, phone number, done. → *FSG gains
   a member in 30 seconds, before she even orders.*
2. Orders 2 kopi; cashier bills **$3 on uPOS** — nothing changes. → *same till, same routine.*
3. Shows her $2 voucher; cashier **scans it with the same uPOS scanner**; **on submit, uPOS checks
   the voucher with CIP** → till shows **$1** → she pays $1. → *FSG knows who bought what, where,
   for how much.*
4. Her phone: **"300 coins earned! Voucher #2 unlocked."** → *a manufactured reason to return — 4
   more times.*
5. Next week the AI notices she loves kopi → sends a kopi voucher. → *marketing that pays for
   itself, measured at the till.*

**The money:** she SEES $5 of free value; FSG PAYS food cost only (≈$1.80, spread over 2+ visits);
FSG COLLECTS $1 cash today vs $0.90 kopi cost — **never cash-negative, even on the free-gift visit.**

**For the uPOS CTO — uPOS is NOT replaced; one integration, all stalls, three capabilities:**
1. **Voucher at tender** (the only new cashier steps): scan the diner's voucher QR (attaches to the
   bill as a tender line) → **on transaction submit, uPOS POSTs to the CIP API** (validate + redeem,
   one call) → **valid: $2 applied, transaction completes**; invalid: till prompts another tender —
   nothing burned, queue keeps moving. *Exactly how gift-card tenders work today.*
2. **After sale:** send the sale record (items, amount, stall, txn id). *Batched or delayed is fine.*
3. *Nice-to-have:* a QR on the printed receipt so members who paid without a voucher still earn.

Same integration later takes the **FS Wallet** as a tender — build once, two products. Signed calls
both ways · idempotent · **zero customer personal data enters uPOS** (PDPA-clean).

## The step flow

```mermaid
flowchart TD
    S1["1 · Diner queues — sees standee:<br/>SCAN FOR $10 FREE VOUCHERS"]
    S2["2 · Scans & registers in 30s<br/>phone + OTP + one consent tap"]
    S3["3 · Welcome pack lands: 5 × $2<br/>voucher #1 unlocked · #2–5 locked"]
    S4["4 · Orders 2 kopi —<br/>cashier bills $3 on uPOS"]
    S5["5 · Diner shows $2 voucher QR<br/>one-time code · 90s · nothing burned yet"]
    S6["6 · Cashier scans the QR —<br/>code attaches to the bill"]
    S7["7 · Cashier SUBMITS the txn —<br/>uPOS POSTs to CIP API"]
    S8{"8 · CIP validates + redeems<br/>ONE atomic call<br/>single-use · min-spend vs final bill"}
    S9["9 · uPOS applies −$2 —<br/>till shows $1 balance"]
    S10["10 · Diner pays $1 cash/PayNow —<br/>transaction completes"]
    S11["11 · Her phone: ✓ redeemed ·<br/>300 coins provisional · voucher #2 UNLOCKED"]
    S12["12 · Later (can lag): uPOS webhook —<br/>items · amount · stall · txn id"]
    S13["13 · CIP matches by txn id:<br/>items → her profile · coins CONFIRMED"]
    S14["14 · CRM/AI: she loves kopi →<br/>sends kopi voucher → she returns"]
    DEC["✗ Invalid: till prompts another tender —<br/>nothing burned, queue keeps moving"]

    S1 --> S2 --> S3 --> S4 --> S5 --> S6 --> S7 --> S8
    S8 -- valid --> S9 --> S10 --> S11 --> S12 --> S13 --> S14
    S8 -- invalid --> DEC
    S14 -. return visit: skip 1–3, voucher #2 .-> S4
```

**Returning diner:** skips steps 1–3 (already a member) — opens the webapp at step 5 with the next
voucher. **No-voucher visit:** pays normally, scans the receipt QR (uPOS capability 3) → earns coins.

## 🔀 Different routes — discuss later (undesigned placeholders)
- Wallet as tender — phase ②, same scan rail (one scan = voucher + wallet remainder)
- Online ordering / order-ahead — phase ③
- Voucher on a cash/PayNow payer where uPOS can't scan (manual fallback detail)
- Multi-voucher in one transaction
- Per-stall settlement of voucher funding — M2
- Offline / uPOS-down degraded mode

## Engineering detail — data flow per actor (the build contract for /tender/scan + the webhook)

```mermaid
sequenceDiagram
    autonumber
    actor D as Diner (webapp)
    participant C as CIP API + DB
    participant U as uPOS (till)
    actor K as Cashier

    D->>C: register (phone + OTP + consent)
    C-->>D: welcome pack 5×$2 (#1 unlocked)
    K->>U: bills 2× kopi = $3
    D->>C: use voucher #1
    C-->>D: QR token (90s, single-use) — voucher stays ISSUED
    D->>K: shows QR
    K->>U: scans — code attaches to bill
    K->>U: SUBMITS txn
    U->>C: POST /tender/scan {token, bill $3, stall, txn_id} (HMAC)
    note over C: ATOMIC: validate → #1 REDEEMED ·<br/>#2 UNLOCKED · +300 coins provisional
    C-->>U: {approved, deduct 2.00}
    U-->>K: balance $1 due → txn completes
    C-->>D: (poll ~2s) ✓ redeemed · #2 unlocked
    D->>K: pays $1
    U->>C: (later, can lag) webhook {txn_id, items, tenders}
    note over C: match by txn_id → items → profile ·<br/>coins CONFIRMED · recon: $2 = FSG budget
```
