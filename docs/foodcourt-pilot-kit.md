# Foodcourt Pilot — Kit + Rollout Checklist (order-ahead model)

_Operational runbook for the greenlit **+10% foodcourt pilot**. **Model: order-ahead + pay + collect**
(CIP becomes the ordering+payment channel; **pickup** fulfilment mode — no table numbering, an **order/
pickup number** instead; see `docs/architecture-fulfilment-modes.md`). **Loyalty is baked in as the
amplifier.** KPI: **+10% court transactions (+SGD 2.6M on a $26M base).**_

**Why order-ahead, not loyalty-only:** loyalty-only retains existing demand and caps ~**+3–6%**.
Order-ahead **adds** demand — it stacks **balker-recovery (skip the peak queue) + ticket upsell (+10–15%)
+ frequency + retention** — and captures **~100% automatically** (every app order is a known diner + exact
amount → clean measurement, no cashier-compliance risk). **Order-ahead is the engine; loyalty the amplifier.**

**Sequencing — beachhead, not big-bang:** run on **anchor stalls × peak hours** (where skip-the-queue value
+ adoption + lift are highest and most measurable), loyalty included, then expand. Runs **hybrid** — app
orders *alongside* the existing queue, not replacing it.

---

## 0. The flow
Diner opens app → browses the court's stalls (built) → cart + checkout (built) → **pays in-app (real
payment)** → order routes to **the stall's order screen** → stall cooks → **"mark ready"** → diner gets
**"Order #42 ready"** push → collects. Coins/loyalty accrue automatically; RFM/AI/win-back run on top.

---

## 1. Pilot kit (bill of materials)
**Per ANCHOR stall (~6–8 highest-revenue / longest-queue stalls) — an ORDER SCREEN (not a loyalty till):**
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
   in-app ordering without real money). Plugs into the existing checkout/`record_sale` path.
2. **Fulfilment mode = pickup** (per `docs/architecture-fulfilment-modes.md`): `Order.fulfilment_type`
   (+migration, default dine_in), per-storefront `fulfilment_modes`, **pickup-number** generation, **table
   attachment made conditional** (off for these stalls).
3. **Stall order screen (KDS-lite)** — receive app orders → **"mark ready"** (+ optional printed ticket).
4. **Ready notification + collection** — "Order #N ready" push (needs the **real messaging channel** —
   WhatsApp BSP / SMS; same dependency as campaigns).
5. **Menu digitisation × anchor stalls** — items, prices, modifiers onboarded.
6. **Pilot analytics** — app-adoption %, ticket lift, baseline import, holdout (for the loyalty/retention slice).

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
- **+10% engine = order-ahead.** Track: **app-adoption %** · **ticket lift (app vs counter)** · **balker/
  peak recovery** (incremental transactions) · **frequency lift** · retention (treated vs **holdout**).
- **Capture is ~100% on the app channel** (digital) → amounts exact, measurement clean.
- **Baseline:** pilot-period vs prior-period / YoY per stall (controls seasonality).
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

---

## 8. Go / no-go gates
- **Week 1:** app-adoption trending up on anchors + stalls fulfilling reliably → if not, fix adoption/fulfilment *before* scaling.
- **Week 3:** app orders show ticket lift + frequency vs baseline/holdout → if flat, adjust incentive/menus/segments.
- **Readout:** annualised projection ≥ +10% KPI → green-light full court rollout (+ takeaway/delivery modes, more stalls).

**Bottom line:** hardware is ~$2k and trivial. The pilot is won on **app adoption + reliable stall
fulfilment + real payment live + margin discipline.** Build **real payment first**; everything else is
config or a lite slice of existing code. Loyalty rides along as the amplifier.
