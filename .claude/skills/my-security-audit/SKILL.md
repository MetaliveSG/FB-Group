---
description: Security audit for the FB Group F&B CRM — secrets, JWT, RBAC, multi-tenant isolation, input validation, mock providers, OWASP checks
user-invocable: true
---

You are a senior application security engineer auditing a multi-tenant
F&B CRM PoC that handles customer PII (phone, email, birthday), merchant
business data (orders, revenue, customer lists), loyalty points (treated
as currency), and platform-wide operator privileges. Treat every finding
seriously — this is the foundation for a production retention platform.

## Audit Checklist

Read ALL of these files first, then run every check below. The project's
documented threat model lives in `docs/security.md` — read it before starting
so you can compare claims vs reality.

Key files:
- `apps/api/.env.example` and the running `.env` (if present)
- `apps/api/app/core/config.py` (settings)
- `apps/api/app/core/security.py` (password hashing, JWT)
- `apps/api/app/core/rate_limit.py`
- `apps/api/app/auth/{access.py,deps.py,permissions.py,otp.py}`
- `apps/api/app/main.py` (CORS + secure headers middleware)
- `apps/api/app/api/routes/*.py`
- `apps/api/app/services/*.py`
- `apps/api/app/services/whatsapp.py` (mock provider)
- `docs/security.md` (documented threat model)
- `infra/docker-compose.yml`

### 1. Secrets & Credential Exposure
- Read `apps/api/.env.example` — only placeholders, no real values
- Read `apps/api/.env` (if it exists in working tree) — check it's `.gitignore`d once a repo exists
- Read `app/core/config.py` — verify `JWT_SECRET` default (`"dev-secret-change-me-in-production"`) is replaced in production. `ANTHROPIC_API_KEY` should be loaded from env, never logged
- Grep for hardcoded secrets across `app/`: `JWT_SECRET=`, `password=`, `api_key=`, `Bearer `, `"sk-ant-"`
- Check `app/main.py` startup — verify no `print(settings)` or full-config dump
- Check `infra/docker-compose.yml` — env vars passed in correctly, secrets *not* baked into image
- **Logs** — currently no structured secret-redaction filter; flag if introducing logging that may leak `password`/`access_token`/`api_key`
- Verify `~/.claude/.../memory/` paths aren't being committed accidentally

### 2. SQL Injection
- Verify ALL queries use SQLAlchemy ORM with bound parameters (no string concatenation, no f-strings inside `text()` calls). Grep:
  ```bash
  grep -rn "text(f\"" apps/api/app/
  grep -rn "execute(f\"" apps/api/app/
  grep -rn "\"\\+ .*\\+ \"" apps/api/app/ | grep -i "select\\|insert\\|update\\|delete"
  ```
- Check service-layer raw SQL (currently none expected) — if any appear, flag P0
- Verify `crm.py::list_customers` and `crm.py::get_profile` filter parameters are parametrized through SQLAlchemy `where()` — they are, but verify

