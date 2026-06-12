# Architecture — Customer-Scan Domains (QR)

_Status: **LOCKED 2026-06-10** (decision register row of that date). The domain scheme is decided; the
`slug` field + tenant-resolved scan base are **NOT built yet** — see the gap below. Moved out of
CLAUDE.md 2026-06-12 (constitution slimming); this doc is the full spec._

## The scheme
The customer-scan surface is served per-tenant on a CIP subdomain: **`{slug}.mycip.io`** (e.g.
`breadtalk.mycip.io`, `fsg.mycip.io`). **Apex/root brand domain = `mycip.io`.** A printed QR therefore
encodes **`https://{slug}.mycip.io/t/{token}`** (a Storefront) or `…/t/node/{id}` (a group browse).

## Rules
- **The QR host comes from PER-TENANT config, never the browser.** *Current gap:*
  `apps/web/src/app/merchant/tables/page.tsx` builds the URL from `window.location.origin`
  (→ `localhost:3001` in dev) — that's PoC-only and MUST be replaced by a tenant-resolved scan base
  before any real QR is printed (**printed codes are permanent**). Same for the `/platform` "QR Menu"
  button + on-screen preview. Backend `qr_path` stays a relative `/t/{token}` — only the web layer
  prepends the origin, so the fix lives there (+ a backend resolver that emits the canonical
  `{slug}.mycip.io` host per tenant).
- **`slug`** = a new per-tenant field (settlement-boundary node / `Merchant`), unique, → its subdomain.
  NOT built yet.
- **Routing:** wildcard `*.mycip.io` DNS → ONE CIP edge → the same Next app serves `/t/{token}`
  regardless of `Host`; the **token alone identifies the outlet** (host = branding + trust). Validate
  the token's tenant matches the host's tenant (so a competitor's QR can't resolve on your branded
  subdomain).
- **TLS:** one wildcard cert `*.mycip.io` covers every tenant subdomain.

## Deferred (Tier 3, post-MVP)
BYO **custom domains** (e.g. `order.fairprice.sg`) — tenant CNAMEs to CIP + per-domain cert automation
(ACM/Caddy) + a `tenant_domains` verification table. Subdomain is the locked default; custom-domain is
later config on the same resolver, never a reprint. Keep retired hosts 301-ing.
