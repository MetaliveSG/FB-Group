# Testing

## Run
```bash
cd apps/api && .venv/bin/python -m pytest -v      # full backend suite
```
Tests use an isolated in-memory SQLite DB (StaticPool) shared between the test
session and the FastAPI `TestClient`, with RBAC seeded and rate-limiter/OTP reset per
test (`app/tests/conftest.py`). Latest run: **95 passed** across 21 files (see
`artifacts/pytest_results.txt`). Frontend: **37 Vitest tests**.

## Coverage by file (95 backend tests)
| File | Module(s) | What it proves |
|---|---|---|
| `test_health.py` | 12 | health endpoint + secure headers |
| `test_auth.py` | 2 | register/login/refresh, duplicate blocked, wrong password, OTP + **invalid OTP blocked**, **expired token rejected**, actor separation, SSO linking |
| `test_qr_flow.py` | 3 | valid QR → correct menu, invalid QR rejected, outlet isolation |
| `test_ordering.py` | 4 | totals (subtotal/service/GST), invalid/unavailable item blocked, **status lifecycle**, manual/cashier |
| `test_checkout_loyalty.py` | 5, 6 | txn + points, **failed payment → no rewards**, double-checkout blocked, insufficient-points, redeem, **campaign multiplier**, **merchant vs coalition** |
| `test_rewards.py` | 6 | loyalty summary, catalog redeem (+insufficient), spin-the-wheel (deduct/award + insufficient) |
| `test_crm.py` | 7 | record updates after order, segmentation, filter, profile histories, **cross-merchant leakage blocked**, tags/notes |
| `test_crm_salesforce.py` | 7 | activity timeline, tasks create/list/complete, record owner, task tenant isolation |
| `test_crm_advanced.py` | 7 | pipeline summary, opportunity advance-to-won, **activity in timeline**, bulk tag (ids+segment), bulk task, opp isolation |
| `test_pipeline_modes.py` | 7 | **win-back pipeline mode**, stage-must-match-type, **win-back launcher** (RFM→opps+campaign), settings toggle, owner-only PATCH |
| `test_campaigns.py` | 8 | create/audience/send/metrics, segment audience, list w/ metrics, **WhatsApp mock retry**, tenant isolation |
| `test_reports.py` | 9 | summary correct, graph timeseries, top items/peak hours, **forecast**, outlet permission |
| `test_ai_insights.py` | 9 | **AI advisor** heuristic shape (summary/highlights/ranked recs), staff-only, cross-merchant blocked |
| `test_seed_kampong.py` | seed | **Kampong Eats** merchant 4 seeded (2 outlets, 11 SG-local items), owner login, QR resolves menu, **idempotent re-run** |
| `test_jackpot.py` | 2 | **888 Jackpot**: insufficient-coins blocked, spin cost deducted every play, grid 3x3 invariants, **middle-row payline matches outcome** (3-of-a-kind on win, not-all-same on loss), win mints `JACKPOT-*` voucher (+ resets the progressive grand-jackpot pot) |
| `test_my_account.py` | 7 | customer **My Account**: order history shape + **customer isolation** (B can't see A's orders), vouchers list, profile get/update, **mobile required + unique** |
| `test_admin_analytics.py` | 9, 10 | menu CRUD + isolation, **user invite/list/revoke** (+perm+scope), **RFM scoring** |
| `test_org_admin.py` | 1, 10 | brand→outlet(auto-menu)→table→**QR resolves**, permission, tenant isolation, unique table label |
| `test_platform.py` | operator | ecosystem overview, merchant directory, **non-operator blocked**, onboard merchant, suspend, coalitions |
| `test_permissions.py` | 1, 10 | super admin all, **merchant can't see another**, **outlet manager scoped**, staff lacks CRM, **audit log** |
| `test_e2e_capture_loop.py` | 1-11 | golden flow end-to-end (below) |

## Required test flows → where verified
1. Customer scans QR → `test_e2e_capture_loop`, `test_qr_flow`, `test_org_admin`
2. Register/log in → `test_e2e` (OTP), `test_auth`
3. Order items → `test_e2e`, `test_ordering`
4. Checkout w/ simulated payment → `test_e2e`, `test_checkout_loyalty`
5. Rewards issued → `test_e2e`, `test_checkout_loyalty`, `test_rewards`
6. Merchant logs in → `test_e2e`, `test_permissions`
7. Merchant views customer in CRM → `test_e2e`, `test_crm`
8. WhatsApp promo mock → `test_campaigns` (send + retry + metrics) ✅
9. Sales dashboard → `test_e2e`, `test_reports`
10. Forecast → `test_e2e`, `test_reports`
11. Permission boundaries → `test_e2e`, `test_permissions`, `test_platform`

## Frontend tests
`apps/web` — **37 Vitest tests** (format helpers, auth-resilience, stage/role/campaign-type contracts, wheel math). Run `npm test` in `apps/web`.

## Regression checklist (run before any release)
- [ ] `pytest` green
- [ ] `alembic upgrade head` + `downgrade base` succeed on a scratch DB
- [ ] `python -m app.seed` populates all 8 segments
- [ ] `docker compose up` brings db+api+web healthy
- [ ] Golden capture loop works in the browser
