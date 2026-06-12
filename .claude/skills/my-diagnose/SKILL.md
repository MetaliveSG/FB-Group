---
description: Diagnose CRM / capture-loop / loyalty / multi-tenant data-flow issues in the FB Group F&B CRM — check DB state, scope filters, JWT actors, idempotent sync drift
user-invocable: true
---

You are diagnosing a data-flow or behaviour issue in the **FB Group F&B
CRM PoC**. Your job: isolate the failure to a specific layer (auth →
routing → service → DB → frontend) using direct queries and curl, not
guesses.

Read these files to understand the system before debugging:
- `apps/api/app/main.py` (router registration)
- `apps/api/app/api/routes/<relevant>.py` (entry point of the broken endpoint)
- `apps/api/app/services/<relevant>.py` (business logic)
- `apps/api/app/auth/{access.py,deps.py,permissions.py}` (scope + permission resolution)
- `apps/api/app/loyalty/engine.py` (for any points/accrual issue)
- `apps/api/app/db/session.py` (DB session lifecycle)
- `~/.claude/.../memory/build-state.md` (architectural decisions + recorded lessons)
- `docs/architecture/architecture.md` (capture loop, multi-tenancy, identity model)

## Diagnostic Toolkit

Use these in order; escalate to the next tier only when the current one is inconclusive.

### Tier 1 — Reproduce with curl (fast, deterministic)

Most "it doesn't work" reports are isolated by replaying the request with
clean credentials. Boilerplate:

```bash
# Staff login
TOK=$(curl -fs -X POST http://localhost:8000/api/v1/auth/staff/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"owner@makan.sg","password":"Password123!"}' | jq -r .access_token)

# Customer OTP
CODE=$(curl -fs -X POST http://localhost:8000/api/v1/auth/customer/otp/request \
  -H 'Content-Type: application/json' -d '{"phone":"+6580000000"}' | jq -r .debug_code)
CTOK=$(curl -fs -X POST http://localhost:8000/api/v1/auth/customer/otp/verify \
  -H 'Content-Type: application/json' \
  -d "{\"phone\":\"+6580000000\",\"code\":\"$CODE\"}" | jq -r .access_token)

# Make the failing call
curl -i "<URL>" -H "Authorization: Bearer $TOK"
```

**Interpretation:**
- 401 `missing_token` / `invalid_token` / `token_expired` → auth layer (header missing, token bad, or TTL expired — 8h demo default)
- 401 `wrong_actor` → using customer token on staff route or vice versa (`Customer` token has `actor: "customer"`, staff has `actor: "user"`)
- 403 `forbidden` → permission missing (consult `permissions.py`) OR wrong merchant scope (resolve_merchant denied)
- 404 `customer_not_found` / `not_found` → either resource doesn't exist, OR tenant isolation blocked the read (correctly: a foreign-merchant customer is 404 not 200)
- 409 `conflict` → idempotent guard fired (e.g. duplicate redemption, insufficient points, stage mismatch)
- 400 — body validation failed; check the Pydantic error detail

### Tier 2 — Inspect the database directly

When the API path looks correct but data is missing/wrong:

```bash
# Open psql against the Docker DB
docker-compose -f infra/docker-compose.yml exec db psql -U fbgroup -d fbgroup

# Or one-shot from host
docker-compose -f infra/docker-compose.yml exec -T db psql -U fbgroup -d fbgroup \
  -c "<SQL query>"
```

Common diagnostic queries:

```sql
-- Customer + loyalty + merchant lookup
SELECT c.id, c.full_name, c.phone, c.email,
       la.scope_type, la.scope_id, la.points_balance, la.lifetime_points,
       la.tier, la.visit_count, la.last_visit_at
FROM customers c
LEFT JOIN loyalty_accounts la ON la.customer_id = c.id
WHERE c.phone = '+6580000001';

-- Recent transactions for a merchant
SELECT t.id, t.created_at, t.amount, t.points_earned, c.full_name
FROM transactions t LEFT JOIN customers c ON c.id = t.customer_id
WHERE t.merchant_id = '<mid>'
ORDER BY t.created_at DESC LIMIT 20;

-- Recent reward txns for a customer's merchant account
SELECT rt.created_at, rt.txn_type, rt.points, rt.reason
FROM reward_transactions rt
JOIN loyalty_accounts la ON la.id = rt.account_id
WHERE la.customer_id = '<cid>' AND la.scope_type = 'merchant' AND la.scope_id = '<mid>'
ORDER BY rt.created_at DESC LIMIT 20;

-- Verify coalition membership
SELECT c.name, cm.merchant_id, m.name AS merchant_name
FROM coalitions c
JOIN coalition_members cm ON cm.coalition_id = c.id
LEFT JOIN merchants m ON m.id = cm.merchant_id;

-- Verify a user's role + scope
SELECT u.email, r.name AS role, ura.scope_type, ura.scope_id
FROM users u
JOIN user_role_assignments ura ON ura.user_id = u.id
JOIN roles r ON r.id = ura.role_id
WHERE u.email = '<email>';

-- Verify menu items + categories for an outlet
SELECT mc.name AS category, mi.name, mi.price, mi.is_available, mi.sort_order
FROM menus m
JOIN menu_categories mc ON mc.menu_id = m.id
JOIN menu_items mi ON mi.category_id = mc.id
WHERE m.outlet_id = '<oid>'
ORDER BY mc.sort_order, mi.sort_order;

-- Open orders by status
SELECT id, status, created_at, total, customer_id
FROM orders WHERE merchant_id = '<mid>' AND status NOT IN ('completed','cancelled')
ORDER BY created_at DESC;

-- Jackpot config drift (compare seed list vs DB)
SELECT item_name, item_price, emoji, weight, sort_order
FROM jackpot_prizes WHERE merchant_id = '<mid>' ORDER BY sort_order;

-- Audit recent privileged actions
SELECT created_at, action, actor_id, entity_type, entity_id, meta
FROM audit_logs WHERE merchant_id = '<mid>' ORDER BY created_at DESC LIMIT 30;
```

### Tier 3 — Inspect FastAPI logs

```bash
docker-compose -f infra/docker-compose.yml logs api --tail 200
docker-compose -f infra/docker-compose.yml logs api --follow  # live
docker-compose -f infra/docker-compose.yml logs api 2>&1 | grep -i "<keyword>"
```

What to look for:
- Tracebacks → exception in a service or route
- "[start] seeding..." → seed status on container start
- "AI insights: Claude call failed, using heuristic fallback: <ExceptionType>" → API key / network egress problem
- "[whatsapp.mock] send" — verify the mock provider is reached for campaign sends
- HTTP request lines with timing — flag any > 1s

### Tier 4 — Reproduce in pytest

For complex multi-step interactions, write a focused test that mimics the
failure:

```python
def test_repro_<issue>(client, db):
    w = make_world(db)
    cust = register_customer(client, email="repro@b.sg")
    # ... reproduce the steps ...
    # assert the bug behavior, then fix and watch it pass
```

Running just that test:
```bash
cd apps/api && .venv/bin/python -m pytest app/tests/<file>.py::test_repro_X -v
```

### Tier 5 — Compare to known-good seed state

```bash
# Drop DB and reseed from scratch (LOSES DATA — confirm first)
docker-compose -f infra/docker-compose.yml down -v
docker-compose -f infra/docker-compose.yml up -d

# Or: reset just the seed via reset_and_seed (also wipes data)
docker-compose -f infra/docker-compose.yml exec -T api python -m app.seed
```

If a fresh reseed shows the system works correctly, the issue is in data
drift, not code. Use Tier 2 to diff the live state from what `build_demo`
would produce.

## Common Issue Playbooks

### 1. Customer scanned QR but no order created
**Layer to check first**: auth (Tier 1).
- 401 → missing/expired token. Refresh OTP.
- 404 `qr_token` not found → QR slug typo. Verify in `qr_codes` table.
- 400 `unavailable_item` → menu item flag. Check `menu_items.is_available`.
- 400 `outlet_mismatch` → trying to order item from a different outlet's menu. The order service validates this.
- 500 → traceback in `app/services/orders.py::create_order`. Tier 3.

### 2. Order created but checkout fails
- 404 `order_not_found` → tenant isolation; the customer's token doesn't own the order. The customer_id on the order row is what matters.
- 409 `order_status` → already checked out, or in a non-checkoutable state. Check `orders.status`.
- 400 `payment_method` → invalid method. Allowed: `cash, card, nets, paywave, paynow`.
- 500 in loyalty engine → exception in `accrue_on_transaction`. Tier 3 logs.

### 3. Checkout succeeded but loyalty points not credited
- Confirm in DB: `reward_transactions` row with `txn_type='earn'` for this account.
- If missing, check `app/loyalty/engine.py::accrue_for_scope` — was a `RewardRule` row active for this merchant? Run:
  ```sql
  SELECT * FROM reward_rules WHERE scope_type='merchant' AND scope_id='<mid>' AND is_active=true;
  ```
