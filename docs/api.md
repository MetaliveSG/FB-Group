# API Reference

Base URL: `http://localhost:8000` · All app endpoints under `/api/v1`.
Interactive docs: `/docs` (Swagger) · `/redoc` · machine spec: `/openapi.json`
(also saved to `artifacts/openapi.json`).

Auth: `Authorization: Bearer <access_token>`. Errors:
`{ "error": { "code": "...", "message": "..." } }` with the matching HTTP status.

## Health
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | – | liveness probe |

## Auth (Module 2)
| Method | Path | Auth | Body / Notes |
|---|---|---|---|
| POST | `/api/v1/auth/customer/register` | – | `{email,password,full_name?,phone?,birthday?}` → token resp (201) |
| POST | `/api/v1/auth/customer/login` | – | `{email,password}` (rate-limited) |
| POST | `/api/v1/auth/customer/otp/request` | – | `{phone}` → `{message, debug_code}` (dev only) |
| POST | `/api/v1/auth/customer/otp/verify` | – | `{phone,code,full_name?}` (register-or-login) |
| POST | `/api/v1/auth/customer/sso` | – | `{provider:"google"\|"apple", sub, email?, full_name?}` (mock) |
| POST | `/api/v1/auth/staff/login` | – | `{email,password}` → token resp `actor:"user"` |
| POST | `/api/v1/auth/refresh` | – | `{refresh_token}` → new access token |

Token response: `{access_token, refresh_token, token_type, actor, customer?, user?}`.

## QR + Menu (Modules 3, 4)
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/qr/{token}` | – | dining context + `is_foodcourt`/`stalls[]`; inline `menu` for single-stall, null for foodcourt; module flags `ordering_enabled`/`rewards_enabled` (Phase 2 — rewards-only when ordering off) |
| GET | `/api/v1/qr/{token}/menu/{menu_id}` | – | full menu for one stall, validated to the token's outlet (cross-outlet → 404 `menu_not_found`) |
| GET | `/api/v1/outlets/{outlet_id}/menu` | – | menu only |

## Orders + Checkout (Modules 4, 5)
| Method | Path | Auth | Notes |
|---|---|---|---|
| POST | `/api/v1/orders` | customer | `{qr_token, items:[{menu_item_id,quantity,modifier_ids?}], order_type?}` |
| GET | `/api/v1/orders` | staff `order.view` | merchant-wide orders feed: order+items+breakdown+outlet/customer/table labels; filters `?status=&outlet_id=&limit=`; outlet-scoped users see only their outlets |
| POST | `/api/v1/orders/manual` | staff `order.manage` | cashier/walk-in order (`{outlet_id, items, customer_phone?}`) |
| GET | `/api/v1/orders/{id}` | customer (own) | order detail |
| PATCH | `/api/v1/orders/{id}/status` | staff `order.manage` | `{status}` — validated lifecycle |
| POST | `/api/v1/orders/{id}/checkout` | customer (own) | `{method, force_outcome?}` → payment + points |
| POST | `/api/v1/orders/{id}/cashier-checkout` | staff `payment.process` | walk-in checkout |

Payment methods: `cash` `card` `nets` `paywave` `paynow`.
Order lifecycle: `pending → accepted → preparing → ready → completed` (`cancelled` from any non-terminal).

## CRM (Module 7) — staff, tenant-isolated
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/crm/customers` | `crm.view` | `?segment=&search=&outlet_id=&merchant_id=` |
| GET | `/api/v1/crm/segments` | `crm.view` | segment counts |
| GET | `/api/v1/crm/customers/{id}` | `crm.view` | profile + visit/txn/reward history + tags/notes |
| POST | `/api/v1/crm/customers/{id}/tags` | `crm.manage` | `{tag}` |
| POST | `/api/v1/crm/customers/{id}/notes` | `crm.manage` | `{body}` |

Segments: `vip`, `inactive`, `new`, `frequent`, `high_spender`, `low_frequency`,
`birthday_month`; `outlet_specific` via `?outlet_id=`.

