# CIP Wallet — scope (closed-loop stored value + auto-reload)

_The **Starbucks / Alipay** model: each diner has a CIP **stored-value balance**, tops it up, and pays for
order-ahead from it — with **auto-reload** so they're never blocked. Closed-loop, **deposit-only (no
cash-out).** Strategic role: **float + lower fees + lock-in (M5)** → compounds the **+10%.** Pairs with
`docs/payments-scope.md`. **Phasing:** pilot ships **pass-through** payment (no wallet) to prove +10% without
regulatory lead time; **wallet is the fast-follow lock-in amplifier.** Status: PLAN. Not legal advice._

## Ownership (decided 2026-06-09): **FSG's wallet, CIP = white-label rails**
- The wallet is **FSG-issued / FSG-held** (top-ups land in **FSG's** HitPay account → FSG holds the float +
  owes the balance; FSG is the stored-value issuer). **CIP provides the ledger + app/UX + auto-reload tech.**
- **One branded wallet per enterprise** — **FS Wallet** (FSG), **Tasty Wallet** (Tasty Wok Group), … each
  spendable **within that group only**.
- **Scoped to the loyalty-domain ring** (`loyalty_domain_id`) — the **same boundary as coins**, so **wallet +
  coins share one account** per customer per enterprise. (Per the CLAUDE.md glossary, "enterprise" = a top
  node carrying `is_loyalty_domain`; for FSG the group node carries **both** flags → loyalty-domain ==
  settlement-boundary == enterprise coincide. Scoping to `loyalty_domain_id` is correct + future-proof.)
- **Light/single-purpose holds while the enterprise = ONE settlement boundary** (one legal merchant-of-record
  — true for the FSG pilot). If an enterprise later spans **multiple settlement boundaries**, wallet money
  across them = **multi-merchant stored value (heavier MAS) + cross-settlement (M2)** — flag then.
- **Cross-enterprise = COINS ONLY.** **Money (wallet) NEVER crosses an enterprise** — each wallet is
  closed-loop within its loyalty domain (→ keeps it single-purpose/light; a universal cross-enterprise *money*
  wallet does **not** exist, by design). The **coins** layer *can* cross via the **coalition ring** (earn at
  FSG, redeem at Tasty = SG-Eats-Rewards). Coins = **loyalty value, not stored money** → **no e-money
  licensing** for cross-enterprise use; only cross-enterprise *coin redemption* needs **coalition
  clearing/settlement (M2, deferred)** + the discipline *"never wire unverified earn to the coalition pool."*
- **Layering:** *within enterprise* = wallet (money) + domain coins; *cross-enterprise* = coalition coins only.

## Model (the decisions, locked)
- **Closed-loop, deposit-only** — spendable only at FSG's foodcourt; **no withdrawal/cash-out** → lightest
  stored-value treatment (not money transmission).
- **FSG = merchant-of-record** — diner pays FSG; FSG settles stalls. This keeps it **single-purpose** (pay
  FSG for the foodcourt) and de-risks the multi-stall question. (Same choice as payments settlement.)
- **Coins + wallet in one account** — money balance (wallet) alongside the loyalty coin balance.

## Top-up
- **Manual top-up — any PSP method** (PayNow, cards, GrabPay/ShopeePay, Apple/Google Pay).
- **Auto-reload (chosen: fixed increment when low) — via a saved card:**
  > `if balance < THRESHOLD → off-session charge RELOAD_AMOUNT → credit wallet` (e.g. **< $5 → reload $20**).
  - Requires a **saved/tokenised card** (off-session charge). **PayNow / e-wallets are on-session → manual
    top-up only**, can't be silently auto-charged (exactly like Alipay auto-debiting the linked card).
  - **Explicit opt-in consent** to auto-reload (clear T&Cs — consumer protection).
  - Fixed increment (not exact-shortfall) on purpose → **fewer PSP charges + more float** (preserves the
    wallet's whole economic advantage).
- **Top-up bonus promo** ("top up $50, get $5") — margin-friendly growth lever (Starbucks/Luckin play).

## Spend
- Order-ahead checkout **debits the wallet** → **one tap, no PSP round-trip per order** (fast + low fee).
- If insufficient and auto-reload is on → reload fires first, then debit. If off → prompt a manual top-up.

## Build — on the existing ledger (don't buy; there's no turnkey SG F&B wallet)
A wallet = **a ledger + a top-up rail.** Reuse the **loyalty posting-ledger pattern** (`reward_transactions`:
append-only, balance = SUM(ledger), idempotent, domain-stamped) with **currency** instead of coins.
- New pieces: **top-up flow** (PSP credit), **debit-at-checkout**, **card vaulting + off-session charge**
  (PSP), the **auto-reload rule**, **balance + auto-reload-consent UI**. Modest — most of it reuses existing
  code + the PSP integration you're building anyway.
- *(Hardened ledger primitives — Formance/TigerBeetle — exist if ever needed at scale; overkill for pilot.)*

## Regulatory & safeguarding (verify with a lawyer — cheap one-pager)
- **Deposit-only + closed-loop + FSG-as-collector ≈ the light lane** (likely **limited-purpose** under the
  MAS **Payment Services Act**, outside e-money licensing). **Confirm the multi-stall point** (spent across
  independent stalls) — FSG-as-merchant-of-record is the structural fix.
- **Float housekeeping:** segregate the float (don't commingle), **unspent balance = a liability** on the
  books, a **refund / dormancy policy**, no cash-out. Light, but real — do it properly.

## Economics (why it's worth it)
- **Lower fees:** one PSP charge per **$20 reload** vs a fee on every **$5** meal → big margin win at foodcourt tickets.
- **Float:** you hold pre-loaded cash (Starbucks holds ~US$1B+).
- **Lock-in (M5):** standing balance + card-on-file = the diner *must* come back → **directly compounds the +10%.**

## Phasing & dependencies
- **Pilot:** **pass-through** payment (prove +10%; don't wait on stored-value legal).
- **Fast-follow:** the wallet, once the **legal one-pager** clears and the **PSP saved-card** is wired (the
  same PSP/e-wallet choice from `docs/payments-scope.md` powers top-ups).

## Open decisions (tune at build)
- Reload **threshold + increment** (default **< $5 → $20**), min/max balance, auto-reload **opt-in default**
  (recommend opt-in **off** by default, prompt after first manual top-up).
