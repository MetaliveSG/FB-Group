# Demo Credentials

_Regenerated 2026-06-08. The old seeded `makan.sg` demo was cleared; the live demo data is the two
UI-onboarded groups rebuilt idempotently by `python -m app.seed_demo_merchants` (fixed node ids →
stable QR tokens; re-run after a data wipe). All passwords `Password123!`._

## Operator (Platform Console)
| Role        | Email                    | URL                                      |
|-------------|--------------------------|------------------------------------------|
| Super Admin | superadmin@platform.sg   | http://localhost:3001/platform/login     |

## Merchant dashboard logins (web, email + password — role = node-scoped **Manager**, owner-equiv)
| Email                  | Scope (member-tree node)                                            |
|------------------------|--------------------------------------------------------------------|
| owner@breadtalk.sg     | **Breadtalk Group** (Bakery, Toast Box, Toast Box @ Orchard/Taka)  |
| owner@pepperlunch.sg   | **Pepper Lunch Group** (all Pepper Lunch outlets + sub-group/YIS)  |
| manager@toastbox.sg    | **Toast Box @ Orchard** only (single-storefront scope)             |

Login at http://localhost:3001/merchant/login

### Web role palette (segregated from POS)
- **Manager** — full node powers (owner-equivalent at its scope)
- **Viewer** — view everything **except** reports
- **Finance** — reports only
(POS operators — **Supervisor / Cashier** — are PIN-only at `/pos`, never web logins; see below.)

## POS operators (PIN-only, at `/pos` — per storefront)
- Each storefront auto-provisions **1 Supervisor + 2 Cashiers** (`User.kind="pos"`, `@pos.local`).
- PINs are encrypted at rest; the owner reveals/sets them in **Settings → Point of Sale → Staff & PINs**
  (or Platform Console node drawer). Not reproducible here — reveal per storefront.

## Customers
- Scan a live storefront QR (each storefront's *Tables & QR* page has its tokens).
- OTP login phone `+6580000000` — in `DEBUG` the API returns `debug_code`.

## Modules (per-node toggles)
Each node can toggle **Table QR · Intelligence · POS** (inherit/on/off, cascades down). The dashboard
sidebar and the customer tab bar show/hide accordingly. POS defaults ON.