## CRM activities — Salesforce-style (staff)
| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/api/v1/crm/customers/{id}/timeline` | `crm.view` | unified activity feed (orders/payments/points/notes/tasks), newest first |
| GET | `/api/v1/crm/customers/{id}/tasks` | `crm.view` | tasks for a customer |
| POST | `/api/v1/crm/customers/{id}/tasks` | `crm.manage` | `{title, description?, due_date?, priority?, assignee_user_id?}` |
| PATCH | `/api/v1/crm/tasks/{task_id}` | `crm.manage` | `{status:"done"\|"open"}` |
| GET | `/api/v1/crm/tasks` | `crm.view` | the caller's open tasks ("My Tasks") |
| PUT | `/api/v1/crm/customers/{id}/owner` | `crm.manage` | `{owner_user_id}` — assign/clear record owner |

Customer list/profile also return `owner_user_id`, `owner_name`, `open_tasks` (list) / `tasks` (profile).

## Promotions & Retention Campaigns (Module 8) — staff `campaign.manage`
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/campaigns` | list campaigns, each with metrics (sent/delivered/redeemed/revenue/conversion/ROI) |
| POST | `/api/v1/campaigns` | `{name, campaign_type, segment_key?, message_template, reward_points?}` |
| GET | `/api/v1/campaigns/{id}` | campaign + metrics + message log |
| POST | `/api/v1/campaigns/{id}/audience` | resolve audience by segment → `{audience_size}` |
| POST | `/api/v1/campaigns/{id}/send` | mock WhatsApp send (with retry) → `{delivered, failed, audience}` |
| GET | `/api/v1/campaigns/{id}/metrics` | sent, delivered, redeemed, revenue_generated, conversion_rate, cost, ROI |
| POST | `/api/v1/campaigns/{id}/redemptions` | `{customer_id, revenue, order_id?}` — track attribution |

Campaign types: `whatsapp_promo`, `birthday`, `winback`, `weekday_boost`, `new_customer_return`, `vip_reward`.
WhatsApp send goes through a provider abstraction (`app/services/whatsapp.py`); the mock logs structured delivery + retries transient failures.

