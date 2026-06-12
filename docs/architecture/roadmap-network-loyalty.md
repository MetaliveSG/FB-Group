# Roadmap — Menu redesign, Foodcourt, and Network Loyalty (universal coin + FX)

> Status: **Phases 1–2 BUILT** (menu redesign + multi-stall foodcourt); **Phase 3 DEFERRED** (universal
> coin + FX + coalition-as-ring, behind the payments-rail gate §5b). Captured 2026-05-30.
> This remains the canonical record of the architecture/product discussion + the funded-vs-unfunded
> economics. Build proceeds phase-by-phase (see §6); Phases 1–2 are coded, Phase 3 is not.

## 1. Vision / one-line

A single F&B platform that flexes from **one hawker stall → a restaurant → a foodcourt of
many stalls**, with a **universal loyalty coin** that works across merchants and regions via
FX. It is a **win-win network**: merchants gain cross-network footfall and retention; the
platform earns **FX spread + cross-merchant redemption fees + breakage** on top of SaaS.

## 2. Hierarchy — one ownership tree + three cross-cutting axes

The model is **not** a single tree. It is a containment tree plus orthogonal scopes that
loyalty attaches to (this is what lets one `scope_type/scope_id` ledger absorb everything).

```
            ┌── Partner-Platform network (cross-platform clearing — SEAM ONLY for PoC) ──┐
PLATFORM  ──┤  (e.g. "FB Group") — runs the default platform program (= "everyone" ring) │
            └── REGION axis (SG / MY / ID …) → currency · locale · tax · timezone · legal ┘
                  └─ COALITION axis (opt-in cross-merchant rings, acceptance + economics)
                        └─ MERCHANT  (the business; earn rules + catalog on the one coin)
                              └─ BRAND
                                    └─ OUTLET (a foodcourt outlet hosts N stall-menus)
                                          └─ Stall-menu / Table / QR
```

- **Containment (strict 1-to-many):** Platform → Merchant → Brand → Outlet → Stall-menu → Table → QR.
- **Cross-cutting (many-to-many):** Coalition, Region, Partner-Platform. A merchant ∈ 0..N coalitions.

> **Structural detail:** see `architecture-org-tree.md` for how the containment tree is
> actually modelled — roles on a self-referential node tree (stall = leaf role, not a fixed
> layer), a thin spine + typed profiles, adjacency `parent_id` + a materialised `path`
> (`a1.b2.c3`) for fast `LIKE 'a1.b2.%'` subtree reads, the uniform QR resolver, and the two
> boundaries (`loyalty_domain_id` vs `settlement_account_id`).

## 3. The three operating models (one reusable menu view)

Build **one** menu component; put a **conditional venue/stall-directory shell** in front of it
that only appears when stall count > 1. The QR resolver decides the mode by stall count.

| Model | Tenancy | Landing screen |
|---|---|---|
| Single stall (~8 items) | 1 merchant · 1 menu | menu directly (category bar + search auto-collapse) |
| Restaurant | 1 merchant · 1 menu | menu directly (full category bar + search) |
| **Foodcourt** | **1 merchant (operator) · N stall-menus** | **stall directory** → tap stall → same menu view |
| Cross-brand alliance | N merchants · opt-in coalition | (loyalty only — not a menu concept) |

**Foodcourt decision:** even *independently-owned* stalls sit under **one merchant (the
operator/merchant-of-record)** — so merchant-wide loyalty spans all stalls with zero extra
machinery (the Koufu/Kopitiam model). The money still has to be **divided back to each stall
owner** → that is a **per-stall sales report** (orders grouped by stall-menu); automated
payout/settlement is a later back-office feature.

**Market study (2025–2026) that this is grounded in:**
- Single restaurant/stall convergence: sticky horizontal **category bar with scroll-spy**,
  **search** pinned near it, row cards (thumb + name + truncated desc + price + badges),
  customisation in a **bottom sheet** (radio for single-choice, checkbox for multi-choice,
  required-first & enforced), **floating cart bar** once non-empty. **Small menus drop the
  tabs/search → one clean scroll.** (me&u, Toast, Square, Storekit, Sunday, Grab/Foodpanda.)
- Foodcourt: **SG (Koufu, Kopitiam/FairPrice) = stall directory / sliding stall tabs**;
  Western (me&u, GoTab) = unified vendor-grouped feed. **One cart spanning stalls, grouped by
  stall → pay once → split into per-stall tickets → collect from each stall.** SG runs
  **operator-level loyalty** (Linkpoints/Koufu wallet) across stalls — maps onto our
  `merchant_id`-scoped loyalty + super_admin drill-in.

