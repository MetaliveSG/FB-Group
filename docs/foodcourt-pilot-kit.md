# Foodcourt Pilot — Kit + Rollout Checklist (dual-lane: order-ahead + receipt-QR)

_Operational runbook for the greenlit **+10% foodcourt pilot** at **FSG** (foodcourt operator; all stalls on
**one POS vendor — uPOS**, one unit per stall). KPI: **+10% court transactions (+SGD 2.6M on a $26M base).**
**All customer-facing = webapp (PWA), no app install.** uPOS is **not replaced** — small tweaks only
(see `docs/payments.md §8 (uPOS)`)._

**Two lanes — cover everyone, force nobody:**
- **Non-queue → ORDER-AHEAD** *(the +10% engine).* Scan stall/court QR → CIP webapp → order + pay (PayNow/
  cards) + collect when ready (**pickup** fulfilment mode — no table numbering; `docs/architecture-fulfilment-modes.md`).
  Exact data; stacks **balker-recovery + ticket upsell (+10–15%) + frequency + retention.**
- **Queue → SCAN RECEIPT QR** *(the retention net).* Order + pay at the uPOS counter as usual → uPOS prints a
  **signed receipt QR** → diner scans → CIP webapp → **verified coins.** Opt-in (a subset of queuers scan).
- **Coins/loyalty accrue on both.** (Loyalty-only alone caps ~**+3–6%** → order-ahead is the engine, loyalty the amplifier.)

**Measurement uses the uPOS outbound webhook** (100% of sales → full baseline + airtight +10%), **NOT** the
opt-in receipt scans. **Sequencing:** beachhead — **anchor stalls × peak hours** — then expand. **Hybrid**:
both lanes run alongside the existing queue, nothing replaced.

---

## 0. The two flows
**Order-ahead (non-queue):** scan stall QR → webapp → cart + checkout → **pay (PayNow/cards)** → order
reaches the stall (**uPOS inbound injection** *if it's a small tweak*, else a **light order screen**) → cook →
**"ready"** → "Order #42 ready" push → collect.
**Receipt-QR (queue):** order + pay at the **uPOS counter** as usual → uPOS prints a **signed receipt QR** →
diner scans → webapp (phone+OTP first time) → **verified coins** for that transaction.
Coins · RFM · AI · win-back run on **both** lanes.

---

## 1. Pilot kit (bill of materials)
**Queue lane needs NO device** — just uPOS's signed **receipt QR** (a uPOS tweak) + a printed counter standee.
**Order-ahead fulfilment needs a way for the order to reach the stall:** if **uPOS inbound injection** is a
small tweak → app orders show on the stall's **own uPOS screen → no device needed**; otherwise provision the
order screen below (anchor stalls only).

**Per ANCHOR stall — an ORDER SCREEN (only if uPOS inbound injection is NOT available):**
| Item | Spec | ~SGD |
|---|---|---|
| Android phone/tablet | Android 11+, 3GB RAM; tablet (~8–10") easier for order tickets | 100–150 |
| Stand/cradle + always-on charger | weighted; tidy cable | 25 |
| Anti-theft tether | cable lock / adhesive mount | 10 |
| Kiosk lock | Fully Kiosk Browser (~$7) or Android screen-pinning | 7 |
| Data SIM (if WiFi weak) | prepaid | 12/mo |
| *(optional)* BT receipt printer | ESC/POS, for paper order tickets | 60 |
| **Per anchor all-in** | | **~$150–230 + $12/mo** |

**Court-wide:**
- **Entry QR standees** per stall + at the court entrance (stall/court context QR → opens that menu; **not** a table QR)
- **Pickup-counter signage** ("Collect here — show your order number")
- Cashier/stall **quick-ref card** ("New order → cook → tap Ready")
- **2 spare devices**

**Cost (20 stalls, 7 anchors):** ~7 × $200 ≈ **~$1,400** + signage ~$150 + spares ~$300 ≈ **~$1,900 capex
+ ~$84/mo.** (Rounding error vs $26M base / $2.6M KPI.) *Tail stalls need no device until they opt into
order-ahead — just an entry QR standee.*

---

## 2. Software — config + the build list
**Built — configure:** foodcourt multi-stall browse, menus, cart, checkout, order status lifecycle,
loyalty + welcome voucher, cross-stall coin ring, RFM, games.

**Build before pilot (engineering, in priority order):**
1. **Real payment** — PayNow (SG primary) + cards. ⚠️ **#1 critical-path** (checkout is mock today; no
   order-ahead without real money). Plugs into the existing checkout/`record_sale` path.
2. **uPOS tweaks** (one vendor → one integration, all stalls — spec in `docs/payments.md §8 (uPOS)`):
   - **Outbound webhook** — uPOS POSTs every sale to CIP → **100% capture + the +10% baseline/measurement.** *(the high-payoff small tweak)*
   - **Signed receipt-QR** — uPOS prints a QR with a **signed/registered txn token** on the receipt → queue-lane verified earn. *(small)*
   - **Inbound order injection** — accept CIP orders into the uPOS queue → order-ahead on the stall's own POS, no order screen. *(verify it's actually small; else use the order screen.)*