## Operator Console — Platform Super Admin only (top of the hierarchy)
All require a `super_admin` staff token (others get 403).
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/platform/overview` | ecosystem KPIs (GMV, orders, active customers, merchants/brands/outlets, coalitions) |
| GET | `/api/v1/platform/merchants` | every merchant + KPIs (revenue, orders, customers, outlets, owner, status) |
| GET | `/api/v1/platform/coalitions` | coalition programs + member merchants (`members` names + parallel `member_ids`) + points issued |
| POST | `/api/v1/platform/merchants` | onboard merchant: `{name, owner_email, owner_password, owner_name?}` → creates merchant + brand + owner (409 if email taken) |
| PATCH | `/api/v1/platform/merchants/{id}` | `{is_active}` — suspend/activate a merchant |
| PUT | `/api/v1/platform/merchants/{id}` | `{name?, module_flags?}` — rename + flip adoption flags (rewards/qr_ordering/pos); unknown flag → 400 |
| GET | `/api/v1/platform/operators` | list platform operators (super-admins); `is_self` marks the caller |
| POST | `/api/v1/platform/operators` | invite operator: `{email, password, full_name?}` → new super-admin (409 if email taken) |
| DELETE | `/api/v1/platform/operators/{id}` | revoke operator access (403 on self or the **last** remaining operator; 404 if not an operator) |
| POST | `/api/v1/platform/coalitions` | `{name}` — create a coalition |
| PATCH | `/api/v1/platform/coalitions/{id}` | `{name?, is_active?}` — rename / activate / deactivate |
| POST | `/api/v1/platform/coalitions/{id}/members` | `{merchant_id}` — add member (409 if already a member) |
| DELETE | `/api/v1/platform/coalitions/{id}/members/{merchant_id}` | remove member (404 if not a member) |

Operator drill-down reuses the CRM/reports endpoints with `?merchant_id=` (super admin may target any merchant).

## Customer Rewards & Spin-the-Wheel (customer)
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/me/loyalty?merchant_id=` | balance, lifetime, tier, next_tier, points_to_next_tier, recent ledger |
| GET | `/api/v1/me/orders?merchant_id=` | the customer's order history (status, total, items_count, summary, outlet, created_at) |
| GET | `/api/v1/me/vouchers?merchant_id=` | the customer's reward vouchers (`reward_name`, `voucher_code`, `status`, `created_at`) |
| GET | `/api/v1/me/profile` | customer profile: `full_name`, `phone`, `email`, `birthday`, `gender` |
| PATCH | `/api/v1/me/profile` | update profile — `phone` (compulsory, E.164, unique), `birthday`/`gender`/`full_name` optional |
| GET | `/api/v1/me/rewards/catalog?merchant_id=` | redeemable rewards + `can_afford` |
| POST | `/api/v1/me/rewards/redeem` | `{merchant_id, item_id}` → `{voucher_code, reward_name, points_balance}` |
| GET | `/api/v1/me/wheel?merchant_id=` | `{spin_cost, segments:[{label,color}]}`. `spin_cost` defaults to 10 but is **per-merchant configurable** via `merchants.settings.wheel_spin_cost`. |
| POST | `/api/v1/me/wheel/spin` | `{merchant_id}` → `{winning_index, prize, points_balance}` (insufficient points → 409) |
| GET | `/api/v1/me/jackpot?merchant_id=` | **888 Jackpot** config: `{spin_cost, grid_size, payline:"middle_row", grand_prize, prizes:[…]}`. `spin_cost` defaults to 5 but is **per-merchant configurable** via `merchants.settings.jackpot_spin_cost` (set on `/org/settings`; 0 = free play); `grand_prize` = persistent progressive pot (base 1000, grows ~0.5/s, resets on a win). |
| POST | `/api/v1/me/jackpot/play` | `{merchant_id}` → server-authoritative outcome: `{spin_cost, grid:[[{item_name,emoji,…}]]×3, won, prize?:{item_name,item_price,emoji,voucher_code}, points_balance}`. Middle row is the payline — 3-of-a-kind there = win that item as a `JACKPOT-*` voucher. **Free to play** (no coin cost / balance untouched while `JACKPOT_SPIN_COST=0`). |

## Reports & Forecast (Module 9) — staff `report.view`, graph-ready
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/reports/summary` | revenue, orders, unique customers, AOV, new vs repeat |
| GET | `/api/v1/reports/sales` | `?granularity=day\|week\|month&days=` timeseries |
| GET | `/api/v1/reports/top-items` | best sellers by revenue |
| GET | `/api/v1/reports/peak-hours` | 24-hour distribution |
| GET | `/api/v1/reports/outlets` | outlet comparison |
| GET | `/api/v1/reports/forecast` | `?horizon=&window=` moving-average forecast |
| GET | `/api/v1/reports/rfm` | RFM scoring: per-customer R/F/M (1-5) + named segment + distribution |
| GET | `/api/v1/reports/ai-insights` | **AI advisor**: executive summary + ranked next-best actions over sales/segments/churn/RFM/pipeline/campaigns. Uses Claude when `AI_ENABLED=1`+`ANTHROPIC_API_KEY` set, else a deterministic heuristic. Response: `{summary, highlights[], recommendations[{title,rationale,action,priority,metric}], generated_by, model, context}` |

Super admin must pass `?merchant_id=`; merchant-scoped users default to their merchant
and are forbidden from querying others.

## Pipeline / Opportunities (Salesforce-style, staff)
Configurable modes: **sales** (prospecting→qualified→proposal→negotiation→won/lost) or
**winback** (at_risk→contacted→offer_sent→recovered/churned).
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/crm/pipeline` | `?pipeline_type=sales\|winback` → stages (count/value + is_open/is_won/is_lost) + open/won totals |
| GET | `/api/v1/crm/opportunities` | `?pipeline_type=` optional filter |
| GET/POST | `/api/v1/crm/customers/{id}/opportunities` | create `{name, amount, pipeline_type?, stage?, expected_close_date?}` |
| PATCH | `/api/v1/crm/opportunities/{id}` | `{stage?, amount?}` (won/lost stage stamps closed_at) |

