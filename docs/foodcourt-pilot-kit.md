# Foodcourt Loyalty Pilot — Kit + Rollout Checklist

_Operational runbook for the **loyalty-only** pilot (no table-QR ordering; keep-your-POS). Capture mode:
**Mode A (cashier-assisted)** on anchor stalls + **printed static QR (Mode B)** on the tail. KPI: **+10%
court transactions (+SGD 2.6M on a $26M base).** North-star equation: **court lift = capture-rate × member
spend-lift → target capture ≥40%, member lift ≥25%.** Strategy/pitch: `docs/cip-vs-salesforce-fnb.md`.
Costs/specs are SG-market illustrative — verify before purchase._

---

## 0. The model (one line)
Stalls keep their own till. CIP runs **enrol → earn (cashier taps phone + $amount) → redeem (cross-stall
coin ring) → grow (RFM/AI pushes)** beside it. A cheap Android per anchor stall runs the **loyalty-till as a
PWA in kiosk mode — nothing installed, nothing changes about how stalls ring sales.**

---

## 1. Pilot kit (bill of materials)

**Per ANCHOR stall (device — ~6–8 highest-revenue stalls):**
| Item | Spec | ~SGD |
|---|---|---|
| Android phone | Android 11+, rear cam ≥8MP, 3GB RAM (Redmi A3 / Galaxy A05 / refurbished) | 100 |
| Stand/cradle | adjustable, weighted | 15 |
| Charger + long cable | always-plugged; route tidily | 10 |
| Anti-theft tether | cable lock / adhesive mount | 10 |
| Kiosk lock | Fully Kiosk Browser (one-time ~$7) **or** free Android screen-pinning | 7 |
| Data SIM (if WiFi weak) | prepaid, low-data plan | 12/mo |
| **Per anchor all-in** | | **~$140 + $12/mo** |

**Per TAIL stall (no device — remaining ~12–14 stalls):**
| Item | Spec | ~SGD |
|---|---|---|
| Laminated **earn QR** | static, stall-scoped, A5 counter card | 2 |
| Sign-up standee | A5/A4, "Scan to join — free welcome voucher" | 3 |

**Court-wide:**
- Entrance standees / posters (×2–3)
- **Cashier quick-ref card** per stall ("Earn in 10s / Redeem in 10s")
- **2 spare devices** (swap on failure/theft)

**Cost summary (20 stalls, 7 anchors):** ~7 × $140 = **~$980 devices** + ~13 × $5 print = **~$65** + spares
~$280 + SIMs ~$84/mo ≈ **~$1,400 capex + ~$100/mo.** (Against $26M base / $2.6M KPI = a rounding error.)

---

## 2. Software setup (config + the build list)
**Already built — just configure:** loyalty engine, vouchers + **welcome voucher**, **no-order earn/redeem**,
RFM, **cross-stall coin ring** (one loyalty domain = the whole court), games, the cashier attach-diner/redeem flow.

