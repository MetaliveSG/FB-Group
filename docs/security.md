# Security (Module 11)

## Security checklist (implemented in PoC)
- [x] **Input validation** — Pydantic v2 schemas on every request body/query (types, lengths, regex for phone, enum constraints).
- [x] **SQL injection protection** — SQLAlchemy 2.0 ORM with bound parameters everywhere; no string-built SQL.
- [x] **Password hashing** — bcrypt with per-password salt (`app/core/security.py`).
- [x] **JWT auth** — short-lived access tokens + refresh tokens; type + actor claims verified; expiry enforced (expired token → 401 `token_expired`).
- [x] **Auth middleware / dependencies** — `get_current_customer` / `get_current_user` separate diner vs staff actors; wrong actor → 403.
- [x] **RBAC + least privilege** — role→permission matrix; scoped assignments (platform/merchant/brand/outlet); `super_admin` wildcard only. Every admin surface is permission-gated: operator `/platform/*` is super-admin-only (403 otherwise); user management requires `user.manage` (owner); menu `menu.manage`; org brands `brand.manage` / outlets+tables `outlet.manage`; campaigns `campaign.manage`; settings `merchant.manage`. User invites can only grant non-super-admin roles within the merchant's own scope.
- [x] **Tenant data isolation** — `merchant_id` predicate on every query; outlet/brand scoping; verified by tests (cross-merchant leakage blocked, outlet manager limited, cross-merchant opportunity/task/menu edits rejected).
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
- No field-level encryption of PII; no data-retention/erasure (PDPA) workflow yet.