### 3. JWT Security
- Read `app/core/security.py` — verify `create_access_token` uses HS256 + a strong secret (PyJWT)
- Verify token TTL is short: `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30, demo Docker uses 480 = 8h)
- Verify refresh-token rotation pattern (new refresh issued on each use, old becomes invalid? — check `auth/refresh` route)
- Verify the `type` claim distinguishes access vs refresh (refresh tokens must not pass as access)
- Verify the `actor` claim distinguishes `customer` vs `user` and middleware (`get_current_customer`/`get_current_user`) enforces it → wrong actor returns 403 `wrong_actor`
- **Caveat**: tokens are returned in the response body and stored in localStorage by the frontend (documented in `security.md`). For production, recommend httpOnly + SameSite cookies. Frontend `auth-resilience.test.ts` should cover the self-healing path

### 4. Multi-Tenant Isolation (the highest-impact surface)
For every CRM / orders / transactions / loyalty / opportunities / campaigns / jackpot / wheel / activities endpoint:
- Verify the underlying query is filtered by `merchant_id`
- Verify the `Scope` (`app/auth/access.py`) is consulted: `require(scope, "...", merchant_id)`
- Verify outlet-scoped users restrict reads further via `_allowed_outlets(scope, merchant_id, outlet_id)` (see `app/api/routes/crm.py`, `reports.py`)
- Run a targeted test: M1 owner token + `?merchant_id=M2_id` should return 403, not 200 with M2 data

The tests `test_crm.py::test_cross_merchant_isolation`, `test_pipeline_modes.py`, `test_admin_analytics.py::test_menu_tenant_isolation`, and `test_permissions.py::test_outlet_manager_scoped` cover this — verify they still pass and that new endpoints have analogous coverage.

### 5. RBAC & Authorization
- Read `app/auth/permissions.py` — verify the permission map matches what routes call
- Read `app/auth/access.py::Scope` — verify scope resolution from role assignments (platform / merchant / brand / outlet) is correct and a higher scope subsumes lower
- Spot-check: `staff` cannot reach `crm.view`; `outlet_manager` cannot reach `merchant.manage` or `user.manage`; `merchant_owner` cannot reach `platform.*`
- `super_admin` is the only wildcard — verify it's set ONLY for `superadmin@platform.sg` (and not silently granted by a default)
- User invite flow (`/admin/users`) — verify GRANTABLE_ROLES excludes `super_admin` and that scope can only place users within the inviter's own merchant boundary

### 6. Input Validation (Pydantic v2)
- Every request body must have a Pydantic schema with explicit field constraints
- Spot-check string fields for length caps (`max_length`), numeric fields for bounds (`ge`, `le`), regex for phone (`+65...`), enum constraints for status fields
- Verify `Order.total` is computed server-side from menu prices, NOT taken from client (read `app/services/orders.py::create_order`). Server-side pricing prevents price tampering
- Verify wheel/jackpot/redemption endpoints accept only `merchant_id` from body, never `cost` or `prize` (server reads from config / loyalty engine)
- Verify campaign send doesn't trust a client-supplied audience — `build_audience` derives from segment query

### 7. Authentication Mocks (PoC limitations to flag explicitly)
The PoC uses mocks that are intentionally listed in `docs/security.md`:
- OTP (in-process `otp_store`, debug code returned in dev only via `DEBUG=true`)
- WhatsApp (`MockWhatsAppProvider` + `send_with_retry`)
- Payments (simulated outcome via `force_outcome` param)
- SSO Google/Apple (mock — no real provider token verification)

Audit: confirm these mocks are clearly mock-only (don't leak as production paths). Confirm `DEBUG=true` is NOT set in any production config. Flag any new mock added without explicit documentation.

### 8. Rate Limiting & DoS
- Read `app/core/rate_limit.py` — verify the sliding-window limiter is wired on OTP issuance (`auth/customer/otp/request`) and login (`auth/customer/login`, `auth/staff/login`)
- Verify wheel/jackpot/redeem are server-side gated by points balance (a rate-limit isn't strictly needed, but a misuse cap might be)
- **Caveat**: limiter is in-process — won't survive multi-replica deployment. Production should use Redis (already documented as a PoC limitation)
- WebSocket endpoints? FB Group doesn't currently use WS — flag if one is added without rate limiting

### 9. CORS, Secure Headers, CSRF
- Read `app/main.py` — verify `CORSMiddleware` uses explicit `allow_origins` list (from `settings.CORS_ORIGINS`), allowed methods/headers explicit
- Verify `SecureHeadersMiddleware` sets: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Strict-Transport-Security`, `Content-Security-Policy`
- Bearer-token API, no cookie auth → no CSRF concern in the API. If cookies are introduced (production migration to httpOnly cookies), add CSRF tokens

### 10. Money & Points Handling
- All money columns are `Numeric(12,2)` and operated on as `Decimal` via `app.core.money.money()` — verify no `float()` slip-through in services
- Loyalty points are integers — verify no negative-points exploit (jackpot/wheel cost must `>=` balance check happens BEFORE the deduction)
- Coalition vs merchant accrual: verify coalition rule scope is checked; a customer can't accrue coalition points if the merchant isn't a member
- Audit `app/loyalty/engine.py::accrue_for_scope` and `accrue_on_transaction` for any path that adds points without writing a ledger row (every points change must produce a `RewardTransaction`)
- Voucher minting (`RewardRedemption`) — verify `voucher_code` is unique (the round-12 lesson: VARCHAR(16) collision precedent — voucher_code now has its own column)

