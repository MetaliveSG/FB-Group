# FB Group F&B CRM — PoC Demo Playbook (deal pitch)

_The 12-minute live demo that shows a diner → loyalty → retention loop working end to end,
on a polished mobile app, backed by a real multi-tenant platform with proof it works._

## 0. The one-liner
**"Turn every walk-in diner into a known, returning customer — automatically."**
A diner scans the table QR, orders, pays, and earns coins + plays games — and that activity
instantly materialises in the merchant's CRM (profile, spend, frequency, churn risk, segments),
ready for win-back campaigns. One platform, three tiers: **Operator → Merchant → Diner.**

## 1. Why it matters (30 sec)
- F&B margins are thin; **repeat customers** are the profit. Most hawker/QSR merchants capture **zero** customer data today.
- This captures identity at the table (QR + OTP), rewards repeat visits (coins, tiers, **games**), and hands the merchant a CRM + AI next-best-actions to bring diners back.
- Built mobile-first; **architected to ship as a native app** next phase (shared design tokens + typed API + Lucide icons).

## 2. Live demo flow (the money path) — ~6 min
Open on a **phone-width** viewport. Two merchants are seeded; use **Kampong Eats**.

1. **Scan → order** — `http://localhost:3001/t/kampong-bedok-01`
   - Browse the warm, mobile-first menu → set quantity → **Add to cart** → sticky cart bar → **View cart** (bottom sheet).
2. **Log in (OTP)** — phone `+6581000000` → OTP auto-fills (demo mode) → **Place Order**.
3. **Pay** — pick a method (Card/NETS/PayNow/PayWave/Cash) → **Pay** → ✅ success → **"+N coins earned"**.
4. **Rewards hub** (bottom tab, with a pulsing "play" dot) — coins balance, tier progress, **Play & Win** menu, catalog (redeem coins for free items), vouchers, recent activity.
5. **Games (hero moment)** — tap **🎰 888 Jackpot**: full-screen gold cabinet, a **real progressive Grand Jackpot pot ticking up**, reels wheel → decelerate → land; on a win → **fireworks + confetti** and a food voucher. Then **🎡 Spin the Wheel** (gold-coin/food prize art).
6. **Orders + Account** — order history shows the order **completed**; Account edits mobile/birthday/gender.
7. **Flip to the merchant** — `http://localhost:3001/merchant/login` → `owner@kampongeats.sg` / `Password123!` → **CRM**: the diner you just created is there with spend/visits/segment; **AI Insights** gives ranked next-best actions; **Operator** console shows the whole ecosystem.

**The pitch beat:** *"Everything that diner just did — order, payment, coins, the voucher they won — is now a customer record the merchant can act on. That's the loop competitors don't have."*

## 3. Proof it actually works (2 min) — credibility
- **Automated tests:** **152 backend (pytest) + 45 frontend (Vitest), all green** — `artifacts/pytest_results.txt`, `artifacts/frontend_test_results.txt`.
  - Rewards system specifically: happy path, **insufficient-coins blocked**, **multi-tenant isolation** (a diner can't spend M1 coins at M2 / redeem another merchant's reward), grand-jackpot **grow + persist + reset-on-win**, voucher survives prize deletion, actor separation, drain-to-insufficient.
- **Live HTTP proof report:** `artifacts/rewards_proof_<date>.txt` — **14/14 scenarios PASSED** with REQUEST/RESPONSE/CHECKS/RESULT transcripts (loyalty, catalog, wheel, jackpot+grand pot, vouchers, orders, profile, negative paths).
- **Structured JSON logging** (`app/core/logging.py`) on every rewards event (`wheel_spin`, `jackpot_play/win/insufficient`, `reward_redeemed`) with `customer_id`/`merchant_id`/`balance`/`cost` context — CloudWatch/OTel-ready (sample lines in the proof report).
- **Server-authoritative games:** outcomes + balance checks happen on the server (atomic check+deduct) — can't be gamed in the browser.

## 4. Platform credibility (1 min)
- **Multi-tenant** by `merchant_id` on every query; RBAC (operator/owner/manager/staff/customer), tenant-isolation **test-proven**.
- FastAPI + SQLAlchemy 2.0 + **PostgreSQL** (41 tables, 13 migrations, 93 endpoints), Next.js 14, fully Dockerised, AWS-target (ECS Fargate + RDS).
- Money as `Decimal`; coins are a pure engagement currency (not cash-redeemable).
- Design system in `packages/ui` (tokens + Lucide) → **web now, React-Native/Expo later** with ~60–70% reuse.

## 5. What's real vs mocked (be honest)
- **Real & working:** ordering, checkout state machine, loyalty accrual + tiers, coins, catalog redemption, spin-the-wheel, 888 jackpot + **persistent progressive pot**, vouchers, CRM capture + segments, RFM, win-back launcher, operator console, multi-tenant + RBAC.
- **Mocked for the PoC (swap-in ready):** payments (Stripe/NETS/PayNow), OTP (→ **WhatsApp OTP**), WhatsApp send, Google/Apple SSO, AI Insights (deterministic heuristic unless `ANTHROPIC_API_KEY` set).

## 6. Roadmap after the deal (next phase) — KIVs
1. **Referral program** (top growth lever).
2. **Scan-QR-to-earn** for kiosk/cashier in-person orders (bridge offline POS → CRM).
3. **Country-code dropdown** at registration (E.164 storage already in place → multi-region).
4. **WhatsApp OTP + deeplinks** (replace mock).
5. Native mobile app (React Native/Expo), merchant-console redesign, real payment/SSO providers, AWS deploy.

## 7. Demo credentials (quick reference)
| Persona | URL | Login |
|---|---|---|
| Diner | `/t/kampong-bedok-01` | OTP `+6581000000` (auto-fills) |
| Merchant owner | `/merchant/login` | `owner@kampongeats.sg` / `Password123!` |
| Operator | `/operator/login` | `superadmin@platform.sg` / `Password123!` |

**Regenerate the live proof anytime:** `cd apps/api && .venv/bin/python scripts/rewards_proof.py` → writes `artifacts/rewards_proof_<date>.txt`.