**Build before pilot (engineering):**
1. **Loyalty-till PWA** — thin cashier screen: scan member QR / type phone **+ $amount → coins**; scan voucher → redeem. **Stall-scoped URL** (each device opens its stall's till → clean per-stall attribution). Reshape of the existing cashier flow.
2. **LAND sign-up front-door + redemption centre** (memory `buildplan-land-first`, ~5d): QR → phone+OTP → PDPA consent → member + welcome voucher.
3. **Real messaging channel** — WhatsApp BSP **or** SMS. ⚠️ **The one true new integration; non-negotiable** (campaigns are mock today; the *push* is the return-driver).
4. **Pilot analytics** — holdout cohort tagging, baseline-revenue import, capture-rate + funnel dashboard.
5. *(optional)* **offline queue** on the till if foodcourt connectivity is shaky.

---

## 3. Pre-pilot checklist (Week 0)
**Operator / commercial**
- [ ] Pilot agreement signed: scope, duration (rec. 6–8 wks), success metric
- [ ] **Operator mandate** that stalls use the scan every transaction (the make-or-break)
- [ ] **Baseline data access** — court's historical revenue (no baseline = no measurable lift)
- [ ] Stall list + revenue history → **rank anchors vs tail** (Pareto)

**Tech**
- [ ] Loyalty-till PWA live + **stall-scoped URLs** generated
- [ ] Sign-up front-door + welcome voucher live; PDPA consent + privacy notice live
- [ ] Coin ring configured: all 20 stalls in **one loyalty domain** (earn-anywhere/redeem-anywhere)
- [ ] **Real WhatsApp/SMS channel wired + test send confirmed**
- [ ] RFM segments + campaign templates ready: welcome/2nd-visit · win-back · cross-stall · off-peak · birthday
- [ ] **Coupon-budget guardrails set** (caps, margin-per-redemption) — the Luckin CFO discipline
- [ ] Baseline revenue imported; **holdout split rule** defined (random % of enrolled get no campaigns)
- [ ] Pilot dashboard live (capture rate · enrolments · earn events · device uptime)

**Devices**
- [ ] Procure + provision anchor devices: kiosk-lock to stall URL, test QR scan in real lighting
- [ ] **Connectivity verified at each stall** (WiFi reachable or SIM data working)
- [ ] Tethers + chargers fitted; 2 spares provisioned
- [ ] Printed earn-QR + sign-up standees produced for tail stalls + entrance

**People**
- [ ] Cashier training (10-min) + quick-ref cards at every stall
- [ ] **Cashier scan incentive** agreed (small per-enrolment/compliance reward)
- [ ] **Diner welcome incentive** compelling enough that they *want* to scan
- [ ] End-to-end **dry run** at 1 stall: enrol → earn $X → redeem voucher → cross-stall redeem

---

## 4. Launch checklist (Week 1 — capture ramp)
- [ ] Standees/QR up at all 20 stalls + entrance; devices live + kiosk-locked at anchors
- [ ] **Daily capture-rate monitor** (members ÷ transactions) — the leading indicator that predicts everything
- [ ] Welcome sends firing on enrolment
- [ ] **Cashier-compliance spot-checks** per stall; coach laggards immediately
- [ ] Device/connectivity uptime check (a dead till = lost capture)

---

## 5. Run checklist (Weeks 2–6/8 — activate levers)
**Daily:** capture rate · enrolments · earn events · device uptime · per-stall compliance %
**Weekly:**
- [ ] RFM refresh → fire **win-back · cross-stall · off-peak** campaigns
- [ ] **Coupon budget vs guardrail**; margin-per-redemption within cap
- [ ] **Holdout integrity** — confirm control group received nothing
- [ ] Intervene on low-compliance stalls (retrain / re-incentivise / escalate to operator)
- [ ] Games live; monitor return-visit lift

---

## 6. Measurement & readout
- **North-star:** court +10% = **capture ≥40% × member lift ≥25%**
- **Causal proof:** treated vs **holdout** lift (defeats "it would've grown anyway" — KPMG-proof)
- **Funnel:** capture rate → 2nd-visit → cross-stall rate → spend/member
- **Baseline:** pilot-period vs prior-period / YoY (controls seasonality)
- **Honesty:** 6–8 wks proves **mechanism + leading indicators + holdout lift** → **extrapolate to annualised +10%**; a fully-measured +10% on total revenue needs ~8–12 wks
- **Deliverable:** readout deck → annualised $ projection on the $26M base → convert to full contract

---

## 7. Risk register (failure modes → mitigation)
| Risk | Mitigation |
|---|---|
| **Low capture** (cashiers don't scan) — #1 killer | operator mandate · cashier incentive · strong welcome voucher · daily spot-checks |
| Connectivity drops | data SIM per anchor · *(optional)* offline queue on the till |
| Device theft/loss | tether + kiosk MDM · cheap units · 2 spares |
| Amount fraud (tail self-scan) | receipt-photo audit · per-claim caps · **anchors carry the clean number** |
| Margin erosion (bought growth) | coupon-budget caps · RFM-targeted not blanket · margin-per-redemption |
| Seasonality skews result | holdout control absorbs it |
| Mock send channel | **real BSP/SMS is non-negotiable** — wire it Week 0 |
| Stall non-cooperation | anchors (device) + tail (printed QR); defensible court number from anchors alone |

---

## 8. Go / no-go gates
- **Week 1 gate:** capture rate trending to ≥40% on anchors → if not, fix compliance/incentive *before* spending on campaigns.
- **Week 3 gate:** treated cohort showing frequency lift vs holdout → if flat, adjust offers/segments.
- **Readout gate:** annualised projection ≥ the +10% KPI → green-light full $26M rollout.

**Bottom line:** the hardware is ~$1.4k and trivial. The pilot is won on **capture rate (cashier compliance)
+ a real send channel + margin discipline + a clean holdout.** Spend your attention there.