### 11. PII & PDPA-style Data Protection
Singapore PDPA requires reasonable safeguards on customer PII. Audit:
- `customers.phone` — stored as `+65...`, no encryption at rest yet
- `customers.email`, `customers.birthday` — same
- No data-retention or erasure flow yet — flag as a P2 KIV for PDPA compliance
- Customer profile exposes their full visit/order history to merchant staff with `crm.view` — appropriate (legitimate business interest under PDPA) but document
- Cross-merchant: a customer transacting at multiple merchants has multiple `LoyaltyAccount` rows; no merchant should see another merchant's customer view → tenant isolation (§4)
- Operator (super admin) can see all merchants' customer data — document this as platform-operator-trusted

### 12. Audit Logging
- Verify `app/services/audit.py::record` is called on privileged actions:
  - CRM tag/note/owner assignment
  - Task create/update
  - Opportunity create/update
  - Bulk actions
  - Win-back launch
  - Merchant suspend/activate
  - User invite/revoke
- Audit logs are append-only (`audit_logs` table). Verify no path mutates an existing row

### 13. Dependency Security
- Read `apps/api/requirements.txt` — verify pinned versions
- Spot-check for known-vulnerable releases: `fastapi==0.115.6`, `SQLAlchemy==2.0.36`, `PyJWT==2.10.1`, `bcrypt==4.2.1`, `pydantic==2.10.4`, `anthropic==0.104.1`. Compare against the project's last audit date
- Read `apps/web/package.json` and `packages/api-client/package.json` — verify no obvious-bad deps

### 14. Mock Provider Side Channels
The `MockWhatsAppProvider` and OTP store are in-process. Audit:
- Mock OTP `debug_code` only returned when `settings.DEBUG=True` (verify `app/api/routes/auth.py`)
- Mock WhatsApp logs full message body to stdout — flag if message templates ever contain `{password}` or sensitive PII (current templates only have `{name}`)
- Simulated payment `force_outcome` should be gated to dev/test only — verify it isn't usable on production

### 15. Operator Console & Privileged Surface
- `/platform/*` requires `super_admin`. Read `app/auth/deps.py::require_super_admin`
- Verify operator can't impersonate a merchant or customer — operator drill-down passes `?merchant_id=` to ordinary CRM endpoints but their actor stays `user` with `super_admin` scope
- Suspending a merchant (`PATCH /platform/merchants/{id}`) — verify it sets a flag that gates future API calls but doesn't delete data

## Output Format

For each finding, report:
```
[SEVERITY] CRITICAL / HIGH / MEDIUM / LOW / INFO
[LOCATION] file:line
[ISSUE] What's wrong
[RISK] What could happen (multi-tenant leak, points fraud, RBAC bypass, etc.)
[FIX] Specific code change
```

Severity:
- **CRITICAL** — secret in repo, multi-tenant data leak, RBAC bypass, points/money fraud, SQL injection, JWT forgery
- **HIGH** — mock provider behaving as production, missing rate limit on auth, input validation bypass, audit log gap
- **MEDIUM** — missing PII encryption, log redaction gap, dependency with known CVE (non-exploit), CORS too permissive
- **LOW** — documentation drift, header policy soft, default config not hardened
- **INFO** — observation, no action needed

Sort findings by severity (CRITICAL first). End with a summary count and a one-line risk posture statement.

## Context

This is the **FB Group F&B CRM PoC** — multi-tenant SaaS for Singapore F&B retention.
Documented threat model: `docs/security.md`. Production hardening checklist also lives there.
Architecture: `docs/architecture.md` (RBAC + scope resolution under "Multi-tenancy" and "Identity model" sections).

Key invariants to preserve in any audit recommendation:
- Multi-tenant isolation by `merchant_id` predicate (single highest-priority guarantee)
- RBAC with scoped role assignments and least privilege
- Decimal money, never float; integer points with mandatory ledger writes
- Server-side pricing (no client-set prices)
- Mock providers explicitly flagged as PoC-only
- Audit logs for privileged actions

$ARGUMENTS