3. **Fulfilment mode = pickup** (`docs/architecture-fulfilment-modes.md`): `Order.fulfilment_type`
   (+migration, default dine_in), per-storefront `fulfilment_modes`, **pickup-number** generation, **table
   attachment conditional** (off for these stalls).
4. **Receipt-QR claim flow** (webapp) — scan signed QR → match the webhook txn → award verified coins.
5. **Stall order screen (KDS-lite)** — *only if inbound injection (2c) isn't available* — receive app orders → "mark ready".
6. **Ready notification + collection** — "Order #N ready" push (needs the **real messaging channel** — WhatsApp BSP / SMS).
7. **Menu digitisation × anchor stalls** — items, prices, modifiers.
8. **Pilot analytics** — driven off the **webhook** (full court): adoption %, ticket lift, baseline, holdout.

---

## 3. Pre-pilot checklist (Week 0)
**Operator / commercial**
- [ ] Pilot agreement: scope, duration (rec. 6–8 wks), success metric, **anchor stall list**
- [ ] **Operator mandate**: anchor stalls fulfil app orders reliably (watch the screen, mark ready)
- [ ] **Baseline data access** — court + per-stall historical revenue (no baseline = no measurable lift)
- [ ] Adoption push agreed: signage, a **skip-the-queue incentive** (e.g. coins/discount for first app order)

**Tech**
- [ ] **Real payment live + tested** (PayNow + cards) — settlement to the right account per stall
- [ ] Fulfilment mode = **pickup** on anchor stalls; **table numbering OFF**; pickup-number working
- [ ] Stall **order screen** live; "mark ready" → push tested end-to-end
- [ ] **Real WhatsApp/SMS channel wired + test send** (ready-notify + campaigns)
- [ ] Anchor **menus digitised** (items/prices/modifiers) + photos where available
- [ ] Coin ring across stalls (one loyalty domain); welcome voucher; PDPA consent live
- [ ] RFM segments + campaign templates (welcome, win-back, cross-stall, off-peak) + **coupon-budget guardrails**
- [ ] Baseline imported; **holdout** split for the retention measurement; pilot dashboard live

**Devices / floor**
- [ ] Anchor order screens provisioned, kiosk-locked, **connectivity verified per stall**
- [ ] Entry-QR standees up (stalls + entrance); **pickup-counter signage** up
- [ ] Tethers + chargers + 2 spares
- [ ] **Dry run**: app order → pay → stall screen → mark ready → push → collect

**People**
- [ ] Stall training (receive → cook → mark ready); quick-ref cards
- [ ] Adoption crew for week 1 (floor staff steering queuers to the app at peak)

---

