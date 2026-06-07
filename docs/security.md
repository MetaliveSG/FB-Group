# Security (Module 11)

## Security checklist (implemented in PoC)
- [x] **Input validation** — Pydantic v2 schemas on every request body/query (types, lengths, regex for phone, enum constraints).
- [x] **SQL injection protection** — SQLAlchemy 2.0 ORM with bound parameters everywhere; no string-built SQL.
- [x] **Password hashing** — bcrypt with per-password salt (`app/core/security.py`).
- [x] **Back-office password policy** (`app/core/passwords.py::validate_password_strength`) — operator + merchant-owner + staff-invite + node-account passwords must be **≥8 chars with ≥1 uppercase letter, ≥1 number, and ≥1 special character** (Pydantic `field_validator` on `OperatorCreateIn` · `MerchantCreateIn.owner_password` · `InviteUserIn` · `NodeAccountCreateIn` → `422` on a weak value). Customer passwords keep the ≥8 floor (consumer UX). Verified by `test_operator_roles.py::test_operator_password_policy`.
- [x] **JWT auth** — short-lived access tokens + refresh tokens; type + actor claims verified; expiry enforced (expired token → 401 `token_expired`).
- [x] **Auth middleware / dependencies** — `get_current_customer` / `get_current_user` separate diner vs staff actors; wrong actor → 403.
- [x] **RBAC + least privilege** — role→permission matrix; scoped assignments (platform/merchant/brand/outlet). Every admin surface is permission-gated: user management `user.manage` (owner); menu `menu.manage`; org brands `brand.manage` / outlets+tables `outlet.manage`; campaigns `campaign.manage`; settings `merchant.manage`. User invites can only grant non-super-admin roles within the merchant's own scope.
- [x] **Granular operator roles + separation of duties** — the operator tier is no longer all-or-nothing: **Owner** (full + manages operators), **Admin** (merchants+coalitions+full drill-in), **Onboarding** (onboard/edit only), **Support** (read-only + read-only drill-in). Each `/platform/*` route requires a specific `platform.*` permission (`require_platform`). **SoD:** only the Owner holds `platform.operators.manage`, so a non-Owner operator cannot escalate their own privileges or remove the Owner; revoke is guarded against removing the **last Owner** and self-revoke. Drill-in into a merchant is capability-mapped (Support = read perms only → write attempts 403). Verified by `test_operator_roles.py`.

  **Operator permission matrix** (`auth/permissions.py::ROLE_PERMISSIONS`; ✓ = allowed, — = 403):

  | Capability (permission) | Owner | Admin | Onboarding | Support |
  |---|:--:|:--:|:--:|:--:|
  | View overview / KPIs (`platform.overview.view`) | ✓ | ✓ | ✓ | ✓ |
  | View merchant directory + coalitions (`platform.merchants.view`) | ✓ | ✓ | ✓ | ✓ |
  | Onboard / edit merchants (`platform.merchants.onboard`) | ✓ | ✓ | ✓ | — |
  | Suspend / activate merchants (`platform.merchants.suspend`) | ✓ | ✓ | — | — |
  | Create / edit coalitions (`platform.coalitions.manage`) | ✓ | ✓ | — | — |
  | Drill into a merchant (`platform.merchant.access`) | ✓ full | ✓ full | — | ✓ read-only |
  | Add / revoke operators (`platform.operators.manage`) | ✓ | — | — | — |

  *"Add"* = create the entity (onboard merchant / add operator); *"edit"* = onboard-perm covers merchant
  edits, suspend is its own perm; *"see"* = the view perms (read-only for Support on drill-in). Owner is
  `super_admin` (`*` wildcard). Each row is asserted in `test_operator_roles.py`.