## 4. Loyalty / coin model — LOCKED DECISIONS

- **Universal coin only.** One balance per customer. **Not** region-scoped; **not** separate
  per-merchant currencies. "Earn at A, spend at B" is automatic — there is only one wallet.
- **Fixed par** (e.g. `1 coin = $0.01` internal reference accounting unit).
- **Hidden spread** (no explicit FX fee line shown to the customer).
- **Manual FX rates** (admin screen sets per-currency `earn_rate`/`redeem_rate`, versioned).
- **FX only at the local-currency edges** (earn: local spend → coins; redeem: coins → local
  value). **The earn↔redeem spread is platform revenue (monetization #1).**
- **Coalition = an acceptance / economics / settlement RING over the one coin — NOT a wallet
  and NOT a coin split.** It controls (a) earn **rate** at members (a multiplier → a bigger
  number in the *same* wallet), (b) **where** coins may be spent (opt-in acceptance), (c) **who
  reimburses whom** at settlement. No coins are ever siphoned into a "coalition wallet."
- **Opt-in acceptance.** A merchant must enable "accept coins" before diners can burn there
  (honoring a burn costs them, so it must be consensual). The **platform program** is the
  default ring; **named coalitions** are tighter rings adding boosted earn + shared catalog +
  private settlement.
- **One universal `LoyaltyAccount` per customer** (refactor from per-scope accounts). Scope
  (`scope_type/scope_id`) no longer partitions the *wallet* — it qualifies **rules** (earn),
  **catalogs/acceptance** (burn) and **settlement**.
- **Region** entity carries currency + locale + tax + timezone only; it supplies the **local
  currency for FX** and never partitions the coin.
- **Platform** becomes a first-class entity (enables multi-platform / white-label); the
  platform-wide program = the default "everyone" coalition.
- **Cross-platform partnership** = the same coin exchanged with a partner platform at an
  inter-platform FX rate + a clearing ledger. **SEAM ONLY for the PoC** (`partner_platform_id`
  + rate row, stubbed settlement).

### Two ledgers (the source of the "coalition wallet" confusion)
1. **Customer wallet** — ONE universal coin balance. Earn adds, redeem subtracts. That's all
   the diner ever sees.
2. **Settlement ledger** — back-office money *between businesses*: who funded the coins, who is
   reimbursed (in local currency at the redeem FX rate) when coins are honored, and the
   platform's spread/fees. Invisible to the diner. "Coalition" and "pool" live here only.

## 5. Monetization (win-win) + the risks that govern it

**Revenue taps (all off one FX/settlement primitive):**
1. **FX spread** on every earn/redeem (hidden).
2. **Cross-merchant redemption fee** — *optional, per-coalition/per-merchant config* on the
   settlement record. Applies when coins earned elsewhere are redeemed at a merchant. **KIV —
   build the seam, switch on later.**
3. **Breakage** — unredeemed/expired coins (quietly the largest margin in most points programs).
4. SaaS base (existing).

**Why it's a real win-win:** revenue is **usage-aligned** (platform earns when coins move), so
platform and merchant incentives point the same way; merchants gain **incremental footfall**
from diners holding coins earned elsewhere; opt-in fees mean merchants pay to *acquire* traffic.

**The number that makes or breaks it:** merchant **unit economics on a cross-merchant
redemption**. B honors coins + may pay a fee → only works if the incremental diner spends more
than (reimbursement gap + fee). **Design rule: total rake (FX spread + redemption fee) must stay
comfortably below the incremental value the network creates — benchmark ~2–3% (card-network
range).** Above that you tax growth instead of enabling it.

### 5z. Closed-loop is FREE — the platform only monetizes the NETWORK (LOCKED)
The spread + redemption fee are a **clearing charge for moving value across a boundary**
(merchant / region / platform). If nothing crosses a boundary, there is **no cut**:
- **Same merchant** (all its brands, outlets, **and foodcourt stalls under one operator-merchant**)
  → earn and redeem are closed-loop → **$0 spread, $0 fee.** It is the merchant's own loyalty,
  run at the merchant's own cost (only the loyalty value it chose to give). The platform must NOT
  tax a merchant's own program.
- **Cross-merchant** (coalition acceptance, issuer ≠ honorer) → spread + optional fee apply.
- **Cross-currency** (cross-region / cross-platform) → **FX spread on top**, only when the
  currency differs.
- **Fund-at-issuance funds the PAR value only** (reserve = credit-risk cover so a cross-merchant
  redemption is always payable). **The spread is assessed only when the coin is actually redeemed
  cross-merchant** — a same-merchant redemption simply reclaims the issuer's own funding (a wash).

### 5a. "If A issues and B redeems, does B lose money?" — NO (the load-bearing rule)
The merchant who **issues** coins funds them; the merchant who **honors** them is reimbursed —
so B is always made whole. Mechanics:
- **Fund-at-issuance + reserve.** When coins are earned at A, the platform **collects A's funding
  (the PAR/redeem value) from A's settlement/payout** into a **reserve pool** — credit-risk cover
  so a cross-merchant redemption is always payable. The spread is NOT taken here (see §5z).
- **Honorer reimbursed in full, in local currency.** When B honors a redemption, B is reimbursed
  the **value it gave away** from the pool (the money A funded). **B is never out of pocket.**
- **Platform margin never comes out of B's reimbursement.** On a **cross-merchant** redemption it
  comes from (a) the **clearing spread debited to A's funding** and (b) B's **optional acquisition
  fee** — never by shorting B. (Shorting B's reimbursement is the one anti-pattern to avoid.)
- **Net effect:** A bears the loyalty cost *by choice* (retention spend, A sets its own earn
  rate); B is reimbursed **and** gains incremental footfall (the redemption is usually a partial
  discount on a larger order); platform earns spread + fee + **breakage** (A's funding stays in
  the pool if coins are never redeemed); customer feels rewarded.
- **Worked example** (100 coins = S$1): spend S$10 at A → A keeps S$10, funds S$1.00 par into the
  reserve, nets S$9.00. **Same-merchant redeem at A:** A reclaims the S$1.00 — wash, platform cut
  $0. **Cross-merchant redeem at B:** B reimbursed S$1.00, platform debits A ~S$0.05 spread (+
  optional ~S$0.02 fee off B) → B net-positive on a larger order, platform keeps ~S$0.07 +
  breakage.
- **Guardrails:** opt-in acceptance + merchant-set earn rate mean neither A nor B is ever forced
  into a losing position. Settlement is **fund-at-issuance**, not pay-on-redeem, so the pool is
  never short.

**Other standing risks (keep clean, not blockers):**
- **Float & liability** — outstanding coins are a redeemable liability that moves with FX; need
  **expiry + reserve + breakage** discipline.
- **Regulatory** — multi-currency, FX-converted, fee-bearing redeemable value edges toward
  **e-money / stored-value / money-transmission (MAS in SG)**. Frame and structure as a
  **loyalty rewards program**, keep the ledger auditor-clean, get **legal in before go-live**.
  PoC = stub, not a regulated issuer.
- **Two-sided cold-start** — coin value depends on acceptance breadth; merchant opt-in depends
  on coin volume. Needs anchor merchants + a platform-funded early boost.

### 5b. FUNDED vs UNFUNDED — cross-merchant is a CLEARING RAIL, not a loyalty toggle (THE GATE)
This is the hard gate on all network monetization. Two diligence questions expose the same truth:
*"the merchant never paid to buy the coins"* and *"why would B hand over food before it gets the
cash?"* — both are the same problem.

- **Today (and for closed-loop): coins are UNFUNDED.** Issuing a coin just increments a number;
  no cash moves. That is **fine for closed-loop** (earn & redeem at the SAME merchant) because the
  merchant never needs cash — it **pays in-kind at redemption** (gives a free item; eats the COGS
  *then*). No reserve, no guarantee, no payments rail needed. **This is what is buildable now and
  carries the SaaS deal.**
- **Cross-merchant CANNOT run on unfunded coins.** If A's coins are just a number and the diner
  redeems at B, B hands over **real food** for value **A never funded** → B is out of pocket and
  the platform's "fee" is a clip on nothing. **Asking B to accept unfunded cross-merchant coins is
  asking B to give food on a promise the platform cannot back — B is right to refuse.**
- **So cross-merchant requires ALL of the following (it is a payments/clearing product):**
  1. **Funded coins** — the issuing merchant actually pays at issuance, via **payout-netting**
     (platform withholds the funding from the merchant's settlement) or a **prepaid loyalty
     wallet**. Issuing a coin MOVES REAL CASH into the reserve.
  2. **Pre-funded reserve (escrow)**, kept **≥ outstanding coin liability** at all times
     (solvency invariant).
  3. **Real-time authorization** at redemption (like a card tap): platform checks the reserve
     covers it → authorizes → B sees "Approved, S$X confirmed" → B hands over food → cash
     **settles to B on the normal payout cycle**. **B trusts the PLATFORM (guarantor), not A.**
  4. **Platform sits in the settlement/payment flow** and **bears the float/credit risk** (and
     earns the spread/fee for it).
  5. **Likely MAS-regulated** (stored-value / e-money / money-transmission).
- **The platform here is NOT a money machine** — it is a **clearing house clipping merchants'
  loyalty spend as it flows across the network.** The real money is the merchants' marketing
  budget; the platform's spread/fee is a cut of that flow when it crosses a merchant. **No
  merchant funding → no real cross-merchant value → no network revenue (SaaS only).**

| | Closed-loop coin (ship now) | Cross-merchant network coin |
|---|---|---|
| Merchant pays cash? | No — pays in-kind at redemption | **Yes — funds at issuance (netting / wallet)** |
| Reserve / guarantee needed? | No | **Yes — escrow + real-time auth + solvency invariant** |
| Platform in payments/settlement flow? | No | **Yes (it is the guarantor)** |
| Licensing? | No | **Likely MAS stored-value/e-money** |
| Platform revenue | SaaS only | SaaS + FX spread + fees + breakage |

**STRATEGIC GATE:** the cross-merchant funded network is a **fintech/payments rail bolted on top of
the CRM**, not a Phase-3 loyalty feature. **Recommendation: build & demo the CLOSED-LOOP coin
(Phases 1–3 menu/foodcourt/merchant loyalty) for the deal — it needs none of the above. Green-light
the funded cross-merchant network only once the platform is in the payment flow, holds a real
reserve, and has licensing handled. The FX/fee/breakage monetization is gated on THAT, not on the
loyalty logic.**

## 6. Build phases (frontend-first by risk; nothing coded yet)

### Phase 1 — Menu redesign  *(frontend only · low risk · ships first)*
- Sticky **scroll-spy category bar** + **search** (auto-collapse for ≤~8-item stalls → clean scroll).
- **Customise bottom-sheet** replaces inline chips: single-choice = segmented/radio, multi =
  checkboxes, required-first & enforced, live price, qty, "Add — $X".
- **Floating cart bar** (extend existing).
- Schema: none in v1 (render existing flat modifiers in the sheet). **OPEN DECISION:** modifier
  grouping = v1 columns `menu_modifiers.group_name` + `group_type(single|multi)` **vs**
  flat-in-sheet for now.
- Tests: Vitest for filter/scroll-spy; keep suite green.

### Phase 2 — Foodcourt  *(schema + screens · medium)*
- `menus` gains stall columns (`stall_name`, `cuisine`, `logo`/emoji, `sort_order`, `is_open`);
  allow **multiple active menus per outlet**.
- **QR resolver** branches: 1 menu → menu; N menus → **stall directory** → menu view.
- **Cart grouped by stall**; checkout **splits into one Order per stall** (linked by `session_id`)
  → per-stall kitchen tickets.
- **Per-stall sales report** (orders grouped by stall-menu).
- Seed: "Kampong Food Hall" demo merchant, 3–4 stalls.
- Tests: resolver 1-vs-N, stall-scoped order split, tenant isolation.

### Phase 3 — Universal coin + FX + region + coalition-as-ring  *(big · backend refactor)*
- **Region** entity (currency, locale, tax, timezone) + `outlet.region_id`.
- **LoyaltyAccount → one universal balance per customer** (collapse per-scope accounts).
- **FX rate table** (currency → `earn_rate`/`redeem_rate`, versioned) + manual-rate **admin screen**.
- **Currency-stamped ledger** — every `RewardTransaction` records currency, FX rate, coins, local value.
- **Earn** credits the one balance via FX × (merchant × coalition × platform multipliers).
- **Earn also writes the funding leg** — debit the issuing merchant's settlement (redeem value +
  spread) into the **reserve pool** (fund-at-issuance; see §5a).
- **Redeem** = FX at burn + **settlement ledger** (honoring merchant **reimbursed in full** in
  local currency *from the reserve pool*; platform keeps the spread; **optional cross-merchant
  redemption fee** off the honorer — never shorting the reimbursement).
- **Coalition = acceptance/economics ring**: opt-in accept-coins toggle (platform program default);
  named coalitions add boosted earn + shared catalog + private settlement.
- **FX/fee P&L report** — *shows the spread + fees as revenue* (the monetization pitch slide).
- **Cross-platform:** seam only (`partner_platform_id` + rate row, stubbed).
- Tests: FX earn/redeem math, spread accounting, acceptance gating, settlement, region currency.
- **Demo-pragmatic slice:** universal balance + FX rate table + FX-spread revenue report on
  **stub settlement** — demos the monetization without becoming a regulated issuer. Full
  settlement + cross-platform = roadmap.

## 7. Open decisions before Phase 1
1. **Modifier grouping:** v1 columns (`group_name`/`group_type`) vs flat-in-sheet for now.

(All other major decisions in §4 are LOCKED.)