- For coalition: verify `coalition_members` entry exists for the merchant before the transaction time.

### 4. Customer doesn't appear in merchant CRM
- Verify `loyalty_accounts` row exists with `scope_type='merchant', scope_id=<mid>` — this is what CRM lists from.
- Check outlet-scope filtering: an outlet-scoped manager only sees customers who transacted at THEIR outlet. Run:
  ```sql
  SELECT DISTINCT customer_id FROM transactions WHERE outlet_id='<oid>';
  ```
- Confirm tenant isolation: the calling token's scope must resolve to this merchant_id (Tier 1).

### 5. AI Insights returning empty / nonsensical recommendations
- Check `generated_by` in the response. If `heuristic`, that's the default; if `claude`, the model was used.
- Inspect `context` field. If `sales.revenue == 0` and `customers.total == 0`, the merchant has no data — heuristic returns the generic "Grow repeat visits" rec only. That's correct behavior.
- If Claude was supposed to run: check `AI_ENABLED=1` + `ANTHROPIC_API_KEY` set. Look for "Claude call failed" in logs (Tier 3). Common causes: bad key, network egress blocked from container, model string typo.

### 6. Jackpot / Wheel "insufficient points"
- See `/my-ops` runbook of the same name.
- Verify cost: wheel=80, jackpot=100. Balance must be >= cost BEFORE the call.
- Verify the customer is calling for the RIGHT merchant_id (their loyalty account is per-merchant).

### 7. Campaign send shows 0 delivered
- Check `campaign_audience` — was an audience built before send? Tests assert `ConflictError("Build the audience before sending")`.
- Check the WhatsApp mock provider in logs — `[whatsapp.mock] send` lines per recipient.
- Check `campaign_messages` rows — `status` should be `delivered` for successes. The mock can also produce `failed` for retry testing.

### 8. Pipeline opp won't advance (PATCH 409 `bad_stage`)
- Each pipeline_type has its own stage set in `PIPELINE_DEFS` (sales vs winback). Verify the new stage is in the correct set.
- Find the opp's pipeline_type: `SELECT id, pipeline_type, stage FROM opportunities WHERE id='<oid>';`
- Valid stages: see `app/models/enums.py::PIPELINE_DEFS`.

### 9. Menu item rename / move not reflected on the live page
- Two layers: backend (DB) and frontend (cached / api-client). If DB has the new name but page shows old, hard-refresh the browser (Cmd+Shift+R).
- For category moves, verify `menu_items.category_id` was updated in BOTH outlet menus (each outlet has its own menu rows — round-14 lesson).

### 10. Seed re-run reports unexpected counts
- Run `python -m app.seed_kampong` against the live container. `_ensure_kampong_jackpot` reports `inserted/updated/removed`.
- `inserted > 0` on a re-run = a new prize was added in `KAMPONG_JACKPOT_PRIZES` since last sync — expected if you edited the seed.
- `removed > 0` = a prize was deleted from the seed — make sure that's intentional (it deletes the corresponding `jackpot_prizes` row).
- `updated > 0` = drifted attrs (emoji / price / weight / sort_order). Expected after seed edits.

### 11. Docker container restart loop
- See `/my-ops` runbook.

### 12. Frontend page renders blank / "client-side exception"
- Round-14 precedent: the api-client TS type asserted fields the backend didn't return. The page crashed only for customers WITH data (empty-state branches rendered fine).
- Diagnosis: compare the api-client interface (`packages/api-client/src/index.ts`) to the backend response schema (`apps/api/app/schemas/...`). If the page reads `o.items.map(...)` and `o.items` is undefined in the live payload, that's the bug — fix the backend schema.

## Output Format

When reporting findings:

```
[LAYER] Auth | Routing | Service | DB | Frontend | Seed | Config
[SYMPTOM] What the user sees
[ROOT CAUSE] What's actually broken, with file:line reference if known
[EVIDENCE] curl response, SQL query result, log line
[FIX] Specific code or data change
[REGRESSION TEST] Optional — pytest test to prevent recurrence
```

## Context

System overview: `docs/architecture/architecture.md` — pay attention to the capture loop
narrative, the multi-tenant `merchant_id` predicate, and the identity model
(customers vs users).

Memory: `~/.claude/.../memory/build-state.md` — every Round entry tells you
what was added/changed and any KIVs. The Round 12 (SQLite VARCHAR overflow),
Round 14 (api-client / schema drift), and Round 5 (port collision, idempotent
seeding) lessons are particularly relevant for diagnosis.

Investigate the issue described below and report findings with root cause and fix.

Issue: $ARGUMENTS