- [x] **Tenant data isolation** — enforced at **three layers**: (1) scope is server-derived from the user's own role assignments (`access.py::resolve_scope` → `accessible_merchant_ids`, unforgeable from the request); (2) the `resolve_merchant` chokepoint rejects any foreign `?merchant_id=` → 403 (used by every merchant-scoped route); (3) services re-check entity ownership by `merchant_id` → 404 on a foreign id (IDOR-safe). Upline is one-directional: a merchant can't reach `/platform/*` (super-admin-only), and a downline brand/outlet manager can neither **read nor write** merchant-level config — full `GET/PATCH /org/settings` and `GET/PUT /org/loyalty` are `merchant.manage` (owner-only), so a downline manager 403s even by direct URL. Navigation that needs a feature toggle reads `GET /org/nav-flags` instead (`order.view` floor) — a projection of only the non-sensitive booleans (`pipeline_enabled` + module flags, already public via the anonymous QR context), never spin costs or earn rates. **Proven** by 22 dedicated tests (`test_tenant_isolation.py`, `test_tenant_isolation_adversarial.py`, `test_platform.py`) — incl. an operator **positive control** (super-admin crosses → 200, so the 403s are scope-based not deny-all), customer-JWT replay rejection, B→A symmetry — plus live HTTP proof (owner@makan attacking Kampong → 403/404 across settings/loyalty/crm/reports/brands/platform, with **zero residue** in the victim tenant).
- [x] **Web/POS login segregation** — `User.kind` splits dashboard logins (email+password) from POS operators (`kind="pos"`, PIN-only). POS accounts have a synthetic `@pos.local` email + a locked random password and are hard-rejected by `login_user`; web users aren't resolvable by PIN. Two-way isolation (`test_pos_pin.py`).
- [x] **POS PIN encryption-at-rest** — till PINs are owner-revealable (so can't be hashed) → encrypted with **Fernet** (AES-128-CBC + HMAC, `app/core/pin_crypto.py`) under a key from `PIN_SECRET` (env, distinct from `JWT_SECRET`; prod → KMS). A DB dump exposes only ciphertext; decrypt only for the authorized owner-reveal / PIN-login. PINs unique per storefront. **KIV:** KMS-sourced key + rotation re-issue.
- [x] **Privileged POS action gating** — voiding a paid sale needs `order.void` (Supervisor+); a cashier can't. The POS takes a momentary Supervisor PIN to authorize, attributing the void to the supervisor in the audit log.
- [x] **PDPA consent at capture** — terms/marketing consent recorded (versioned) at register/OTP/SSO and via `/auth/customer/consent` (`customer_consents`).
- [x] **Suspend enforcement** — a suspended tenant's staff are blocked at login + order; operators stay able to un-suspend.
- [x] **Rate limiting** — sliding-window limiter on OTP issuance + login (abuse/brute-force prevention).
- [x] **OTP hardening** — TTL expiry, attempt cap, constant-time compare, single-use.
- [x] **CORS restriction** — explicit allowed origins (env), limited methods/headers; plus a private-LAN/`.local` origin regex so same-wifi devices (demo on a phone) are allowed without opening it to the public internet.
- [x] **Log secret redaction** — every log record (file + console) is scrubbed of JWTs, `Authorization` headers, passwords, and long keys before write (`app/core/logging.py`); access + business errors are logged with context (method/path/code), never the bearer token.
- [x] **Secure headers** — `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, HSTS, CSP.
- [x] **Audit logs** — append-only `audit_logs` for privileged actions (order status change, manual order, payment, CRM tag).
- [x] **Secrets via env** — `JWT_SECRET`, DB URL etc. from environment; `.env.example` only; no hardcoded credentials in code.
- [x] **No price tampering** — server prices order items from the catalog; client cannot set prices.
- [x] **Error hygiene** — domain errors mapped to safe responses; unhandled errors return generic 500 (no stack traces leaked).

## Threat model (summary)
| Asset | Threat | Mitigation (PoC) | Production hardening |
|---|---|---|---|
| Customer PII | Cross-tenant read | `merchant_id` isolation + scope tests | Row-level security, per-tenant audit alerts |
| Auth tokens | Theft / replay | Short expiry, HTTPS, refresh rotation | httpOnly cookies, token binding, rotation + revocation list |
| Login/OTP | Brute force / SMS pumping | Rate limits, attempt cap, TTL | Redis limits, CAPTCHA, device fingerprinting, real SMS provider w/ fraud controls |
| Payments | Tampered amounts | Server-side pricing; PoC simulated | Real PSP, webhook signature verification, idempotency keys |
| Privileged actions | Abuse by staff | RBAC + audit logs | SoD, approval workflows, anomaly detection |
| DB | Injection | ORM/bound params | Managed Postgres, least-priv DB user, encryption at rest |
| Secrets | Leakage | Env vars, gitignored `.env` | AWS Secrets Manager / KMS, rotation |

## Known PoC limitations (security)
- Rate limiter + OTP store are **in-process** (per-instance) — not shared across replicas. Production: Redis.
- SSO (Google/Apple) is a **mock**: no real provider token verification.
- Payments are **simulated**; no real PSP, no PCI scope.
- JWTs are returned in the response body and stored in browser localStorage for the demo (XSS-exposed); production should use httpOnly, SameSite cookies.
- No CSRF tokens (bearer-token API, no cookie auth in PoC).
- CSP is strict on the API; the Next.js app needs its own CSP in production.
- PDPA **consent** is captured (terms/marketing, versioned); POS PINs are encrypted at rest. Still TODO: field-level PII encryption + data-retention/erasure (PDPA) workflow.