## 4. Launch checklist (Week 1 — adoption ramp)
- [ ] Entry QR + pickup signage live; anchor order screens live
- [ ] **Daily: app-adoption %** (app orders ÷ total orders) — the leading indicator that predicts the lift
- [ ] **Stall fulfilment SLA** monitored (orders acknowledged + marked ready promptly — a missed app order kills trust)
- [ ] Skip-the-queue incentive firing on first app order; welcome voucher on enrol
- [ ] Device/connectivity uptime check

---

## 5. Run checklist (Weeks 2–6/8)
**Daily:** app-adoption % · ticket (app vs counter) · order-screen uptime · fulfilment SLA per stall
**Weekly:**
- [ ] RFM refresh → win-back · cross-stall · off-peak campaigns
- [ ] Coupon budget vs guardrail; margin-per-redemption within cap
- [ ] Holdout integrity (retention slice)
- [ ] Intervene on slow-fulfilment stalls (retrain / escalate to operator)
- [ ] Games live; monitor return-visit lift

---

## 6. Measurement & readout
- **Source of truth = the uPOS webhook** → **100% of sales** (queue + app), so the **baseline and the +10%
  are airtight**, not a sample. (The opt-in receipt-QR scans drive *earn*, not measurement.)
- **+10% engine = order-ahead.** Track: **app-adoption %** · **ticket lift (app vs counter)** · **balker/
  peak recovery** (incremental transactions) · **frequency lift** · retention (treated vs **holdout**).
- **Baseline:** webhook history (or operator data) — pilot-period vs prior-period / YoY per stall (controls seasonality).
- **Honesty:** 6–8 wks proves **mechanism + adoption curve + per-channel lift** → **extrapolate to
  annualised +10%**; a fully-measured +10% on total court revenue needs ~8–12 wks + decent adoption.
- **Deliverable:** readout deck → annualised $ on the $26M base → green-light full rollout.

---

## 7. Risk register (failure modes → mitigation)
| Risk | Mitigation |
|---|---|
| **Low app adoption** — the #1 killer now | skip-the-queue incentive · floor crew steering queuers at peak · target peak/regulars · strong welcome |
| **Stall doesn't fulfil app orders** (breaks the promise) | operator mandate · fulfilment SLA monitor · audible order alert · escalate fast |
| Real-payment issues / settlement per stall | test thoroughly Wk0; per-stall settlement account mapping; reconciliation |
| Connectivity drops | data SIM per anchor; *(optional)* offline queue |
| Margin erosion (bought growth) | coupon-budget caps · RFM-targeted · margin-per-redemption |
| Seasonality skews result | per-stall baseline + YoY; holdout on the retention slice |
| Device theft | tether + kiosk MDM · spares |
| **uPOS tweaks slip** (webhook/QR/injection late or "not small") | get the 4-Q capability answer + cost/timeline **Wk-0** (`docs/payments.md §8 (uPOS)`); webhook + signed-QR are the must-haves; inbound injection has the order-screen fallback; FSG (the paying customer) applies the pressure |

---

## 8. Go / no-go gates
- **Week 1:** app-adoption trending up on anchors + stalls fulfilling reliably → if not, fix adoption/fulfilment *before* scaling.
- **Week 3:** app orders show ticket lift + frequency vs baseline/holdout → if flat, adjust incentive/menus/segments.
- **Readout:** annualised projection ≥ +10% KPI → green-light full court rollout (+ takeaway/delivery modes, more stalls).

**Bottom line:** hardware is trivial (queue lane needs none; order-ahead needs an order screen only if uPOS
inbound injection isn't available). The pilot is won on **app adoption + reliable fulfilment + real payment +
the uPOS webhook + margin discipline.** Critical path = **real payment + the uPOS webhook/signed-QR tweaks**;
everything else is config or a lite slice of existing code. **Dual lanes (order-ahead + receipt-QR) on one
webapp, uPOS untouched but for small tweaks.** Loyalty rides along as the amplifier.
