# Vouchers & redemption — design (decided 2026-06-05)

**Status:** agreed; build in progress. The decision: a **shared Voucher core** with **two issuers**
(loyalty + campaign) and **one cashier redemption flow**. Grounded in BreadTalk / Ya Kun / Starbucks /
Grab practice (see §5).

## 1. Campaign vs loyalty program — the distinction

| | **Loyalty program** | **Campaign** |
|---|---|---|
| Value is… | **Earned** (points for spend) | **Granted** (free) |
| Who | Every member, ongoing | A targeted segment / trigger |
| When | Always-on, permanent | Time-bound / event-triggered |
| Goal | Retention | Acquire · reactivate · boost |
| Configured | Once, in **Settings** | Per-campaign (audience + schedule + reward) |
| Examples | earn 1pt/$1, "$1 off for 100 coins", wheel, jackpot, birthday points | welcome pack, win-back, weekday promo, referral |

**Litmus test:** does the customer *earn* it (spend → points → redeem, always-on, everyone) → **loyalty**;
or is it *granted* to a target/trigger (just signed up, lapsed 60d, birthday) → **campaign**.

## 2. The resolving nuance — shared core, split issuance

Both produce the **same voucher** and are **redeemed the same way** (cashier scans at the counter); only
the **issuance trigger** differs. So:

- **Voucher + redemption = shared core** (the primitive): a voucher carries `value` + rules, and there is
  ONE cashier validate-&-redeem flow.
- **Loyalty** = the *earned* issuer (points catalog, birthday, wheel/jackpot) — configured in Settings.
- **Campaign** = the *granted* issuer (welcome pack, referral, promo, win-back) — configured per-campaign.

This mirrors BreadTalk: **"1-for-1 Welcome eVoucher"** (granted on signup = campaign) and **"Bun Voucher
for 1 point"** (earned = loyalty) live in the same app, redeemed identically at the till.

→ **"10× $1 vouchers on registration, 1 usable per day/week/month"** = a **welcome CAMPAIGN** (trigger =
register) that issues vouchers from the core, with the per-period cap as a voucher rule. The points-catalog
**"$1 off for 100 coins"** is **loyalty**, redeemed through the *same* core.

## 3. Current state (as-built, the gap)

- ✅ **Issue**: `services/rewards.py::redeem_catalog_item`, `spin_wheel`, `jackpot.py::play_jackpot` all
  create a `RewardRedemption` (`models/loyalty.py`) with a `voucher_code`. Customer lists via `GET /me/vouchers`.
- ❌ **Redeem (the missing half)**: NO cashier validate/redeem endpoint; `status` never transitions to
  "used"; vouchers are NOT applied to an order total (no `Order` voucher field); checkout ignores them.
- ❌ **Rules**: no `value`-application, no validity window, **no per-day/week/month cap**, no single-use guard.
- ⚠️ **Status inconsistency**: catalog/wheel write `status="redeemed"`, jackpot writes `"active"`.
- ❌ **Issue-on-registration**: only a first-*visit* bonus in **points**, not vouchers on signup.

## 4. Build plan

1. **Voucher core + cashier redemption** (the real gap; Foundation-adjacent — settles on the
   checkout / future `record_sale()` path):
   - Voucher fields: `value` (Decimal), `single_use`, `valid_from/until`, `min_spend`, `per_period`
     cap (none|day|week|month), status `issued → redeemed` (+ `expired`/`void`); normalise the
     issuer status values.
   - `POST /vouchers/{code}/redeem` — **staff-scoped**, scan-QR or enter-code → validate (active, in
     window, single-use, per-period cap, min-spend, right tenant) → mark used → apply value to the order.
   - Apply-at-checkout (voucher reduces the order total; recorded on the transaction).
2. **Issuance hooks**: a welcome-campaign trigger on registration (the 10× $1); keep catalog/wheel/jackpot
   issuing into the same core.
3. **UI**: customer "My Vouchers" (show QR to cashier) + a cashier "Scan/Redeem voucher" action on the
   Orders/POS screen.

## 5. Industry reference (SG F&B)

- **BreadTalk Group Rewards** — 1pt/$1 store-credit; redeem from 1 point; **Bun Vouchers** (≤$2.30 item)
  redeemed by **presenting the app/card at the counter**; **1-for-1 Welcome eVouchers on signup** (~$35);
  birthday perks; **referral $2 voucher**.
- **Ya Kun** — 8pts/$1; **pay in-app**; **$2 cash voucher** + **$6.30 set-meal voucher**, redeemed in-app at payment.
- **Starbucks** — welcome pack (50% off first drinks + 1-for-1); earn/redeem by **scanning a QR**.
- **Grab/GrabFood** — new-user vouchers redeemed by **scanning a QR or entering a code**.

**Pattern:** welcome vouchers granted on signup (often 1-for-1, not "10× $1 stacked"); redemption is
digital (show app / scan QR / enter code), single-use, with validity windows + per-transaction limits;
two issuance sources (earned vs granted), one redemption mechanic. *(A 10× $1 drip is workable but
off-trend — a single 1-for-1 welcome + a per-visit cap is the more conventional default.)*