## Activity logging + Bulk actions + Win-back (staff)
| Method | Path | Notes |
|---|---|---|
| GET/POST | `/api/v1/crm/customers/{id}/activities` | log call/email/meeting/whatsapp/note (feeds timeline) |
| POST | `/api/v1/crm/bulk/tag` | `{tag, customer_ids?\|segment?}` → `{affected}` |
| POST | `/api/v1/crm/bulk/owner` | `{owner_user_id?, customer_ids?\|segment?}` |
| POST | `/api/v1/crm/bulk/task` | `{title, priority?, customer_ids?\|segment?}` |
| POST | `/api/v1/crm/winback` | `{customer_ids?\|rfm_segments?, create_campaign?, message_template?}` → win-back opportunities + optional campaign |

## Menu management (Module 4 admin) — staff `menu.manage`
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/menu-admin/outlets` | outlets + their menu_id (pick what to edit) |
| POST/PATCH/DELETE | `/api/v1/menu-admin/categories[/{id}]` | category CRUD |
| POST/PATCH/DELETE | `/api/v1/menu-admin/items[/{id}]` | item CRUD + `is_available` toggle |
| POST/DELETE | `/api/v1/menu-admin/modifiers[/{id}]` | modifier add/remove |

## User management (Module 10) — staff `user.manage` (owner)
| Method | Path | Notes |
|---|---|---|
| GET | `/api/v1/admin/users` | users + scoped role assignments |
| POST | `/api/v1/admin/users` | invite `{email, password, full_name, role, scope_type, scope_id?}` (409 if email taken) |
| DELETE | `/api/v1/admin/users/assignments/{id}` | revoke a role assignment |

## Org structure (Module 1 admin) — brands / outlets / tables+QR
| Method | Path | Notes |
|---|---|---|
| GET/POST/PATCH | `/api/v1/org/brands[/{id}]` | brand CRUD (`brand.manage`) |
| GET/POST/PATCH | `/api/v1/org/outlets[/{id}]` | outlet CRUD (`outlet.manage`); create auto-provisions an empty menu |
| GET/POST | `/api/v1/org/outlets/{id}/tables` | list/add tables (auto-generates a stable QR token) |
| DELETE | `/api/v1/org/tables/{id}` | remove a table + its QR |
| GET | `/api/v1/org/nav-flags` | nav-only booleans `{pipeline_enabled, rewards_enabled, qr_ordering_enabled, pos_enabled, can_manage_merchant}` for sidebar/nav gating — readable by **any staff member** (`order.view` floor); carries **no** spin costs / earn rates. `can_manage_merchant` = caller holds `merchant.manage` (owner/operator) → client hides owner-only nav (Settings/Team) when false |
| GET/PATCH | `/api/v1/org/settings` | full merchant settings: `{pipeline_enabled, wheel_spin_cost, jackpot_spin_cost, rewards_enabled, qr_ordering_enabled, pos_enabled}` — **owner-only** (GET **and** PATCH need `merchant.manage`; downline managers 403 — hard upline isolation, use `/org/nav-flags` for nav) |
| GET/PUT | `/api/v1/org/loyalty` | loyalty program (standing earn rules): `{points_per_dollar, welcome_bonus, birthday_bonus}` — 0 disables a rule; **owner-only** (GET **and** PUT need `merchant.manage`, audited) |
| GET/POST/DELETE | `/api/v1/promotions[/{id}]` | point-multiplier promos (time-bound `CAMPAIGN_MULTIPLIER`): `{label, multiplier, starts_on, ends_on, is_active}` — engine applies an active in-window multiplier to every earn (`campaign.manage`, audited) |
